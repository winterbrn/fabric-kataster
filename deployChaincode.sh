#!/bin/bash
set -euo pipefail

source ./env.sh

CHANNEL_NAME="${CHANNEL_NAME:-landregistry}"
CC_NAME="${CC_NAME:-parcel}"
CC_RUNTIME_LANGUAGE="golang"
CC_VERSION="${CC_VERSION:-1}"
CC_SEQUENCE="${CC_SEQUENCE:-1}"
CC_SRC_PATH="${CC_SRC_PATH:-./chaincodes/land-registry/land-registry-chaincode-go}"

ORDERER_ADDR="orderer.orderer.com:7050"
ORDERER_CA_IN_CONTAINER="/etc/hyperledger/channel/crypto-config/ordererOrganizations/orderer.com/orderers/orderer.orderer.com/tls/ca.crt"

DISTRICT_ADMIN_MSP="/etc/hyperledger/channel/crypto-config/peerOrganizations/district.com/users/Admin@district.com/msp"
CADASTRE_ADMIN_MSP="/etc/hyperledger/channel/crypto-config/peerOrganizations/cadastre.com/users/Admin@cadastre.com/msp"

DISTRICT_PEER0_TLS_CA="/etc/hyperledger/channel/crypto-config/peerOrganizations/district.com/peers/peer0.district.com/tls/ca.crt"
CADASTRE_PEER0_TLS_CA="/etc/hyperledger/channel/crypto-config/peerOrganizations/cadastre.com/peers/peer0.cadastre.com/tls/ca.crt"

runPeer() {
  local container="$1"
  shift
  docker exec "${container}" bash -lc "$*"
}

peerEnvDistrictPeer0() {
  cat <<EOF
export FABRIC_LOGGING_SPEC=INFO
export CORE_PEER_LOCALMSPID=DistrictMSP
export CORE_PEER_MSPCONFIGPATH=${DISTRICT_ADMIN_MSP}
export CORE_PEER_ADDRESS=peer0.district.com:7051
export CORE_PEER_TLS_ENABLED=true
export CORE_PEER_TLS_ROOTCERT_FILE=${DISTRICT_PEER0_TLS_CA}
EOF
}

peerEnvCadastrePeer0() {
  cat <<EOF
export FABRIC_LOGGING_SPEC=INFO
export CORE_PEER_LOCALMSPID=CadastreMSP
export CORE_PEER_MSPCONFIGPATH=${CADASTRE_ADMIN_MSP}
export CORE_PEER_ADDRESS=peer0.cadastre.com:9051
export CORE_PEER_TLS_ENABLED=true
export CORE_PEER_TLS_ROOTCERT_FILE=${CADASTRE_PEER0_TLS_CA}
EOF
}

packageChaincode() {
  rm -f "${CC_NAME}.tar.gz"
  peer lifecycle chaincode package "${CC_NAME}.tar.gz" \
    --path "${CC_SRC_PATH}" \
    --lang "${CC_RUNTIME_LANGUAGE}" \
    --label "${CC_NAME}_${CC_VERSION}"
  echo "Packaged: ${CC_NAME}.tar.gz"
}

installChaincode() {
  docker cp "${CC_NAME}.tar.gz" peer0.district.com:/tmp/"${CC_NAME}.tar.gz"
  docker cp "${CC_NAME}.tar.gz" peer0.cadastre.com:/tmp/"${CC_NAME}.tar.gz"

  runPeer peer0.district.com "$(peerEnvDistrictPeer0); peer lifecycle chaincode install /tmp/${CC_NAME}.tar.gz"
  runPeer peer0.cadastre.com "$(peerEnvCadastrePeer0); peer lifecycle chaincode install /tmp/${CC_NAME}.tar.gz"

  echo "Installed on peer0.district.com and peer0.cadastre.com"
}

queryInstalled() {
  local out
  out="$(runPeer peer0.district.com "$(peerEnvDistrictPeer0); peer lifecycle chaincode queryinstalled")"
  echo "${out}"
  local matches
  matches="$(
    echo "${out}" \
      | tr -d '\r' \
      | sed -n "/${CC_NAME}_${CC_VERSION}/{s/^Package ID: //; s/, Label:.*$//; p;}"
  )"
  if [[ -z "${matches}" ]]; then
    echo "Failed to parse PACKAGE_ID from queryinstalled output" >&2
    exit 1
  fi
  if [[ "$(printf '%s\n' "${matches}" | wc -l | tr -d ' ')" != "1" ]]; then
    echo "WARN: multiple PACKAGE_ID matches for label ${CC_NAME}_${CC_VERSION}; using the last one" >&2
  fi
  PACKAGE_ID="$(printf '%s\n' "${matches}" | tail -n 1)"
  export PACKAGE_ID
  echo "PACKAGE_ID=${PACKAGE_ID}"
}

approveForDistrict() {
  : "${PACKAGE_ID:?PACKAGE_ID is required (run queryInstalled first)}"
  runPeer peer0.district.com "$(peerEnvDistrictPeer0); peer lifecycle chaincode approveformyorg -o ${ORDERER_ADDR} --ordererTLSHostnameOverride orderer.orderer.com --tls --cafile ${ORDERER_CA_IN_CONTAINER} --channelID ${CHANNEL_NAME} --name ${CC_NAME} --version ${CC_VERSION} --package-id '${PACKAGE_ID}' --sequence ${CC_SEQUENCE} --waitForEventTimeout 300s"
  echo "Approved by DistrictMSP"
}

approveForCadastre() {
  : "${PACKAGE_ID:?PACKAGE_ID is required (run queryInstalled first)}"
  runPeer peer0.cadastre.com "$(peerEnvCadastrePeer0); peer lifecycle chaincode approveformyorg -o ${ORDERER_ADDR} --ordererTLSHostnameOverride orderer.orderer.com --tls --cafile ${ORDERER_CA_IN_CONTAINER} --channelID ${CHANNEL_NAME} --name ${CC_NAME} --version ${CC_VERSION} --package-id '${PACKAGE_ID}' --sequence ${CC_SEQUENCE} --waitForEventTimeout 300s"
  echo "Approved by CadastreMSP"
}

checkCommitReadiness() {
  runPeer peer0.district.com "$(peerEnvDistrictPeer0); peer lifecycle chaincode checkcommitreadiness --channelID ${CHANNEL_NAME} --name ${CC_NAME} --version ${CC_VERSION} --sequence ${CC_SEQUENCE} --output json"
}

commitChaincodeDefinition() {
  runPeer peer0.district.com "$(peerEnvDistrictPeer0); peer lifecycle chaincode commit -o ${ORDERER_ADDR} --ordererTLSHostnameOverride orderer.orderer.com --tls --cafile ${ORDERER_CA_IN_CONTAINER} --channelID ${CHANNEL_NAME} --name ${CC_NAME} --version ${CC_VERSION} --sequence ${CC_SEQUENCE} --peerAddresses peer0.district.com:7051 --tlsRootCertFiles ${DISTRICT_PEER0_TLS_CA} --peerAddresses peer0.cadastre.com:9051 --tlsRootCertFiles ${CADASTRE_PEER0_TLS_CA} --waitForEventTimeout 900s"
  echo "Committed chaincode definition"
}

queryCommitted() {
  runPeer peer0.district.com "$(peerEnvDistrictPeer0); peer lifecycle chaincode querycommitted --channelID ${CHANNEL_NAME} --name ${CC_NAME}"
}

invokeCreateParcel() {
  local parcel_json="$1"

  local cc_payload
  cc_payload="$(
    python3 -c 'import json,sys; parcel=sys.stdin.read(); sys.stdout.write(json.dumps({"function":"CreateParcel","Args":[parcel]}, ensure_ascii=False, separators=(",", ":")))' <<<"${parcel_json}"
  )"

  local cc_payload_b64
  if cc_payload_b64="$(printf '%s' "${cc_payload}" | base64 -w0 2>/dev/null)"; then
    :
  else
    cc_payload_b64="$(printf '%s' "${cc_payload}" | base64)"
    cc_payload_b64="${cc_payload_b64//$'\n'/}"
  fi

  runPeer peer0.district.com "$(peerEnvDistrictPeer0); CC_PAYLOAD_B64='${cc_payload_b64}'; cc_payload=\$(printf '%s' \"\${CC_PAYLOAD_B64}\" | base64 -d); peer chaincode invoke -o ${ORDERER_ADDR} --ordererTLSHostnameOverride orderer.orderer.com --tls --cafile ${ORDERER_CA_IN_CONTAINER} -C ${CHANNEL_NAME} -n ${CC_NAME} --peerAddresses peer0.district.com:7051 --tlsRootCertFiles ${DISTRICT_PEER0_TLS_CA} --peerAddresses peer0.cadastre.com:9051 --tlsRootCertFiles ${CADASTRE_PEER0_TLS_CA} -c \"\${cc_payload}\" --waitForEventTimeout 300s"
}

queryParcel() {
  local id="$1"
  runPeer peer0.district.com "$(peerEnvDistrictPeer0); peer chaincode query -C ${CHANNEL_NAME} -n ${CC_NAME} -c '{\"function\":\"ReadParcel\",\"Args\":[\"${id}\"]}'"
}

usage() {
  cat <<EOF
Usage:
  ./deployChaincode.sh package
  ./deployChaincode.sh install
  ./deployChaincode.sh queryinstalled
  ./deployChaincode.sh approve
  ./deployChaincode.sh check
  ./deployChaincode.sh commit
  ./deployChaincode.sh querycommitted
  ./deployChaincode.sh createparcel '<json>'
  ./deployChaincode.sh readparcel '<id>'

Env overrides:
  CHANNEL_NAME, CC_NAME, CC_VERSION, CC_SEQUENCE, CC_SRC_PATH
EOF
}

cmd="${1:-}"
case "${cmd}" in
  package) packageChaincode ;;
  install) installChaincode ;;
  queryinstalled) queryInstalled ;;
  approve) queryInstalled; approveForDistrict; approveForCadastre ;;
  check) checkCommitReadiness ;;
  commit) commitChaincodeDefinition ;;
  querycommitted) queryCommitted ;;
  createparcel) invokeCreateParcel "${2:?parcel json is required}" ;;
  readparcel) queryParcel "${2:?id is required}" ;;
  *) usage; exit 1 ;;
esac
