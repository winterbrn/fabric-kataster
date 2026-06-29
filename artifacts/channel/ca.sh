#!/bin/bash

set -e

# ==============================
# Configuration
# ==============================

SYS_CHANNEL="sys-channel"
CHANNEL_NAME="landregistry"
CONFIG_PATH="."

GENESIS_BLOCK="./genesis.block"
CHANNEL_TX="./${CHANNEL_NAME}.tx"

DISTRICT_ANCHOR="./DistrictMSPanchors.tx"
CADASTRE_ANCHOR="./CadastreMSPanchors.tx"

echo "System channel: $SYS_CHANNEL"
echo "Application channel: $CHANNEL_NAME"
echo "Using config path: $CONFIG_PATH"

# ==============================
# Cleanup old artifacts
# ==============================

echo "Cleaning old artifacts..."

[ -f "$GENESIS_BLOCK" ] && rm -f "$GENESIS_BLOCK"
[ -f "$CHANNEL_TX" ] && rm -f "$CHANNEL_TX"
[ -f "$DISTRICT_ANCHOR" ] && rm -f "$DISTRICT_ANCHOR"
[ -f "$CADASTRE_ANCHOR" ] && rm -f "$CADASTRE_ANCHOR"

# ==============================
# Generate System Genesis Block
# ==============================

echo "Generating system genesis block..."

configtxgen \
  -profile OrdererGenesis \
  -configPath $CONFIG_PATH \
  -channelID $SYS_CHANNEL \
  -outputBlock $GENESIS_BLOCK

# ==============================
# Generate Channel Creation TX
# ==============================

echo "Generating channel creation transaction..."

configtxgen \
  -profile LandRegistryChannel \
  -configPath $CONFIG_PATH \
  -outputCreateChannelTx $CHANNEL_TX \
  -channelID $CHANNEL_NAME

# ==============================
# Generate Anchor Peer Updates
# ==============================

echo "Generating District anchor peer..."

configtxgen \
  -profile LandRegistryChannel \
  -configPath $CONFIG_PATH \
  -outputAnchorPeersUpdate $DISTRICT_ANCHOR \
  -channelID $CHANNEL_NAME \
  -asOrg DistrictMSP


echo "Generating Cadastre anchor peer..."

configtxgen \
  -profile LandRegistryChannel \
  -configPath $CONFIG_PATH \
  -outputAnchorPeersUpdate $CADASTRE_ANCHOR \
  -channelID $CHANNEL_NAME \
  -asOrg CadastreMSP


echo "All artifacts generated successfully."
