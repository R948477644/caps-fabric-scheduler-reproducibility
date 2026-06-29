'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const { Gateway, Wallets } = require('fabric-network');

const config = {
    port: Number(process.env.SUPPLY_CHAIN_ADMIN_PORT || 8090),
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

async function createContract() {
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

function readJson(req) {
    return new Promise((resolve, reject) => {
        let body = '';
        req.on('data', chunk => {
            body += chunk;
            if (body.length > 1024 * 1024) {
                reject(new Error('request body is too large'));
                req.destroy();
            }
        });
        req.on('end', () => {
            try {
                resolve(body ? JSON.parse(body) : {});
            } catch (error) {
                reject(error);
            }
        });
        req.on('error', reject);
    });
}

function sendJson(res, statusCode, payload) {
    const body = JSON.stringify(payload, null, 2);
    res.writeHead(statusCode, {
        'content-type': 'application/json',
        'content-length': Buffer.byteLength(body)
    });
    res.end(body);
}

function positiveNumber(value, fallback) {
    const number = Number(value || fallback);
    if (!Number.isFinite(number) || number <= 0) throw new Error('parameters must be positive');
    return number;
}

function warehouse(index) {
    return `wh${String(index).padStart(3, '0')}`;
}

function sku(index) {
    return `sku${String(index).padStart(5, '0')}`;
}

async function initialize(contract, body) {
    const warehouseCount = positiveNumber(body.warehouseCount, 20);
    const skuCount = positiveNumber(body.skuCount, 50);
    const initialQuantity = positiveNumber(body.initialQuantity, 1000000);
    const batchCount = positiveNumber(body.batchCount, 100);
    await contract.submitTransaction(
        'InitSupplyChain',
        String(warehouseCount),
        String(skuCount),
        String(initialQuantity),
        String(batchCount)
    );
    return { operation: 'initialize', warehouseCount, skuCount, initialQuantity, batchCount };
}

async function verify(contract, body) {
    const warehouseCount = positiveNumber(body.warehouseCount, 20);
    const skuCount = positiveNumber(body.skuCount, 50);
    const initialQuantity = positiveNumber(body.initialQuantity, 1000000);
    const expectedPerSku = warehouseCount * initialQuantity;
    const keys = [];
    const skuTotals = {};
    const failures = [];
    for (let skuIndex = 0; skuIndex < skuCount; skuIndex++) {
        const skuId = sku(skuIndex);
        skuTotals[skuId] = 0;
        for (let warehouseIndex = 0; warehouseIndex < warehouseCount; warehouseIndex++) {
            keys.push(`inv:${warehouse(warehouseIndex)}:${skuId}`);
        }
    }
    const response = await contract.evaluateTransaction('AuditInventory', JSON.stringify(keys));
    const audit = JSON.parse(response.toString());
    for (const [key, item] of Object.entries(audit.items || {})) {
        if (item.quantity < 0) failures.push({ key, error: 'negative inventory', actual: item.quantity });
        skuTotals[item.sku] = (skuTotals[item.sku] || 0) + item.quantity;
    }
    for (const [skuId, total] of Object.entries(skuTotals)) {
        if (total !== expectedPerSku) failures.push({ sku: skuId, expected: expectedPerSku, actual: total });
    }
    return {
        operation: 'verify',
        invariant: 'per-SKU inventory conservation and non-negative quantity',
        expectedPerSku,
        checkedSkus: skuCount,
        valid: failures.length === 0,
        failures,
        skuTotals
    };
}

async function main() {
    const { gateway, contract } = await createContract();
    const server = http.createServer(async (req, res) => {
        if (req.method === 'GET' && req.url === '/health') {
            sendJson(res, 200, { ok: true, mode: 'supply-chain-admin' });
            return;
        }
        if (req.method !== 'POST' || !['/init', '/verify'].includes(req.url)) {
            sendJson(res, 404, { error: 'not found' });
            return;
        }
        try {
            const body = await readJson(req);
            const result = req.url === '/init'
                ? await initialize(contract, body)
                : await verify(contract, body);
            sendJson(res, result.valid === false ? 409 : 200, result);
        } catch (error) {
            sendJson(res, 500, { error: String(error && (error.stack || error.message || error)) });
        }
    });
    const shutdown = () => server.close(() => {
        gateway.disconnect();
        process.exit(0);
    });
    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);
    server.listen(config.port, '127.0.0.1', () => {
        console.log(`Supply-chain admin server listening on ${config.port}`);
    });
}

main().catch(error => {
    console.error(error);
    process.exit(1);
});
