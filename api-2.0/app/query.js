const helper = require('./helper');

const query = async (channelName, chaincodeName, args, fcn, username, orgName) => {
    const ccp = helper.getCCP(orgName);
    const { wallet } = await helper.getWalletAndIdentity(orgName, username);
    const argList = helper.toArgsArray(args);

    const gateway = await helper.connectGateway(ccp, wallet, username);
    try {
        const network = await gateway.getNetwork(channelName);
        const contract = network.getContract(chaincodeName);
        const resultBuffer = await contract.evaluateTransaction(fcn, ...argList);
        let resultString = resultBuffer ? resultBuffer.toString() : '';

        if (resultString === '' && fcn.startsWith('GetAll')) {
            resultString = '[]';
        }

        return helper.tryParseJson(resultString);
    } finally {
        gateway.disconnect();
    }
};

exports.query = query;
