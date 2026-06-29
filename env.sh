#!/bin/bash

export PATH="${PWD}/fabric-bin/bin:${PATH}"

export CORE_PEER_TLS_ENABLED=true
export FABRIC_CFG_PATH="${PWD}/fabric-bin/config"
export CHANNEL_NAME="landregistry"

export ORDERER_CA="${PWD}/artifacts/channel/crypto-config/ordererOrganizations/orderer.com/orderers/orderer.orderer.com/tls/ca.crt"

export PEER0_DISTRICT_CA="${PWD}/artifacts/channel/crypto-config/peerOrganizations/district.com/peers/peer0.district.com/tls/ca.crt"
export PEER0_CADASTRE_CA="${PWD}/artifacts/channel/crypto-config/peerOrganizations/cadastre.com/peers/peer0.cadastre.com/tls/ca.crt"

setGlobalsForPeer0District() {
    export CORE_PEER_LOCALMSPID="DistrictMSP"
    export CORE_PEER_TLS_ROOTCERT_FILE="$PEER0_DISTRICT_CA"
    export CORE_PEER_MSPCONFIGPATH="${PWD}/artifacts/channel/crypto-config/peerOrganizations/district.com/users/Admin@district.com/msp"
    export CORE_PEER_ADDRESS="peer0.district.com:7051"
}

setGlobalsForPeer1District() {
    export CORE_PEER_LOCALMSPID="DistrictMSP"
    export CORE_PEER_TLS_ROOTCERT_FILE="$PEER0_DISTRICT_CA"
    export CORE_PEER_MSPCONFIGPATH="${PWD}/artifacts/channel/crypto-config/peerOrganizations/district.com/users/Admin@district.com/msp"
    export CORE_PEER_ADDRESS="peer1.district.com:8051"
}

setGlobalsForPeer0Cadastre() {
    export CORE_PEER_LOCALMSPID="CadastreMSP"
    export CORE_PEER_TLS_ROOTCERT_FILE="$PEER0_CADASTRE_CA"
    export CORE_PEER_MSPCONFIGPATH="${PWD}/artifacts/channel/crypto-config/peerOrganizations/cadastre.com/users/Admin@cadastre.com/msp"
    export CORE_PEER_ADDRESS="peer0.cadastre.com:9051"
}

setGlobalsForPeer1Cadastre() {
    export CORE_PEER_LOCALMSPID="CadastreMSP"
    export CORE_PEER_TLS_ROOTCERT_FILE="$PEER0_CADASTRE_CA"
    export CORE_PEER_MSPCONFIGPATH="${PWD}/artifacts/channel/crypto-config/peerOrganizations/cadastre.com/users/Admin@cadastre.com/msp"
    export CORE_PEER_ADDRESS="peer1.cadastre.com:10051"
}
