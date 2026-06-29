'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const { execFile } = require('child_process');
const { Gateway, Wallets } = require('fabric-network');

const config = {
    port: Number(process.env.DRT_DISPATCHER_PORT || 8088),
    maxQueue: Number(process.env.DRT_MAX_QUEUE || 500),
    maxActive: Number(process.env.DRT_MAX_ACTIVE || 32),
    drtWindow: Number(process.env.DRT_WINDOW || 256),
    ageBoostMs: Number(process.env.DRT_AGE_BOOST_MS || 100),
    ageWeight: Number(process.env.DRT_AGE_WEIGHT || 10),
    conflictWeight: Number(process.env.DRT_CONFLICT_WEIGHT || 1),
    positionWeight: Number(process.env.DRT_POSITION_WEIGHT || 0.001),
    submitRetries: Number(process.env.FABRIC_SUBMIT_RETRIES || 3),
    submitter: process.env.FABRIC_SUBMITTER || 'sdk',
    peerBin: process.env.FABRIC_PEER_BIN || '/home/rd/fabric-exp/fabric-samples/bin/peer',
    fabricCfgPath: process.env.FABRIC_CFG_PATH || '/home/rd/fabric-exp/fabric-samples/config',
    testNetworkHome: process.env.TEST_NETWORK_HOME || '/home/rd/fabric-exp/fabric-samples/test-network',
    channelName: process.env.FABRIC_CHANNEL || 'vllchannel',
    chaincodeName: process.env.FABRIC_CHAINCODE || 'hotkey',
    mspId: process.env.FABRIC_MSP_ID || 'Org1MSP',
    identity: process.env.FABRIC_IDENTITY || 'User1',
    ccpPath: process.env.FABRIC_CCP ||
        '/home/rd/fabric-exp/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/connection-org1.yaml',
    certPath: process.env.FABRIC_CERT ||
        '/home/rd/fabric-exp/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/users/User1@org1.example.com/msp/signcerts/User1@org1.example.com-cert.pem',
    keyPath: process.env.FABRIC_KEY ||
        '/home/rd/fabric-exp/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/users/User1@org1.example.com/msp/keystore/priv_sk',
    endorsingPeers: (process.env.FABRIC_ENDORSING_PEERS || 'peer0.org1.example.com:7051,peer0.org2.example.com:9051')
        .split(',')
        .map(peer => peer.trim())
        .filter(Boolean),
    settleMs: Number(process.env.DRT_SETTLE_MS || 0)
};

config.ordererCa = `${config.testNetworkHome}/organizations/ordererOrganizations/example.com/tlsca/tlsca.example.com-cert.pem`;
config.org1Ca = `${config.testNetworkHome}/organizations/peerOrganizations/org1.example.com/tlsca/tlsca.org1.example.com-cert.pem`;
config.org2Ca = `${config.testNetworkHome}/organizations/peerOrganizations/org2.example.com/tlsca/tlsca.org2.example.com-cert.pem`;
config.org1AdminMsp = `${config.testNetworkHome}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp`;

function nowMs() {
    return Date.now();
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function isMvccFailure(err) {
    return String(err && (err.stack || err.message || err)).includes('MVCC_READ_CONFLICT');
}

function isTransientSubmitFailure(err) {
    const msg = String(err && (err.stack || err.message || err));
    return msg.includes('No endorsement plan available') ||
        msg.includes('SERVICE_UNAVAILABLE') ||
        msg.includes('UNAVAILABLE') ||
        msg.includes('DEADLINE_EXCEEDED') ||
        msg.includes('Failed, not able to reconnect');
}

function readJson(req) {
    return new Promise((resolve, reject) => {
        let body = '';
        req.on('data', chunk => {
            body += chunk;
            if (body.length > 1024 * 1024) {
                reject(new Error('Request body is too large'));
                req.destroy();
            }
        });
        req.on('end', () => {
            try {
                resolve(body ? JSON.parse(body) : {});
            } catch (err) {
                reject(err);
            }
        });
        req.on('error', reject);
    });
}

function sendJson(res, statusCode, payload) {
    if (res.writableEnded) {
        return;
    }
    const body = JSON.stringify(payload);
    res.writeHead(statusCode, {
        'content-type': 'application/json',
        'content-length': Buffer.byteLength(body)
    });
    res.end(body);
}

async function createContract() {
    const ccpText = fs.readFileSync(config.ccpPath, 'utf8');
    const ccp = ['.yaml', '.yml'].includes(path.extname(config.ccpPath).toLowerCase())
        ? yaml.load(ccpText)
        : JSON.parse(ccpText);
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
    return {
        gateway,
        network,
        contract: network.getContract(config.chaincodeName)
    };
}

class DrtReimplDispatcher {
    constructor(contract) {
        this.contract = contract;
        this.nextId = 1;
        this.queue = [];
        this.activeReaders = new Map();
        this.activeWriters = new Map();
        this.active = 0;
        this.stopping = false;
        this.resetMetrics();
    }

    resetMetrics() {
        this.metrics = {
            received: 0,
            accepted: 0,
            rejected: 0,
            succeeded: 0,
            failed: 0,
            mvccFailures: 0,
            transientRetries: 0,
            queueWaitTotalMs: 0,
            queueWaitMaxMs: 0,
            fabricTotalMs: 0,
            fabricMaxMs: 0,
            totalTotalMs: 0,
            totalMaxMs: 0,
            queueLengthTotal: 0,
            queueLengthSamples: 0,
            queueLengthMax: 0,
            readyChecks: 0,
            conflictBlocked: 0,
            dependencyWindows: 0,
            drtSelected: 0,
            dependencyEdges: 0,
            reorderedBypassed: 0
        };
    }

    resetRuntimeState() {
        this.queue = [];
        this.activeReaders.clear();
        this.activeWriters.clear();
        this.active = 0;
        this.stopping = false;
        this.resetMetrics();
    }

    enqueue(task) {
        this.metrics.received += 1;
        if (this.queue.length + this.active >= config.maxQueue + config.maxActive) {
            this.metrics.rejected += 1;
            sendJson(task.res, 429, { ok: false, error: 'drt_backpressure' });
            return;
        }

        task.id = this.nextId++;
        task.running = false;
        task.done = false;

        this.metrics.accepted += 1;
        this.queue.push(task);
        this.sampleQueue();
        this.drain();
    }

    sampleQueue() {
        const waiting = this.queue.length;
        this.metrics.queueLengthTotal += waiting;
        this.metrics.queueLengthSamples += 1;
        this.metrics.queueLengthMax = Math.max(this.metrics.queueLengthMax, waiting);
    }

    isReady(task) {
        this.metrics.readyChecks += 1;
        for (const key of task.readSet || []) {
            if ((this.activeWriters.get(key) || 0) > 0) {
                this.metrics.conflictBlocked += 1;
                return false;
            }
        }
        for (const key of task.writeSet) {
            if ((this.activeWriters.get(key) || 0) > 0 || (this.activeReaders.get(key) || 0) > 0) {
                this.metrics.conflictBlocked += 1;
                return false;
            }
        }
        return true;
    }

    reserve(task) {
        for (const key of task.readSet || []) {
            this.activeReaders.set(key, (this.activeReaders.get(key) || 0) + 1);
        }
        for (const key of task.writeSet) {
            this.activeWriters.set(key, (this.activeWriters.get(key) || 0) + 1);
        }
        task.running = true;
        this.active += 1;
    }

    drain() {
        if (this.stopping) {
            return;
        }

        while (this.active < config.maxActive) {
            const selected = this.selectDrtBatch(config.maxActive - this.active);
            if (selected.length === 0) {
                return;
            }
            this.metrics.drtSelected += selected.length;
            for (const task of selected) {
                const index = this.queue.indexOf(task);
                if (index >= 0) {
                    this.queue.splice(index, 1);
                }
                this.reserve(task);
                this.runTask(task).finally(() => {
                    this.completeTask(task);
                    this.sampleQueue();
                    this.drain();
                });
            }
        }
    }

    selectDrtBatch(capacity) {
        const window = this.queue.slice(0, Math.min(config.drtWindow, this.queue.length));
        if (window.length === 0 || capacity <= 0) {
            return [];
        }

        this.metrics.dependencyWindows += 1;
        const runnable = window.filter(task => this.isReady(task));
        if (runnable.length === 0) {
            return [];
        }

        const keyFrequency = new Map();
        for (const task of runnable) {
            for (const key of task.writeSet) {
                keyFrequency.set(key, (keyFrequency.get(key) || 0) + 1);
            }
        }

        const conflictCosts = new Map();
        let approximateEdges = 0;
        for (const task of runnable) {
            let conflictCost = 0;
            for (const key of task.writeSet) {
                const conflictsOnKey = (keyFrequency.get(key) || 1) - 1;
                conflictCost += conflictsOnKey;
                approximateEdges += conflictsOnKey;
            }
            conflictCosts.set(task.id, conflictCost);
        }
        this.metrics.dependencyEdges += Math.floor(approximateEdges / 2);

        const now = nowMs();
        const positions = new Map();
        for (let index = 0; index < window.length; index++) {
            positions.set(window[index].id, index);
        }

        runnable.sort((a, b) => {
            const scoreA = this.matchingScore(a, now, conflictCosts, positions);
            const scoreB = this.matchingScore(b, now, conflictCosts, positions);
            if (scoreA !== scoreB) {
                return scoreB - scoreA;
            }
            return a.id - b.id;
        });

        const selected = [];
        const selectedReaders = new Set();
        const selectedWriters = new Set();
        for (const task of runnable) {
            if (selected.length >= capacity) {
                break;
            }
            if (!isCompatibleWithSelected(task, selectedReaders, selectedWriters)) {
                continue;
            }
            selected.push(task);
            for (const key of task.readSet || []) {
                selectedReaders.add(key);
            }
            for (const key of task.writeSet || []) {
                selectedWriters.add(key);
            }
        }

        if (selected.length > 0) {
            const oldestSelected = Math.min(...selected.map(task => task.id));
            for (const task of window) {
                if (task.id < oldestSelected && !selected.includes(task)) {
                    this.metrics.reorderedBypassed += 1;
                }
            }
        }
        return selected;
    }

    matchingScore(task, now, conflictCosts, positions) {
        const ageScore = Math.floor((now - task.arrivalTime) / config.ageBoostMs);
        const conflictCost = conflictCosts.get(task.id) || 0;
        const position = positions.get(task.id) || 0;
        return (config.ageWeight * ageScore) -
            (config.conflictWeight * conflictCost) -
            (config.positionWeight * position);
    }

    completeTask(task) {
        task.done = true;
        for (const key of task.readSet || []) {
            const count = this.activeReaders.get(key) || 0;
            if (count <= 1) {
                this.activeReaders.delete(key);
            } else {
                this.activeReaders.set(key, count - 1);
            }
        }
        for (const key of task.writeSet) {
            const count = this.activeWriters.get(key) || 0;
            if (count <= 1) {
                this.activeWriters.delete(key);
            } else {
                this.activeWriters.set(key, count - 1);
            }
        }
        this.active -= 1;
    }

    async submitWithRetry(task) {
        let lastErr;
        for (let attempt = 0; attempt <= config.submitRetries; attempt++) {
            try {
                if (config.submitter === 'cli') {
                    await this.submitWithCli(task);
                } else {
                    const transaction = this.contract.createTransaction(task.functionName || 'Transfer');
                    const channel = this.contract.network.getChannel();
                    const endorsers = config.endorsingPeers
                        .map(peer => channel.getEndorser(peer))
                        .filter(Boolean);
                    if (endorsers.length > 0) {
                        transaction.setEndorsingPeers(endorsers);
                    }
                    await transaction.submit(...(task.args || [task.from, task.to, task.amount]));
                }
                if (config.settleMs > 0) {
                    await sleep(config.settleMs);
                }
                return;
            } catch (err) {
                lastErr = err;
                if (isMvccFailure(err) || !isTransientSubmitFailure(err) || attempt === config.submitRetries) {
                    throw err;
                }
                this.metrics.transientRetries += 1;
                await sleep(50 * (attempt + 1));
            }
        }
        throw lastErr;
    }

    submitWithCli(task) {
        const invokeSpec = JSON.stringify({
            function: task.functionName || 'Transfer',
            Args: task.args || [task.from, task.to, task.amount]
        });
        const args = [
            'chaincode', 'invoke',
            '-o', 'localhost:7050',
            '--ordererTLSHostnameOverride', 'orderer.example.com',
            '--tls',
            '--cafile', config.ordererCa,
            '-C', config.channelName,
            '-n', config.chaincodeName,
            '--peerAddresses', 'localhost:7051',
            '--tlsRootCertFiles', config.org1Ca,
            '--peerAddresses', 'localhost:9051',
            '--tlsRootCertFiles', config.org2Ca,
            '-c', invokeSpec
        ];
        const env = {
            ...process.env,
            PATH: `/usr/local/go/bin:/home/rd/fabric-exp/fabric-samples/bin:${process.env.PATH || ''}`,
            FABRIC_CFG_PATH: config.fabricCfgPath,
            CORE_PEER_TLS_ENABLED: 'true',
            CORE_PEER_LOCALMSPID: 'Org1MSP',
            CORE_PEER_TLS_ROOTCERT_FILE: config.org1Ca,
            CORE_PEER_MSPCONFIGPATH: config.org1AdminMsp,
            CORE_PEER_ADDRESS: 'localhost:7051'
        };

        return new Promise((resolve, reject) => {
            execFile(config.peerBin, args, {
                env,
                timeout: 120000,
                maxBuffer: 1024 * 1024
            }, (err, stdout, stderr) => {
                if (err) {
                    err.message = `${err.message}\nstdout=${stdout}\nstderr=${stderr}`;
                    reject(err);
                    return;
                }
                resolve();
            });
        });
    }

    async runTask(task) {
        const startFabric = nowMs();
        const queueWaitMs = startFabric - task.arrivalTime;
        this.metrics.queueWaitTotalMs += queueWaitMs;
        this.metrics.queueWaitMaxMs = Math.max(this.metrics.queueWaitMaxMs, queueWaitMs);

        try {
            await this.submitWithRetry(task);
            const done = nowMs();
            const fabricMs = done - startFabric;
            const totalMs = done - task.arrivalTime;
            this.metrics.fabricTotalMs += fabricMs;
            this.metrics.fabricMaxMs = Math.max(this.metrics.fabricMaxMs, fabricMs);
            this.metrics.totalTotalMs += totalMs;
            this.metrics.totalMaxMs = Math.max(this.metrics.totalMaxMs, totalMs);
            this.metrics.succeeded += 1;
            sendJson(task.res, 200, { ok: true, scheduler: 'drt-reimpl', queueWaitMs, fabricMs, totalMs });
        } catch (err) {
            if (isMvccFailure(err)) {
                this.metrics.mvccFailures += 1;
            }
            console.error('DRT-Reimpl task failed:', err && (err.stack || err.message) || err);
            this.metrics.failed += 1;
            sendJson(task.res, 500, {
                ok: false,
                error: isMvccFailure(err) ? 'MVCC_READ_CONFLICT' : 'fabric_submit_failed',
                message: String(err && err.message ? err.message : err)
            });
        }
    }

    snapshot() {
        const m = this.metrics;
        return {
            ...m,
            active: this.active,
            activeReadKeys: this.activeReaders.size,
            waiting: this.queue.length,
            activeWriteKeys: this.activeWriters.size,
            queuedTasks: this.queue.length + this.active,
            queueWaitAvgMs: m.succeeded + m.failed ? m.queueWaitTotalMs / (m.succeeded + m.failed) : 0,
            fabricAvgMs: m.succeeded ? m.fabricTotalMs / m.succeeded : 0,
            totalAvgMs: m.succeeded ? m.totalTotalMs / m.succeeded : 0,
            queueLengthAvg: m.queueLengthSamples ? m.queueLengthTotal / m.queueLengthSamples : 0
        };
    }
}

function buildTaskFromPayload(payload) {
    const functionName = String(payload.functionName || payload.function || 'Transfer');
    if (functionName === 'Transfer') {
        const from = String(payload.from || '');
        const to = String(payload.to || '');
        const amount = String(payload.amount || '1');
        if (!from || !to || from === to) {
            return null;
        }
        const writeSet = [...new Set([from, to])].sort();
        return {
            functionName,
            args: [from, to, amount],
            from,
            to,
            amount,
            readSet: writeSet,
            writeSet,
            keys: writeSet
        };
    }

    if (functionName === 'BatchTransfer') {
        const operations = Array.isArray(payload.operations) ? payload.operations : [];
        if (operations.length === 0) {
            return null;
        }
        const keys = [];
        const normalized = [];
        for (const op of operations) {
            const from = String(op.from || '');
            const to = String(op.to || '');
            const amount = Number(op.amount || payload.amount || 1);
            if (!from || !to || from === to || !Number.isFinite(amount) || amount <= 0) {
                return null;
            }
            normalized.push({ from, to, amount });
            keys.push(from, to);
        }
        const writeSet = [...new Set(keys)].sort();
        return {
            functionName,
            args: [JSON.stringify(normalized)],
            operations: normalized,
            readSet: writeSet,
            writeSet,
            keys: writeSet
        };
    }

    if (functionName === 'AuditAccounts') {
        const accounts = Array.isArray(payload.accounts) ? payload.accounts.map(String).filter(Boolean) : [];
        if (accounts.length === 0) {
            return null;
        }
        const readSet = [...new Set(accounts)].sort();
        return {
            functionName,
            args: [JSON.stringify(accounts)],
            accounts,
            readSet,
            writeSet: [],
            keys: []
        };
    }

    if (functionName === 'TransferInventory') {
        const source = String(payload.source || '');
        const destination = String(payload.destination || '');
        const sku = String(payload.sku || '');
        const quantity = Number(payload.quantity || 1);
        if (!source || !destination || source === destination || !sku || !Number.isFinite(quantity) || quantity <= 0) {
            return null;
        }
        const writeSet = [...new Set([inventoryKey(source, sku), inventoryKey(destination, sku)])].sort();
        return { functionName, args: [source, destination, sku, String(quantity)], readSet: writeSet, writeSet, keys: writeSet };
    }

    if (functionName === 'BatchTransferInventory') {
        const operations = Array.isArray(payload.operations) ? payload.operations : [];
        const keys = [];
        const normalized = [];
        for (const op of operations) {
            const source = String(op.source || '');
            const destination = String(op.destination || '');
            const sku = String(op.sku || '');
            const quantity = Number(op.quantity || payload.quantity || 1);
            if (!source || !destination || source === destination || !sku || !Number.isFinite(quantity) || quantity <= 0) {
                return null;
            }
            normalized.push({ source, destination, sku, quantity });
            keys.push(inventoryKey(source, sku), inventoryKey(destination, sku));
        }
        if (normalized.length === 0) {
            return null;
        }
        const writeSet = [...new Set(keys)].sort();
        return { functionName, args: [JSON.stringify(normalized)], readSet: writeSet, writeSet, keys: writeSet };
    }

    if (functionName === 'UpdateBatchStatus') {
        const batchId = String(payload.batchId || '');
        const nextStatus = String(payload.nextStatus || '');
        if (!batchId || !nextStatus) {
            return null;
        }
        const writeSet = [`batch:${batchId}`];
        return { functionName, args: [batchId, nextStatus], readSet: writeSet, writeSet, keys: writeSet };
    }

    if (functionName === 'AuditInventory') {
        const inventoryKeys = Array.isArray(payload.inventoryKeys) ? payload.inventoryKeys.map(String).filter(Boolean) : [];
        if (inventoryKeys.length === 0) {
            return null;
        }
        const readSet = [...new Set(inventoryKeys)].sort();
        return { functionName, args: [JSON.stringify(readSet)], readSet, writeSet: [], keys: [] };
    }

    return null;
}

function inventoryKey(warehouse, sku) {
    return `inv:${warehouse}:${sku}`;
}

function isCompatibleWithSelected(task, selectedReaders, selectedWriters) {
    for (const key of task.readSet || []) {
        if (selectedWriters.has(key)) {
            return false;
        }
    }
    for (const key of task.writeSet || []) {
        if (selectedWriters.has(key) || selectedReaders.has(key)) {
            return false;
        }
    }
    return true;
}

async function main() {
    const { gateway, contract } = await createContract();
    const dispatcher = new DrtReimplDispatcher(contract);

    const server = http.createServer(async (req, res) => {
        if (req.method === 'GET' && req.url === '/health') {
            sendJson(res, 200, {
                ok: true,
                mode: 'drt-reimpl-dispatcher',
                maxQueue: config.maxQueue,
                maxActive: config.maxActive,
                drtWindow: config.drtWindow,
                ageWeight: config.ageWeight,
                conflictWeight: config.conflictWeight,
                positionWeight: config.positionWeight
            });
            return;
        }

        if (req.method === 'GET' && req.url === '/metrics') {
            sendJson(res, 200, dispatcher.snapshot());
            return;
        }

        if (req.method === 'POST' && req.url === '/reset') {
            dispatcher.resetRuntimeState();
            sendJson(res, 200, { ok: true });
            return;
        }

        if (req.method === 'POST' && (req.url === '/transfer' || req.url === '/submit')) {
            let payload;
            try {
                payload = await readJson(req);
            } catch (err) {
                sendJson(res, 400, { ok: false, error: 'invalid_json', message: err.message });
                return;
            }

            const task = buildTaskFromPayload(payload);
            if (!task) {
                console.error('Invalid DRT payload:', JSON.stringify(payload));
                sendJson(res, 400, { ok: false, error: 'invalid_task' });
                return;
            }
            dispatcher.enqueue({
                ...task,
                arrivalTime: nowMs(),
                res
            });
            return;
        }

        sendJson(res, 404, { ok: false, error: 'not_found' });
    });

    server.headersTimeout = 120000;
    server.requestTimeout = 120000;
    server.listen(config.port, () => {
        console.log(`DRT-Reimpl dispatcher listening on ${config.port}`);
        console.log(`maxQueue=${config.maxQueue} maxActive=${config.maxActive} drtWindow=${config.drtWindow}`);
        console.log(`DRT score=age*${config.ageWeight}-conflict*${config.conflictWeight}-position*${config.positionWeight}`);
    });

    const shutdown = () => {
        dispatcher.stopping = true;
        server.close();
        gateway.disconnect();
        process.exit(0);
    };
    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});

