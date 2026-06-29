'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const { Gateway, Wallets } = require('fabric-network');

// fabric-network can surface a duplicate commit-listener rejection after
// transaction.submit() has already rejected and been handled below.
process.on('unhandledRejection', error => {
    const message = String(error && (error.stack || error.message || error));
    if (message.includes('MVCC_READ_CONFLICT')) {
        return;
    }
    console.error('Unhandled Fabric promise rejection:', message);
});

const config = {
    port: Number(process.env.NATIVE_FABRIC_GATEWAY_PORT || 8089),
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

function freshMetrics() {
    return {
        received: 0,
        succeeded: 0,
        failed: 0,
        mvccFailures: 0,
        active: 0,
        activeMax: 0,
        fabricTotalMs: 0,
        fabricMaxMs: 0
    };
}

let metrics = freshMetrics();

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
    const body = JSON.stringify(payload);
    res.writeHead(statusCode, {
        'content-type': 'application/json',
        'content-length': Buffer.byteLength(body)
    });
    res.end(body);
}

function invocationFromPayload(payload) {
    const functionName = String(payload.functionName || '');
    if (functionName === 'TransferInventory') {
        return [functionName, [
            String(payload.source || ''),
            String(payload.destination || ''),
            String(payload.sku || ''),
            String(payload.quantity || 1)
        ]];
    }
    if (functionName === 'BatchTransferInventory') {
        return [functionName, [JSON.stringify(payload.operations || [])]];
    }
    if (functionName === 'UpdateBatchStatus') {
        return [functionName, [String(payload.batchId || ''), String(payload.nextStatus || '')]];
    }
    if (functionName === 'AuditInventory') {
        return [functionName, [JSON.stringify(payload.inventoryKeys || [])]];
    }
    return null;
}

async function main() {
    const { gateway, contract } = await createContract();
    const server = http.createServer(async (req, res) => {
        if (req.method === 'GET' && req.url === '/health') {
            sendJson(res, 200, { ok: true, mode: 'native-fabric-gateway' });
            return;
        }
        if (req.method === 'GET' && req.url === '/metrics') {
            sendJson(res, 200, {
                ...metrics,
                fabricAvgMs: metrics.succeeded ? metrics.fabricTotalMs / metrics.succeeded : 0
            });
            return;
        }
        if (req.method === 'POST' && req.url === '/reset') {
            metrics = freshMetrics();
            sendJson(res, 200, { ok: true });
            return;
        }
        if (req.method !== 'POST' || req.url !== '/submit') {
            sendJson(res, 404, { error: 'not found' });
            return;
        }

        let invocation;
        try {
            invocation = invocationFromPayload(await readJson(req));
        } catch (error) {
            sendJson(res, 400, { error: error.message });
            return;
        }
        if (!invocation || invocation[1].some(value => value === '')) {
            sendJson(res, 400, { error: 'invalid transaction payload' });
            return;
        }

        metrics.received += 1;
        metrics.active += 1;
        metrics.activeMax = Math.max(metrics.activeMax, metrics.active);
        const startedAt = Date.now();
        try {
            const transaction = contract.createTransaction(invocation[0]);
            await transaction.submit(...invocation[1]);
            const elapsed = Date.now() - startedAt;
            metrics.succeeded += 1;
            metrics.fabricTotalMs += elapsed;
            metrics.fabricMaxMs = Math.max(metrics.fabricMaxMs, elapsed);
            sendJson(res, 200, { ok: true, fabricMs: elapsed });
        } catch (error) {
            const message = String(error && (error.stack || error.message || error));
            metrics.failed += 1;
            if (message.includes('MVCC_READ_CONFLICT')) metrics.mvccFailures += 1;
            sendJson(res, 500, {
                ok: false,
                mvcc: message.includes('MVCC_READ_CONFLICT'),
                error: message
            });
        } finally {
            metrics.active -= 1;
        }
    });

    const shutdown = () => server.close(() => {
        gateway.disconnect();
        process.exit(0);
    });
    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);
    server.listen(config.port, '127.0.0.1', () => {
        console.log(`Native Fabric gateway listening on ${config.port}`);
    });
}

main().catch(error => {
    console.error(error);
    process.exit(1);
});
