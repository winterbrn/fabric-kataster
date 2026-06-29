#!/bin/bash
set -e

CHANNEL_NAME="landregistry"
CHANNEL_TX_FILE="/etc/hyperledger/channel/${CHANNEL_NAME}.tx"
CHANNEL_BLOCK_FILE="/etc/hyperledger/channel/${CHANNEL_NAME}.block"

ORDERER_CA="/etc/hyperledger/channel/crypto-config/ordererOrganizations/orderer.com/orderers/orderer.orderer.com/tls/ca.crt"

DISTRICT_ADMIN_MSP="/etc/hyperledger/channel/crypto-config/peerOrganizations/district.com/users/Admin@district.com/msp"
CADASTRE_ADMIN_MSP="/etc/hyperledger/channel/crypto-config/peerOrganizations/cadastre.com/users/Admin@cadastre.com/msp"

DISTRICT_PEER0_TLS_CA="/etc/hyperledger/channel/crypto-config/peerOrganizations/district.com/peers/peer0.district.com/tls/ca.crt"
DISTRICT_PEER1_TLS_CA="/etc/hyperledger/channel/crypto-config/peerOrganizations/district.com/peers/peer1.district.com/tls/ca.crt"
CADASTRE_PEER0_TLS_CA="/etc/hyperledger/channel/crypto-config/peerOrganizations/cadastre.com/peers/peer0.cadastre.com/tls/ca.crt"
CADASTRE_PEER1_TLS_CA="/etc/hyperledger/channel/crypto-config/peerOrganizations/cadastre.com/peers/peer1.cadastre.com/tls/ca.crt"

DISTRICT_ANCHOR_TX="/etc/hyperledger/channel/DistrictMSPanchors.tx"
CADASTRE_ANCHOR_TX="/etc/hyperledger/channel/CadastreMSPanchors.tx"

createChannel() {
  echo "Creating channel ${CHANNEL_NAME}..."
  docker exec peer0.district.com bash -c "
    export FABRIC_LOGGING_SPEC=INFO
    export CORE_PEER_LOCALMSPID=DistrictMSP
    export CORE_PEER_MSPCONFIGPATH=${DISTRICT_ADMIN_MSP}
    export CORE_PEER_ADDRESS=peer0.district.com:7051
    export CORE_PEER_TLS_ENABLED=true
    export CORE_PEER_TLS_ROOTCERT_FILE=${DISTRICT_PEER0_TLS_CA}

    peer channel create \
      -o orderer.orderer.com:7050 \
      -c ${CHANNEL_NAME} \
      -f ${CHANNEL_TX_FILE} \
      --outputBlock ${CHANNEL_BLOCK_FILE} \
      --tls \
      --cafile ${ORDERER_CA}
  "
}

joinPeer() {
  CONTAINER=$1
  MSPID=$2
  ADDRESS=$3
  ADMIN_MSP=$4
  PEER_TLS_CA=$5

  echo "Joining ${CONTAINER} to channel ${CHANNEL_NAME}..."
  docker exec "${CONTAINER}" bash -c "
    export FABRIC_LOGGING_SPEC=INFO
    export CORE_PEER_LOCALMSPID=${MSPID}
    export CORE_PEER_MSPCONFIGPATH=${ADMIN_MSP}
    export CORE_PEER_ADDRESS=${ADDRESS}
    export CORE_PEER_TLS_ENABLED=true
    export CORE_PEER_TLS_ROOTCERT_FILE=${PEER_TLS_CA}

    peer channel join -b ${CHANNEL_BLOCK_FILE}
  "
}

updateAnchorPeer() {
  CONTAINER=$1
  MSPID=$2
  ADDRESS=$3
  ADMIN_MSP=$4
  PEER_TLS_CA=$5
  ANCHOR_TX=$6

  echo "Updating anchor peer for ${MSPID}..."
  docker exec "${CONTAINER}" bash -c "
    export FABRIC_LOGGING_SPEC=INFO
    export CORE_PEER_LOCALMSPID=${MSPID}
    export CORE_PEER_MSPCONFIGPATH=${ADMIN_MSP}
    export CORE_PEER_ADDRESS=${ADDRESS}
    export CORE_PEER_TLS_ENABLED=true
    export CORE_PEER_TLS_ROOTCERT_FILE=${PEER_TLS_CA}

    peer channel update \
      -o orderer.orderer.com:7050 \
      -c ${CHANNEL_NAME} \
      -f ${ANCHOR_TX} \
      --tls \
      --cafile ${ORDERER_CA}
  "
}

createChannel

joinPeer peer0.district.com DistrictMSP peer0.district.com:7051 ${DISTRICT_ADMIN_MSP} ${DISTRICT_PEER0_TLS_CA}
joinPeer peer1.district.com DistrictMSP peer1.district.com:8051 ${DISTRICT_ADMIN_MSP} ${DISTRICT_PEER1_TLS_CA}
joinPeer peer0.cadastre.com CadastreMSP peer0.cadastre.com:9051 ${CADASTRE_ADMIN_MSP} ${CADASTRE_PEER0_TLS_CA}
joinPeer peer1.cadastre.com CadastreMSP peer1.cadastre.com:10051 ${CADASTRE_ADMIN_MSP} ${CADASTRE_PEER1_TLS_CA}

updateAnchorPeer peer0.district.com DistrictMSP peer0.district.com:7051 ${DISTRICT_ADMIN_MSP} ${DISTRICT_PEER0_TLS_CA} ${DISTRICT_ANCHOR_TX}
updateAnchorPeer peer0.cadastre.com CadastreMSP peer0.cadastre.com:9051 ${CADASTRE_ADMIN_MSP} ${CADASTRE_PEER0_TLS_CA} ${CADASTRE_ANCHOR_TX}

echo "Channel ${CHANNEL_NAME} created and peers joined successfully."