'use strict';

const http = require('http');
const fs = require('fs');

const args = parseArgs(process.argv.slice(2));

const config = {
    url: args.url || 'http://127.0.0.1:8084/submit',
    clients: Number(args.clients || 100),
    tps: Number(args.tps || 50),
    duration: Number(args.duration || 60),
    accountCount: Number(args.accountCount || 1000),
    hotAccountCount: Number(args.hotAccountCount || 100),
    amount: Number(args.amount || 1),
    workload: String(args.workload || 'w2'),
    batchSize: Number(args.batchSize || 4),
    auditSize: Number(args.auditSize || 8),
    transferPct: Number(args.transferPct || 70),
    auditPct: Number(args.auditPct || 20),
    batchPct: Number(args.batchPct || 10),
    timeoutMs: Number(args.timeoutMs || 240000),
    maxOutstanding: Number(args.maxOutstanding || 10000),
    maxSockets: Number(args.maxSockets || args.maxOutstanding || 10000),
    out: args.out || ''
};

const agent = new http.Agent({
    keepAlive: true,
    maxSockets: Math.max(32, config.maxSockets)
});

function parseArgs(argv) {
    const result = {};
    for (let i = 0; i < argv.length; i++) {
        const item = argv[i];
        if (!item.startsWith('--')) {
            continue;
        }
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

function account(index) {
    return `acct${String(index).padStart(6, '0')}`;
}

function hotIndex(sequence, salt = 0) {
    const hot = Math.max(2, Math.min(config.hotAccountCount, config.accountCount));
    return (sequence * 17 + salt * 31 + Math.floor(sequence / Math.max(1, config.clients))) % hot;
}

function transferPayload(sequence) {
    const hot = Math.max(2, Math.min(config.hotAccountCount, config.accountCount));
    const fromIndex = hotIndex(sequence, 0);
    const toIndex = (fromIndex + 1 + (sequence % (hot - 1))) % hot;
    return {
        functionName: 'Transfer',
        from: account(fromIndex),
        to: account(toIndex),
        amount: String(config.amount)
    };
}

function batchTransferPayload(sequence) {
    const hot = Math.max(2, Math.min(config.hotAccountCount, config.accountCount));
    const operations = [];
    const usedPairs = new Set();
    for (let i = 0; i < config.batchSize; i++) {
        const fromIndex = hotIndex(sequence + i * 13, i);
        const toIndex = (fromIndex + 1 + ((sequence + i * 7) % (hot - 1))) % hot;
        const pair = `${fromIndex}:${toIndex}`;
        if (fromIndex === toIndex || usedPairs.has(pair)) {
            continue;
        }
        usedPairs.add(pair);
        operations.push({
            from: account(fromIndex),
            to: account(toIndex),
            amount: config.amount
        });
    }
    return {
        functionName: 'BatchTransfer',
        operations
    };
}

function auditPayload(sequence) {
    const accounts = [];
    for (let i = 0; i < config.auditSize; i++) {
        accounts.push(account(hotIndex(sequence + i * 19, i)));
    }
    return {
        functionName: 'AuditAccounts',
        accounts: [...new Set(accounts)]
    };
}

function workloadPayload(sequence) {
    if (config.workload === 'w2') {
        return batchTransferPayload(sequence);
    }
    if (config.workload === 'w3') {
        const bucket = (sequence * 37) % 100;
        if (bucket < config.transferPct) {
            return transferPayload(sequence);
        }
        if (bucket < config.transferPct + config.auditPct) {
            return auditPayload(sequence);
        }
        return batchTransferPayload(sequence);
    }
    return transferPayload(sequence);
}

function postJson(payload) {
    const target = new URL(config.url);
    const body = JSON.stringify(payload);
    const start = Date.now();
    const options = {
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
    };

    return new Promise(resolve => {
        const req = http.request(options, res => {
            res.resume();
            res.on('end', () => {
                resolve({
                    statusCode: res.statusCode,
                    latencyMs: Date.now() - start
                });
            });
        });
        req.on('timeout', () => {
            req.destroy();
            resolve({ statusCode: 408, latencyMs: Date.now() - start });
        });
        req.on('error', () => {
            resolve({ statusCode: 599, latencyMs: Date.now() - start });
        });
        req.write(body);
        req.end();
    });
}

async function main() {
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
        const due = start + Math.floor(i * intervalMs);
        const wait = due - Date.now();
        if (wait > 0) {
            await sleep(wait);
        }

        const outstanding = summary.sent - summary.completed;
        if (outstanding >= config.maxOutstanding) {
            summary.localDropped += 1;
            continue;
        }

        const payload = workloadPayload(i);
        summary.sent += 1;
        summary.functionCounts[payload.functionName] = (summary.functionCounts[payload.functionName] || 0) + 1;
        const promise = postJson(payload).then(result => {
            summary.completed += 1;
            const key = String(result.statusCode);
            summary.statusCounts[key] = (summary.statusCounts[key] || 0) + 1;
            summary.latencyTotalMs += result.latencyMs;
            summary.latencyMaxMs = Math.max(summary.latencyMaxMs, result.latencyMs);
        });
        promises.push(promise);
    }

    await Promise.all(promises);
    const elapsedMs = Date.now() - start;
    summary.elapsedMs = elapsedMs;
    summary.sendRate = summary.sent / (config.duration || 1);
    summary.completionRate = summary.completed / (elapsedMs / 1000);
    summary.latencyAvgMs = summary.completed ? summary.latencyTotalMs / summary.completed : 0;

    const output = JSON.stringify(summary, null, 2);
    if (config.out) {
        fs.writeFileSync(config.out, output);
    }
    console.log(output);
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});
