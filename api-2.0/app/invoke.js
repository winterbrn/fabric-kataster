const helper = require('./helper');

function toTransientMap(transientData) {
    if (!transientData) return undefined;

    const parsed = helper.tryParseJson(transientData);
    if (!parsed || typeof parsed !== 'object') return undefined;

    const transientMap = {};
    for (const [key, value] of Object.entries(parsed)) {
        transientMap[key] = Buffer.from(typeof value === 'string' ? value : JSON.stringify(value));
    }
    return transientMap;
}

const invokeTransaction = async (channelName, chaincodeName, fcn, args, username, orgName, transientData) => {
    const ccp = helper.getCCP(orgName);
    const { wallet } = await helper.getWalletAndIdentity(orgName, username);
    const argList = helper.toArgsArray(args);
    const transientMap = toTransientMap(transientData);

    const gateway = await helper.connectGateway(ccp, wallet, username);
    try {
        const network = await gateway.getNetwork(channelName);
        const contract = network.getContract(chaincodeName);
        const transaction = contract.createTransaction(fcn);
        if (transientMap) transaction.setTransient(transientMap);
        const resultBuffer = await transaction.submit(...argList);
        const resultString = resultBuffer ? resultBuffer.toString() : '';
        return helper.tryParseJson(resultString);
    } finally {
        gateway.disconnect();
    }
};

exports.invokeTransaction = invokeTransaction;
