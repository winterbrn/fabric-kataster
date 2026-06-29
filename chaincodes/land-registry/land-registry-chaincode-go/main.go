package main

import (
	"log"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

func main() {
	chaincode, err := contractapi.NewChaincode(&SmartContract{})
	if err != nil {
		log.Panicf("failed to create chaincode: %v", err)
	}

	if err := chaincode.Start(); err != nil {
		log.Panicf("failed to start chaincode: %v", err)
	}
}
