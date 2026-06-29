'use strict';

const { WorkloadModuleBase } = require('@hyperledger/caliper-core');

class GetAllParcelsWorkload extends WorkloadModuleBase {
    async initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext) {
        this.workerIndex = workerIndex;
        this.roundArguments = roundArguments || {};
        this.sutAdapter = sutAdapter;

        this.channel = this.roundArguments.channel || 'landregistry';
        this.contractId = this.roundArguments.contractId || 'parcel';
        this.invokerMspId = this.roundArguments.invokerMspId;
        this.invokerIdentity = this.roundArguments.invokerIdentity;
    }

    async submitTransaction() {
        const requestSettings = {
            channel: this.channel,
            contractId: this.contractId,
            contractFunction: 'GetAllParcels',
            contractArguments: [],
            readOnly: true,
            invokerMspId: this.invokerMspId,
            invokerIdentity: this.invokerIdentity,
        };

        await this.sutAdapter.sendRequests(requestSettings);
    }
}

function createWorkloadModule() {
    return new GetAllParcelsWorkload();
}

module.exports.createWorkloadModule = createWorkloadModule;

