'use strict';

const crypto = require('crypto');
const { WorkloadModuleBase } = require('@hyperledger/caliper-core');

class CreateParcelWorkload extends WorkloadModuleBase {
    async initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext) {
        this.workerIndex = workerIndex;
        this.txIndex = 0;
        this.roundArguments = roundArguments || {};
        this.sutAdapter = sutAdapter;

        this.channel = this.roundArguments.channel || 'landregistry';
        this.contractId = this.roundArguments.contractId || 'parcel';
        this.invokerMspId = this.roundArguments.invokerMspId;
        this.invokerIdentity = this.roundArguments.invokerIdentity;
    }

    _newParcel() {
        const nonce = crypto.randomBytes(4).toString('hex');
        const id = `caliper-${Date.now()}-${this.workerIndex}-${this.txIndex}-${nonce}`;
        const parcel = {
            id,
            parcelId: `P-${this.workerIndex}-${this.txIndex}`,
            parcelNumber: `${1000 + this.workerIndex}-${this.txIndex}`,
            cadastralArea: 'TestArea',
            area: 100 + (this.txIndex % 50),
            owners: [{
                userId: `CALIP-${this.workerIndex}-${this.txIndex}-${nonce}`,
                name: 'Alice',
                share: '1/1',
                address: 'TestStreet 1',
                birthDate: '1990-01-01',
            }],
            points: [
                { x: 0, y: 0 },
                { x: 10, y: 0 },
                { x: 10, y: 10 },
                { x: 0, y: 10 },
            ],
        };

        this.txIndex += 1;
        return JSON.stringify(parcel);
    }

    async submitTransaction() {
        const parcelJson = this._newParcel();

        const requestSettings = {
            channel: this.channel,
            contractId: this.contractId,
            contractFunction: 'CreateParcel',
            contractArguments: [parcelJson],
            readOnly: false,
            invokerMspId: this.invokerMspId,
            invokerIdentity: this.invokerIdentity,
        };

        await this.sutAdapter.sendRequests(requestSettings);
    }
}

function createWorkloadModule() {
    return new CreateParcelWorkload();
}

module.exports.createWorkloadModule = createWorkloadModule;

