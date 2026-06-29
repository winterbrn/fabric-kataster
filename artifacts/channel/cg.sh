#!/bin/bash

# This script runs cryptogen generate for all .yaml files in the current folder
# It deletes the existing crypto-config folder first, if it exists

CRYPTO_DIR="./crypto-config"

# Remove existing crypto-config directory
if [ -d "$CRYPTO_DIR" ]; then
    echo "Deleting existing $CRYPTO_DIR directory..."
    sudo rm -rf "$CRYPTO_DIR"
fi

# Loop through all YAML files in the folder
for yaml_file in *.yaml; do
    echo "Generating crypto material from: $yaml_file"
    cryptogen generate --config="$yaml_file"
    
    if [ $? -ne 0 ]; then
        echo "Error processing $yaml_file"
        exit 1
    fi
done

echo "Cryptogen generation completed for all YAML files."