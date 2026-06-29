'use strict';

const http = require('http');
const fs = require('fs');

const args = parseArgs(process.argv.slice(2));
const config = {
    url: args.url || 'http://127.0.0.1:8086/submit',
    clients: Number(args.clients || 100),
    tps: Number(args.tps || 300),
    duration: Number(args.duration || 20),
    workload: String(args.workload || 'sc-w3').toLowerCase(),
    warehouseCount: Number(args.warehouseCount || 20),
    skuCount: Number(args.skuCount || 50),
    hotSkuCount: Number(args.hotSkuCount || 10),
    batchCount: Number(args.batchCount || 10000),
    batchSize: Number(args.batchSize || 4),
    auditSize: Number(args.auditSize || 8),
    quantity: Number(args.quantity || 1),
    zipfAlpha: Number(args.zipfAlpha || 1.2),
    timeoutMs: Number(args.timeoutMs || 240000),
    maxOutstanding: Number(args.maxOutstanding || 10000),
    maxSockets: Number(args.maxSockets || args.maxOutstanding || 10000),
    preview: Number(args.preview || 0),
    out: args.out || ''
};

validateConfig();

const agent = new http.Agent({
    keepAlive: true,
    maxSockets: Math.max(32, config.maxSockets)
});
const zipfCdf = buildZipfCdf(Math.min(config.hotSkuCount, config.skuCount), config.zipfAlpha);

function parseArgs(argv) {
    const result = {};
    for (let i = 0; i < argv.length; i++) {
        const item = argv[i];
        if (!item.startsWith('--')) continue;
        const key = item.slice(2);
        const next = argv[i + 1];
        if (!next || next.startsWith('--')) {
            result[key] = true;
        } else {
            result[key] = next;
            i += 1;
        }
    }
    return result;
}

function validateConfig() {
    for (const [name, value] of Object.entries({
        clients: config.clients,
        tps: config.tps,
        duration: config.duration,
        warehouseCount: config.warehouseCount,
        skuCount: config.skuCount,
        hotSkuCount: config.hotSkuCount,
        batchCount: config.batchCount,
        batchSize: config.batchSize,
        auditSize: config.auditSize,
        quantity: config.quantity
    })) {
        if (!Number.isFinite(value) || value <= 0) {
            throw new Error(`${name} must be positive`);
        }
    }
    if (config.warehouseCount < 2) {
        throw new Error('warehouseCount must be at least 2');
    }
    if (!['sc-w1', 'sc-w2', 'sc-w3'].includes(config.workload)) {
        throw new Error(`unknown supply-chain workload: ${config.workload}`);
    }
}

function warehouse(index) {
    return `wh${String(index % config.warehouseCount).padStart(3, '0')}`;
}

function sku(index) {
    return `sku${String(index % config.skuCount).padStart(5, '0')}`;
}

function inventoryKey(warehouseId, skuId) {
    return `inv:${warehouseId}:${skuId}`;
}

function mix32(value) {
    let x = value | 0;
    x ^= x >>> 16;
    x = Math.imul(x, 0x7feb352d);
    x ^= x >>> 15;
    x = Math.imul(x, 0x846ca68b);
    x ^= x >>> 16;
    return x >>> 0;
}

function deterministicUnit(sequence, salt = 0) {
    return mix32(sequence + Math.imul(salt + 1, 0x9e3779b1)) / 0x100000000;
}

function buildZipfCdf(size, alpha) {
    const weights = [];
    let total = 0;
    for (let rank = 1; rank <= size; rank++) {
        const weight = 1 / Math.pow(rank, alpha);
        weights.push(weight);
        total += weight;
    }
    let cumulative = 0;
    return weights.map(weight => {
        cumulative += weight / total;
        return cumulative;
    });
}

function zipfSkuIndex(sequence, salt = 0) {
    const value = deterministicUnit(sequence, salt);
    const index = zipfCdf.findIndex(boundary => value <= boundary);
    return index < 0 ? zipfCdf.length - 1 : index;
}

function uniformTransfer(sequence) {
    const sourceIndex = mix32(sequence * 17 + 3) % config.warehouseCount;
    const destinationIndex = (sourceIndex + 1 + (mix32(sequence * 31 + 7) % (config.warehouseCount - 1))) % config.warehouseCount;
    return {
        functionName: 'TransferInventory',
        source: warehouse(sourceIndex),
        destination: warehouse(destinationIndex),
        sku: sku(mix32(sequence * 43 + 11) % config.skuCount),
        quantity: config.quantity
    };
}

function hotspotTransfer(sequence) {
    const sourceIndex = mix32(sequence * 17 + 5) % config.warehouseCount;
    const destinationIndex = (sourceIndex + 1 + (mix32(sequence * 29 + 13) % (config.warehouseCount - 1))) % config.warehouseCount;
    return {
        functionName: 'TransferInventory',
        source: warehouse(sourceIndex),
        destination: warehouse(destinationIndex),
        sku: sku(zipfSkuIndex(sequence, 17)),
        quantity: config.quantity
    };
}

function centralWarehouseTransfer(sequence) {
    const destinationIndex = 1 + (mix32(sequence * 23 + 19) % (config.warehouseCount - 1));
    return {
        functionName: 'TransferInventory',
        source: warehouse(0),
        destination: warehouse(destinationIndex),
        sku: sku(zipfSkuIndex(sequence, 23)),
        quantity: config.quantity
    };
}

function batchDistribution(sequence) {
    const operations = [];
    const used = new Set();
    for (let i = 0; i < config.batchSize; i++) {
        const destinationIndex = 1 + (mix32(sequence * 37 + i * 41) % (config.warehouseCount - 1));
        const skuIndex = zipfSkuIndex(sequence + i * 53, i + 31);
        const key = `${destinationIndex}:${skuIndex}`;
        if (used.has(key)) continue;
        used.add(key);
        operations.push({
            source: warehouse(0),
            destination: warehouse(destinationIndex),
            sku: sku(skuIndex),
            quantity: config.quantity
        });
    }
    return { functionName: 'BatchTransferInventory', operations };
}

function inventoryAudit(sequence, hotspot) {
    const keys = [];
    for (let i = 0; i < config.auditSize; i++) {
        const warehouseIndex = mix32(sequence * 47 + i * 59) % config.warehouseCount;
        const skuIndex = hotspot
            ? zipfSkuIndex(sequence + i * 61, i + 43)
            : mix32(sequence * 67 + i * 71) % config.skuCount;
        keys.push(inventoryKey(warehouse(warehouseIndex), sku(skuIndex)));
    }
    return {
        functionName: 'AuditInventory',
        inventoryKeys: [...new Set(keys)]
    };
}

function batchStatusUpdate(sequence) {
    const hotBatchCount = Math.max(1, Math.min(100, config.batchCount));
    const batchIndex = mix32(sequence * 73 + 29) % hotBatchCount;
    return {
        functionName: 'UpdateBatchStatus',
        batchId: `batch${String(batchIndex).padStart(6, '0')}`,
        nextStatus: 'DISPATCHED'
    };
}

function workloadPayload(sequence) {
    const bucket = mix32(sequence * 79 + 37) % 100;
    if (config.workload === 'sc-w1') {
        return bucket < 80 ? uniformTransfer(sequence) : inventoryAudit(sequence, false);
    }
    if (config.workload === 'sc-w2') {
        return bucket < 80 ? hotspotTransfer(sequence) : inventoryAudit(sequence, true);
    }
    if (bucket < 60) return centralWarehouseTransfer(sequence);
    if (bucket < 80) return batchDistribution(sequence);
    if (bucket < 95) return inventoryAudit(sequence, true);
    return batchStatusUpdate(sequence);
}

function postJson(payload) {
    const target = new URL(config.url);
    const body = JSON.stringify(payload);
    const start = Date.now();
    return new Promise(resolve => {
        const req = http.request({
            hostname: target.hostname,
            port: target.port || 80,
            path: target.pathname,
            method: 'POST',
            agent,
            timeout: config.timeoutMs,
            headers: {
                'content-type': 'application/json',
                'content-length': Buffer.byteLength(body)
            }
        }, res => {
            res.resume();
            res.on('end', () => resolve({ statusCode: res.statusCode, latencyMs: Date.now() - start }));
        });
        req.on('timeout', () => {
            req.destroy();
            resolve({ statusCode: 408, latencyMs: Date.now() - start });
        });
        req.on('error', () => resolve({ statusCode: 599, latencyMs: Date.now() - start }));
        req.write(body);
        req.end();
    });
}

async function main() {
    if (config.preview > 0) {
        const preview = [];
        for (let i = 0; i < config.preview; i++) {
            preview.push(workloadPayload(i));
        }
        console.log(JSON.stringify(preview, null, 2));
        return;
    }
    const totalToSend = Math.floor(config.tps * config.duration);
    const intervalMs = 1000 / config.tps;
    const start = Date.now();
    const promises = [];
    const summary = {
        config,
        sent: 0,
        localDropped: 0,
        completed: 0,
        statusCounts: {},
        functionCounts: {},
        latencyTotalMs: 0,
        latencyMaxMs: 0
    };

    for (let i = 0; i < totalToSend; i++) {
        const wait = start + Math.floor(i * intervalMs) - Date.now();
        if (wait > 0) await sleep(wait);
        if (summary.sent - summary.completed >= config.maxOutstanding) {
            summary.localDropped += 1;
            continue;
        }
        const payload = workloadPayload(i);
        summary.sent += 1;
        summary.functionCounts[payload.functionName] = (summary.functionCounts[payload.functionName] || 0) + 1;
        promises.push(postJson(payload).then(result => {
            summary.completed += 1;
            const status = String(result.statusCode);
            summary.statusCounts[status] = (summary.statusCounts[status] || 0) + 1;
            summary.latencyTotalMs += result.latencyMs;
            summary.latencyMaxMs = Math.max(summary.latencyMaxMs, result.latencyMs);
        }));
    }

    await Promise.all(promises);
    summary.elapsedMs = Date.now() - start;
    summary.sendRate = summary.sent / config.duration;
    summary.completionRate = summary.completed / (summary.elapsedMs / 1000);
    summary.latencyAvgMs = summary.completed ? summary.latencyTotalMs / summary.completed : 0;
    const output = JSON.stringify(summary, null, 2);
    if (config.out) fs.writeFileSync(config.out, output);
    console.log(output);
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

main().catch(error => {
    console.error(error);
    process.exit(1);
});
