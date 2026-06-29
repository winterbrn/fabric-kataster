# Land Registry on Hyperledger Fabric

A blockchain-based land registry system built with Hyperledger Fabric 2.5. This was made as a diploma thesis project.

The network has two organizations (District and Cadastre), each with two peers, one orderer, and a REST API for interacting with the chaincode.

## Prerequisites

- Docker and Docker Compose
- Node.js (v14+)
- Go (for chaincode)
- Python 3 (for seeding test data)
- Linux or WSL2

## Setup

### 1. Install Fabric binaries

```bash
./install-fabric-2.5.15.sh
```

This downloads the Fabric 2.5.15 binaries into the `fabric-bin/` folder.

### 2. Start the network

```bash
./network-up.sh
```

This starts all the Docker containers (peers, orderer, CAs, CouchDB).

### 3. Create channel and join peers

```bash
./cc.sh
```

Creates the `landregistry` channel and joins all four peers to it.

### 4. Deploy the chaincode

```bash
./deployChaincode.sh
```

Packages, installs, approves, and commits the `parcel` chaincode on all peers.

### 5. Start the API

```bash
cd api-2.0
npm install
npm start
```

The API runs on `http://localhost:4000` by default.

### 6. Enroll users and seed data (optional)

```bash
./enroll-seed-users.sh 300
./seedParcels.sh 300
```

This creates 300 test users and 300 test parcels.

## Stopping the network

```bash
./network-down.sh
```

This stops all containers and removes the volumes.

## Project structure

- `artifacts/` - Docker Compose files, crypto material, channel config
- `api-2.0/` - REST API (Express.js)
- `chaincodes/` - Go chaincode for land registry
- `caliper/` - Hyperledger Caliper benchmarks
