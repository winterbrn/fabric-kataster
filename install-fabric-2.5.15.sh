#!/bin/bash

###############################################################################
# Hyperledger Fabric 2.5.15 Binary Installation Script
#
# This script downloads and installs the official Hyperledger Fabric
# binaries (peer, orderer, configtxgen, etc.) and the Fabric CA client
# for version 2.5.15.
#
# The script is intended for academic / research environments
# where reproducible and version-pinned installations are required.
#
# Tested on Ubuntu 22.04 / WSL2.
###############################################################################

set -e  # Stop immediately if any command fails

FABRIC_VERSION="2.5.15"
CA_VERSION="1.5.8"
ARCH="linux-amd64"

INSTALL_DIR="$PWD/fabric-bin"
BIN_DIR="$INSTALL_DIR/bin"

echo "============================================================"
echo "Installing Hyperledger Fabric ${FABRIC_VERSION}"
echo "Target directory: ${INSTALL_DIR}"
echo "============================================================"

# ---------------------------------------------------------------------------
# Step 1: Create installation directory
# ---------------------------------------------------------------------------

mkdir -p ${INSTALL_DIR}
cd ${INSTALL_DIR}

# ---------------------------------------------------------------------------
# Step 2: Download Fabric core binaries
# ---------------------------------------------------------------------------

echo "Downloading Fabric peer/orderer tools..."

curl -L -o fabric.tar.gz \
https://github.com/hyperledger/fabric/releases/download/v${FABRIC_VERSION}/hyperledger-fabric-${ARCH}-${FABRIC_VERSION}.tar.gz

# ---------------------------------------------------------------------------
# Step 3: Extract binaries
# ---------------------------------------------------------------------------

tar -xzf fabric.tar.gz
rm fabric.tar.gz

# ---------------------------------------------------------------------------
# Step 4: Download Fabric CA client
# ---------------------------------------------------------------------------

echo "Downloading Fabric CA client..."

curl -L -o fabric-ca.tar.gz \
https://github.com/hyperledger/fabric-ca/releases/download/v${CA_VERSION}/hyperledger-fabric-ca-${ARCH}-${CA_VERSION}.tar.gz

tar -xzf fabric-ca.tar.gz
rm fabric-ca.tar.gz

# ---------------------------------------------------------------------------
# Step 5: Verification
# ---------------------------------------------------------------------------

echo ""
echo "Verifying installed binaries..."
echo "------------------------------------------------------------"

${BIN_DIR}/peer version
${BIN_DIR}/orderer version
${BIN_DIR}/configtxgen --version
${BIN_DIR}/fabric-ca-client version

echo "------------------------------------------------------------"
echo "Installation completed successfully."
echo ""
echo "To use Fabric tools, add the following to your PATH:"
echo ""
echo "export PATH=\$PATH:${BIN_DIR}"
echo ""
echo "For permanent usage, append it to ~/.bashrc:"
echo "echo 'export PATH=\$PATH:${BIN_DIR}' >> ~/.bashrc"
echo ""
echo "============================================================"
