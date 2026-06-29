'use strict';

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const { Gateway, Wallets } = require('fabric-network');

const args = parseArgs(process.argv.slice(2));
const config = {
    command: String(args.command || 'verify'),
    warehouseCount: Number(args.warehouseCount || 20),
    skuCount: Number(args.skuCount || 50),
    initialQuantity: Number(args.initialQuantity || 1000000),
    batchCount: Number(args.batchCount || 10000),
    channelName: process.env.FABRIC_CHANNEL || 'vllchannel',
    chaincodeName: process.env.FABRIC_CHAINCODE || 'hotkey',
    mspId: process.env.FABRIC_MSP_ID || 'Org1MSP',
    identity: process.env.FABRIC_IDENTITY || 'User1',
    ccpPath: process.env.FABRIC_CCP ||
        '/home/rd/fabric-exp/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/connection-org1.yaml',
    certPath: process.env.FABRIC_CERT ||
        '/home/rd/fabric-exp/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/users/User1@org1.example.com/msp/signcerts/User1@org1.example.com-cert.pem',
    keyPath: process.env.FABRIC_KEY ||
        '/home/rd/fabric-exp/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/users/User1@org1.example.com/msp/keystore/priv_sk'
};

function parseArgs(argv) {
    const result = {};
    for (let i = 0; i < argv.length; i++) {
        if (!argv[i].startsWith('--')) continue;
        const key = argv[i].slice(2);
        const value = argv[i + 1];
        if (!value || value.startsWith('--')) {
            result[key] = true;
        } else {
            result[key] = value;
            i += 1;
        }
    }
    return result;
}

async function connect() {
    const text = fs.readFileSync(config.ccpPath, 'utf8');
    const ccp = ['.yaml', '.yml'].includes(path.extname(config.ccpPath).toLowerCase())
        ? yaml.load(text)
        : JSON.parse(text);
    const wallet = await Wallets.newInMemoryWallet();
    await wallet.put(config.identity, {
        credentials: {
            certificate: fs.readFileSync(config.certPath, 'utf8'),
            privateKey: fs.readFileSync(config.keyPath, 'utf8')
        },
        mspId: config.mspId,
        type: 'X.509'
    });
    const gateway = new Gateway();
    await gateway.connect(ccp, {
        wallet,
        identity: config.identity,
        discovery: { enabled: true, asLocalhost: true }
    });
    const network = await gateway.getNetwork(config.channelName);
    return { gateway, contract: network.getContract(config.chaincodeName) };
}

function warehouse(index) {
    return `wh${String(index).padStart(3, '0')}`;
}

function sku(index) {
    return `sku${String(index).padStart(5, '0')}`;
}

async function initialize(contract) {
    await contract.submitTransaction(
        'InitSupplyChain',
        String(config.warehouseCount),
        String(config.skuCount),
        String(config.initialQuantity),
        String(config.batchCount)
    );
    return {
        operation: 'initialize',
        warehouseCount: config.warehouseCount,
        skuCount: config.skuCount,
        initialQuantity: config.initialQuantity,
        batchCount: config.batchCount
    };
}

async function verify(contract) {
    const expectedPerSku = config.warehouseCount * config.initialQuantity;
    const failures = [];
    const skuTotals = {};
    const keys = [];
    for (let skuIndex = 0; skuIndex < config.skuCount; skuIndex++) {
        const skuId = sku(skuIndex);
        skuTotals[skuId] = 0;
        for (let warehouseIndex = 0; warehouseIndex < config.warehouseCount; warehouseIndex++) {
            keys.push(`inv:${warehouse(warehouseIndex)}:${skuId}`);
        }
    }
    const response = await contract.evaluateTransaction('AuditInventory', JSON.stringify(keys));
    const audit = JSON.parse(response.toString());
    for (const [key, item] of Object.entries(audit.items || {})) {
        if (item.quantity < 0) {
            failures.push({ key, error: 'negative inventory', actual: item.quantity });
        }
        skuTotals[item.sku] = (skuTotals[item.sku] || 0) + item.quantity;
    }
    for (const [skuId, total] of Object.entries(skuTotals)) {
        if (total !== expectedPerSku) {
            failures.push({ sku: skuId, expected: expectedPerSku, actual: total });
        }
    }
    return {
        operation: 'verify',
        invariant: 'sum of warehouse inventory for each SKU is conserved and every quantity is non-negative',
        expectedPerSku,
        checkedSkus: config.skuCount,
        valid: failures.length === 0,
        failures,
        skuTotals
    };
}

async function main() {
    const { gateway, contract } = await connect();
    try {
        const result = config.command === 'init'
            ? await initialize(contract)
            : await verify(contract);
        console.log(JSON.stringify(result, null, 2));
        if (result.valid === false) process.exitCode = 2;
    } finally {
        gateway.disconnect();
    }
}

main().catch(error => {
    console.error(error);
    process.exit(1);
});
