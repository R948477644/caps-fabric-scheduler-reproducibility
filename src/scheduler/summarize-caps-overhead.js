'use strict';

const fs = require('fs');
const path = require('path');

const args = parseArgs(process.argv.slice(2));
const root = path.resolve(args.root || 'results/caps-overhead');
const outPrefix = path.resolve(args.out || path.join(root, 'caps-overhead-summary'));

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

function readJson(file) {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function listDirs(dir) {
    if (!fs.existsSync(dir)) return [];
    return fs.readdirSync(dir, { withFileTypes: true })
        .filter(entry => entry.isDirectory())
        .map(entry => entry.name)
        .sort();
}

function mean(values) {
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

function std(values) {
    if (values.length <= 1) return 0;
    const avg = mean(values);
    const variance = values.reduce((sum, value) => sum + Math.pow(value - avg, 2), 0) / (values.length - 1);
    return Math.sqrt(variance);
}

function fmt(value, digits = 2) {
    return Number.isFinite(value) ? value.toFixed(digits) : '0.00';
}

const rows = [];
for (const workload of listDirs(root)) {
    const workloadDir = path.join(root, workload);
    for (const rateDirName of listDirs(workloadDir)) {
        const rate = Number(rateDirName.replace(/tps$/, ''));
        const rateDir = path.join(workloadDir, rateDirName);
        for (const repeatDirName of listDirs(rateDir)) {
            if (!repeatDirName.startsWith('repeat-')) continue;
            const runDir = path.join(rateDir, repeatDirName);
            const metricsFile = path.join(runDir, 'scheduler-metrics.json');
            const clientFile = path.join(runDir, 'client.json');
            const invariantFile = path.join(runDir, 'invariant-check.json');
            if (!fs.existsSync(metricsFile) || !fs.existsSync(clientFile)) continue;
            const metrics = readJson(metricsFile);
            const client = readJson(clientFile);
            const invariant = fs.existsSync(invariantFile) ? readJson(invariantFile) : {};
            rows.push({
                workload,
                rate,
                repeat: Number(repeatDirName.replace('repeat-', '')),
                validInvariant: invariant.valid === true,
                sent: client.sent || 0,
                completed: client.completed || 0,
                committed: metrics.succeeded || 0,
                rejected: metrics.rejected || 0,
                mvccFailures: metrics.mvccFailures || 0,
                schedulingAvgMs: metrics.schedulingAvgMs || 0,
                schedulingP95Ms: metrics.schedulingP95Ms || 0,
                schedulingMaxMs: metrics.schedulingMaxMs || 0,
                schedulingEvents: metrics.schedulingEvents || 0,
                schedulerCpuPercentAvg: metrics.schedulerCpuPercentAvg || 0,
                schedulerCpuPercentMax: metrics.schedulerCpuPercentMax || 0,
                schedulerRssMbAvg: metrics.schedulerRssMbAvg || 0,
                schedulerRssMbMax: metrics.schedulerRssMbMax || 0
            });
        }
    }
}

const groups = new Map();
for (const row of rows) {
    const key = `${row.workload}|${row.rate}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
}

const summary = [];
for (const [key, groupRows] of [...groups.entries()].sort()) {
    const [workload, rateText] = key.split('|');
    const pick = field => groupRows.map(row => row[field]);
    summary.push({
        workload,
        rate: Number(rateText),
        repeats: groupRows.length,
        committedMean: mean(pick('committed')),
        committedStd: std(pick('committed')),
        schedulingAvgMsMean: mean(pick('schedulingAvgMs')),
        schedulingAvgMsStd: std(pick('schedulingAvgMs')),
        schedulingP95MsMean: mean(pick('schedulingP95Ms')),
        schedulingP95MsStd: std(pick('schedulingP95Ms')),
        schedulerCpuPercentAvgMean: mean(pick('schedulerCpuPercentAvg')),
        schedulerCpuPercentAvgStd: std(pick('schedulerCpuPercentAvg')),
        schedulerRssMbAvgMean: mean(pick('schedulerRssMbAvg')),
        schedulerRssMbAvgStd: std(pick('schedulerRssMbAvg')),
        schedulerRssMbMaxMean: mean(pick('schedulerRssMbMax')),
        schedulerRssMbMaxStd: std(pick('schedulerRssMbMax')),
        mvccFailuresMean: mean(pick('mvccFailures'))
    });
}

const csvHeader = [
    'workload',
    'rate',
    'repeats',
    'committed_mean',
    'committed_std',
    'scheduling_avg_ms_mean',
    'scheduling_avg_ms_std',
    'scheduling_p95_ms_mean',
    'scheduling_p95_ms_std',
    'scheduler_cpu_percent_avg_mean',
    'scheduler_cpu_percent_avg_std',
    'scheduler_rss_mb_avg_mean',
    'scheduler_rss_mb_avg_std',
    'scheduler_rss_mb_max_mean',
    'scheduler_rss_mb_max_std',
    'mvcc_failures_mean'
];
const csvLines = [
    csvHeader.join(','),
    ...summary.map(row => [
        row.workload,
        row.rate,
        row.repeats,
        fmt(row.committedMean),
        fmt(row.committedStd),
        fmt(row.schedulingAvgMsMean, 4),
        fmt(row.schedulingAvgMsStd, 4),
        fmt(row.schedulingP95MsMean, 4),
        fmt(row.schedulingP95MsStd, 4),
        fmt(row.schedulerCpuPercentAvgMean, 2),
        fmt(row.schedulerCpuPercentAvgStd, 2),
        fmt(row.schedulerRssMbAvgMean, 2),
        fmt(row.schedulerRssMbAvgStd, 2),
        fmt(row.schedulerRssMbMaxMean, 2),
        fmt(row.schedulerRssMbMaxStd, 2),
        fmt(row.mvccFailuresMean, 2)
    ].join(','))
];

const mdLines = [
    '| Workload | Offered load | Repeats | Commits | Scheduling avg (ms) | Scheduling P95 (ms) | CPU avg (%) | RSS avg (MB) | RSS max (MB) | MVCC-invalid |',
    '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ...summary.map(row => [
        row.workload,
        `${row.rate} tx/s`,
        row.repeats,
        `${fmt(row.committedMean, 1)} +/- ${fmt(row.committedStd, 1)}`,
        `${fmt(row.schedulingAvgMsMean, 4)} +/- ${fmt(row.schedulingAvgMsStd, 4)}`,
        `${fmt(row.schedulingP95MsMean, 4)} +/- ${fmt(row.schedulingP95MsStd, 4)}`,
        `${fmt(row.schedulerCpuPercentAvgMean, 2)} +/- ${fmt(row.schedulerCpuPercentAvgStd, 2)}`,
        `${fmt(row.schedulerRssMbAvgMean, 2)} +/- ${fmt(row.schedulerRssMbAvgStd, 2)}`,
        `${fmt(row.schedulerRssMbMaxMean, 2)} +/- ${fmt(row.schedulerRssMbMaxStd, 2)}`,
        fmt(row.mvccFailuresMean, 1)
    ].join(' | ')).map(line => `| ${line} |`)
];

fs.mkdirSync(path.dirname(outPrefix), { recursive: true });
fs.writeFileSync(`${outPrefix}.raw.json`, JSON.stringify(rows, null, 2));
fs.writeFileSync(`${outPrefix}.summary.json`, JSON.stringify(summary, null, 2));
fs.writeFileSync(`${outPrefix}.csv`, `${csvLines.join('\n')}\n`);
fs.writeFileSync(`${outPrefix}.md`, `${mdLines.join('\n')}\n`);

console.log(JSON.stringify({ root, runs: rows.length, groups: summary.length, outPrefix }, null, 2));
