'use strict';

const FabricCAServices = require('fabric-ca-client');
const { Gateway, Wallets } = require('fabric-network');
const path = require('path');
const fs = require('fs');

const ORG_CONFIG = {
    Cadastre: {
        ccp: 'connection-cadastre.json',
        ca: 'ca.cadastre.com',
        wallet: 'cadastre-wallet',
        mspId: 'CadastreMSP',
        affiliation: 'org1.department1',
    },
    District: {
        ccp: 'connection-district.json',
        ca: 'ca.district.com',
        wallet: 'district-wallet',
        mspId: 'DistrictMSP',
        affiliation: 'org2.department1',
    },
};

function getOrgConfig(org) {
    const config = ORG_CONFIG[org];
    if (!config) throw new Error(`Unknown org '${org}'`);
    return config;
}

function getCCP(org) {
    const config = getOrgConfig(org);
    const ccpPath = path.resolve(__dirname, '..', 'config', config.ccp);
    return JSON.parse(fs.readFileSync(ccpPath, 'utf8'));
}

function getWalletPath(org) {
    const config = getOrgConfig(org);
    const baseDir = process.env.WALLET_BASE_DIR || process.cwd();
    return path.join(baseDir, config.wallet);
}

function tryParseJson(value) {
    if (typeof value !== 'string') return value;
    try {
        return JSON.parse(value);
    } catch (e) {
        return value;
    }
}

function toArgsArray(args) {
    const parsed = tryParseJson(args);
    if (!Array.isArray(parsed)) {
        throw new Error('args must be a JSON array');
    }
    return parsed.map((arg) => (typeof arg === 'string' ? arg : JSON.stringify(arg)));
}

async function getWalletAndIdentity(org, username) {
    const walletPath = getWalletPath(org);
    const wallet = await Wallets.newFileSystemWallet(walletPath);
    const identity = await wallet.get(username);
    if (!identity) {
        throw new Error(`No identity for user '${username}' in wallet '${walletPath}'.`);
    }
    return { wallet, walletPath };
}

async function connectGateway(ccp, wallet, username) {
    const gateway = new Gateway();
    await gateway.connect(ccp, {
        wallet,
        identity: username,
        discovery: { enabled: true, asLocalhost: process.env.AS_LOCALHOST !== 'false' },
    });
    return gateway;
}

const newCaClient = async (org) => {
    const config = getOrgConfig(org);
    const ccp = getCCP(org);
    const caInfo = ccp.certificateAuthorities[config.ca];
    if (!caInfo) throw new Error(`CA info not found for org '${org}'`);

    const ca = new FabricCAServices(caInfo.url, { trustedRoots: caInfo.tlsCACerts?.pem, verify: false }, caInfo.caName);
    return { ca, ccp };
};

const ensureAdminEnrolled = async (org, ccp, ca) => {
    const config = getOrgConfig(org);
    const walletPath = getWalletPath(org);
    const wallet = await Wallets.newFileSystemWallet(walletPath);

    let adminIdentity = await wallet.get('admin');
    if (adminIdentity) return { wallet, walletPath };

    const enrollment = await ca.enroll({ enrollmentID: 'admin', enrollmentSecret: 'adminpw' });
    await wallet.put('admin', {
        credentials: {
            certificate: enrollment.certificate,
            privateKey: enrollment.key.toBytes(),
        },
        mspId: config.mspId,
        type: 'X.509',
    });

    return { wallet, walletPath };
};

const registerAndEnrollUser = async (username, org, attrs) => {
    const config = getOrgConfig(org);
    const { ca, ccp } = await newCaClient(org);
    const { wallet, walletPath } = await ensureAdminEnrolled(org, ccp, ca);

    const existing = await wallet.get(username);

    if (existing) {
        if (attrs && Object.keys(attrs).length > 0) {
            const adminIdentity = await wallet.get('admin');
            const provider = wallet.getProviderRegistry().getProvider(adminIdentity.type);
            const adminUser = await provider.getUserContext(adminIdentity, 'admin');

            const attrEntries = Object.entries(attrs).map(([name, value]) => ({
                name, value: String(value), ecert: true,
            }));

            const idService = ca.newIdentityService();
            await idService.update(username, { attrs: attrEntries }, adminUser);

            const user = await provider.getUserContext(existing, username);
            const attrReqs = Object.keys(attrs).map((name) => ({ name, optional: false }));
            const reenrollment = await ca.reenroll(user, { attr_reqs: attrReqs });

            await wallet.put(username, {
                credentials: {
                    certificate: reenrollment.certificate,
                    privateKey: reenrollment.key.toBytes(),
                },
                mspId: config.mspId,
                type: 'X.509',
            });
        }
        return { success: true, message: `Identity '${username}' already exists in wallet`, walletPath };
    }

    const adminIdentity = await wallet.get('admin');
    const provider = wallet.getProviderRegistry().getProvider(adminIdentity.type);
    const adminUser = await provider.getUserContext(adminIdentity, 'admin');

    let registerRequest = { affiliation: config.affiliation, enrollmentID: username, role: 'client' };
    let attrReqs = undefined;

    if (attrs && Object.keys(attrs).length > 0) {
        registerRequest.attrs = Object.entries(attrs).map(([name, value]) => ({
            name, value: String(value), ecert: true,
        }));
        attrReqs = Object.keys(attrs).map((name) => ({ name, optional: false }));
    }

    let enrollment;
    try {
        const secret = await ca.register(registerRequest, adminUser);
        enrollment = await ca.enroll({
            enrollmentID: username,
            enrollmentSecret: secret,
            attr_reqs: attrReqs,
        });
    } catch (regErr) {
        if (!regErr.message?.includes('is already registered')) throw regErr;
        const idService = ca.newIdentityService();
        const resetSecret = username + 'pw';
        await idService.update(username, {
            enrollmentSecret: resetSecret,
            attrs: registerRequest.attrs || [],
        }, adminUser);
        enrollment = await ca.enroll({
            enrollmentID: username,
            enrollmentSecret: resetSecret,
            attr_reqs: attrReqs,
        });
    }

    await wallet.put(username, {
        credentials: {
            certificate: enrollment.certificate,
            privateKey: enrollment.key.toBytes(),
        },
        mspId: config.mspId,
        type: 'X.509',
    });

    return { success: true, message: `Enrolled '${username}'`, walletPath };
};

const isUserRegistered = async (username, org) => {
    const walletPath = getWalletPath(org);
    const wallet = await Wallets.newFileSystemWallet(walletPath);
    const userIdentity = await wallet.get(username);
    return !!userIdentity;
};

module.exports = {
    getCCP,
    getWalletPath,
    tryParseJson,
    toArgsArray,
    getWalletAndIdentity,
    connectGateway,
    registerAndEnrollUser,
    isUserRegistered,
};
