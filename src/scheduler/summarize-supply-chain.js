'use strict';

const fs = require('fs');
const path = require('path');

const args = parseArgs(process.argv.slice(2));
const root = path.resolve(args.root || 'results/supply-chain');
const outPrefix = path.resolve(args.out || path.join(root, 'summary'));

function parseArgs(argv) {
    const result = {};
    for (let i = 0; i < argv.length; i++) {
        if (!argv[i].startsWith('--')) continue;
        const key = argv[i].slice(2);
        result[key] = argv[i + 1];
        i += 1;
    }
    return result;
}

function walk(directory, filename, matches = []) {
    if (!fs.existsSync(directory)) return matches;
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
        const fullPath = path.join(directory, entry.name);
        if (entry.isDirectory()) walk(fullPath, filename, matches);
        else if (entry.name === filename) matches.push(fullPath);
    }
    return matches;
}

function number(value) {
    return Number.isFinite(Number(value)) ? Number(value) : 0;
}

function mean(values) {
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

function standardDeviation(values) {
    if (values.length < 2) return 0;
    const average = mean(values);
    const variance = values.reduce((sum, value) => sum + Math.pow(value - average, 2), 0) / (values.length - 1);
    return Math.sqrt(variance);
}

function parseRun(clientPath) {
    const runDirectory = path.dirname(clientPath);
    const relative = path.relative(root, runDirectory).split(path.sep);
    if (relative.length < 4) return null;
    const [workload, scheduler, rateLabel, repeatLabel] = relative;
    const client = JSON.parse(fs.readFileSync(clientPath, 'utf8'));
    const schedulerMetricsPath = path.join(runDirectory, 'scheduler-metrics.json');
    const invariantPath = path.join(runDirectory, 'invariant-check.json');
    const schedulerMetrics = fs.existsSync(schedulerMetricsPath)
        ? JSON.parse(fs.readFileSync(schedulerMetricsPath, 'utf8'))
        : {};
    const invariant = fs.existsSync(invariantPath)
        ? JSON.parse(fs.readFileSync(invariantPath, 'utf8'))
        : { valid: false };
    const committed = number(client.statusCounts && client.statusCounts['200']);
    const elapsedSeconds = number(client.elapsedMs) / 1000;
    return {
        workload,
        scheduler,
        offeredLoad: number(rateLabel.replace('tps', '')),
        repeat: number(repeatLabel.replace('repeat-', '')),
        sent: number(client.sent),
        localDropped: number(client.localDropped),
        committed,
        goodput: elapsedSeconds > 0 ? committed / elapsedSeconds : 0,
        validRatio: number(client.sent) > 0 ? committed / number(client.sent) : 0,
        admissionRejected: number(client.statusCounts && client.statusCounts['429']),
        queueTimeout: number(client.statusCounts && client.statusCounts['408']),
        failed: number(client.statusCounts && client.statusCounts['500']) + number(client.statusCounts && client.statusCounts['599']),
        latencyAvgMs: number(client.latencyAvgMs),
        committedLatencyAvgMs: number(schedulerMetrics.totalAvgMs || schedulerMetrics.fabricAvgMs),
        queueWaitAvgMs: number(schedulerMetrics.queueWaitAvgMs),
        mvccFailures: number(schedulerMetrics.mvccFailures),
        mvccInvalidRatio: number(client.sent) > 0 ? number(schedulerMetrics.mvccFailures) / number(client.sent) : 0,
        invariantValid: invariant.valid === true
    };
}

function summarize(runs) {
    const groups = new Map();
    for (const run of runs) {
        const key = `${run.workload}|${run.scheduler}|${run.offeredLoad}`;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(run);
    }
    const metrics = [
        'committed',
        'goodput',
        'validRatio',
        'admissionRejected',
        'queueTimeout',
        'failed',
        'localDropped',
        'latencyAvgMs',
        'committedLatencyAvgMs',
        'queueWaitAvgMs',
        'mvccFailures',
        'mvccInvalidRatio'
    ];
    return [...groups.values()].map(group => {
        const row = {
            workload: group[0].workload,
            scheduler: group[0].scheduler,
            offeredLoad: group[0].offeredLoad,
            repeats: group.length,
            invariantPasses: group.filter(run => run.invariantValid).length
        };
        for (const metric of metrics) {
            const values = group.map(run => run[metric]);
            row[`${metric}Mean`] = mean(values);
            row[`${metric}Std`] = standardDeviation(values);
        }
        return row;
    }).sort((a, b) =>
        a.workload.localeCompare(b.workload) ||
        a.offeredLoad - b.offeredLoad ||
        a.scheduler.localeCompare(b.scheduler)
    );
}

function csv(rows) {
    if (rows.length === 0) return '';
    const headers = Object.keys(rows[0]);
    return [
        headers.join(','),
        ...rows.map(row => headers.map(header => row[header]).join(','))
    ].join('\n') + '\n';
}

const runs = walk(root, 'client.json').map(parseRun).filter(Boolean);
const summary = summarize(runs);
fs.mkdirSync(path.dirname(outPrefix), { recursive: true });
fs.writeFileSync(`${outPrefix}-runs.json`, JSON.stringify(runs, null, 2));
fs.writeFileSync(`${outPrefix}.json`, JSON.stringify(summary, null, 2));
fs.writeFileSync(`${outPrefix}.csv`, csv(summary));
console.log(JSON.stringify({ root, runCount: runs.length, groupCount: summary.length, outPrefix }, null, 2));
