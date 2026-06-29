#!/bin/bash

function one_line_pem {
    echo "`awk 'NF {sub(/\\n/, ""); printf "%s\\\\\\\n",$0;}' $1`"
}

function json_ccp {
    local PP=$(one_line_pem $4)
    local CP=$(one_line_pem $5)
    local PP1=$(one_line_pem $6)
    sed -e "s/\${ORG}/$1/" \
        -e "s/\${P0PORT}/$2/" \
        -e "s/\${CAPORT}/$3/" \
        -e "s#\${PEERPEM}#$PP#" \
        -e "s#\${CAPEM}#$CP#" \
        -e "s#\${PEERPEM1}#$PP1#" \
        -e "s#\${P0PORT1}#$7#" \
        ./ccp-template.json
}

ORG=cadastre
P0PORT=7051
CAPORT=7054
P0PORT1=8051
PEERPEM=../../artifacts/channel/crypto-config/peerOrganizations/cadastre.com/peers/peer0.cadastre.com/msp/tlscacerts/tlsca.cadastre.com-cert.pem
PEERPEM1=../../artifacts/channel/crypto-config/peerOrganizations/cadastre.com/peers/peer1.cadastre.com/msp/tlscacerts/tlsca.cadastre.com-cert.pem
CAPEM=../../artifacts/channel/crypto-config/peerOrganizations/cadastre.com/msp/tlscacerts/tlsca.cadastre.com-cert.pem

echo "$(json_ccp $ORG $P0PORT $CAPORT $PEERPEM $CAPEM $PEERPEM1 $P0PORT1)" > connection-cadastre.json


ORG=district
P0PORT=9051
CAPORT=8054
P0PORT1=10051
PEERPEM=../../artifacts/channel/crypto-config/peerOrganizations/district.com/peers/peer0.district.com/msp/tlscacerts/tlsca.district.com-cert.pem
PEERPEM1=../../artifacts/channel/crypto-config/peerOrganizations/district.com/peers/peer1.district.com/msp/tlscacerts/tlsca.district.com-cert.pem
CAPEM=../../artifacts/channel/crypto-config/peerOrganizations/district.com/msp/tlscacerts/tlsca.district.com-cert.pem


echo "$(json_ccp $ORG $P0PORT $CAPORT $PEERPEM $CAPEM $PEERPEM1 $P0PORT1)" > connection-district.json