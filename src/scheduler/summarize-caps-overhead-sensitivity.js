'use strict';

const fs = require('fs');
const path = require('path');

const args = parseArgs(process.argv.slice(2));
const root = path.resolve(args.root || 'results/caps-overhead-sensitivity');
const outPrefix = path.resolve(args.out || path.join(root, 'caps-overhead-sensitivity-summary'));

function parseArgs(argv) {
    const result = {};
    for (let i = 0; i < argv.length; i++) {
        const item = argv[i];
        if (!item.startsWith('--')) continue;
        const key = item.slice(2);
        const next = argv[i + 1];
        if (!next || next.startsWith('--')) result[key] = true;
        else {
            result[key] = next;
            i += 1;
        }
    }
    return result;
}

function readJson(file) {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function dirs(dir) {
    if (!fs.existsSync(dir)) return [];
    return fs.readdirSync(dir, { withFileTypes: true }).filter(e => e.isDirectory()).map(e => e.name).sort();
}

function mean(xs) {
    return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0;
}

function std(xs) {
    if (xs.length < 2) return 0;
    const m = mean(xs);
    return Math.sqrt(xs.reduce((s, x) => s + Math.pow(x - m, 2), 0) / (xs.length - 1));
}

function fmt(x, d = 2) {
    return Number.isFinite(x) ? x.toFixed(d) : '0.00';
}

const rows = [];
for (const name of dirs(root)) {
    const groupDir = path.join(root, name);
    const cfgFile = path.join(groupDir, 'config.json');
    if (!fs.existsSync(cfgFile)) continue;
    const cfg = readJson(cfgFile);
    for (const repeat of dirs(groupDir).filter(d => d.startsWith('repeat-'))) {
        const metricsFile = path.join(groupDir, repeat, 'scheduler-metrics.json');
        const clientFile = path.join(groupDir, repeat, 'client.json');
        if (!fs.existsSync(metricsFile) || !fs.existsSync(clientFile)) continue;
        const m = readJson(metricsFile);
        const c = readJson(clientFile);
        rows.push({
            name,
            repeat: Number(repeat.replace('repeat-', '')),
            maxActive: cfg.maxActive,
            scdWindow: cfg.scdWindow,
            hotAccountCount: cfg.hotAccountCount,
            sent: c.sent || 0,
            committed: m.succeeded || 0,
            rejected: m.rejected || 0,
            queueLengthAvg: m.queueLengthAvg || 0,
            queueLengthMax: m.queueLengthMax || 0,
            schedulingAvgMs: m.schedulingAvgMs || 0,
            schedulingP95Ms: m.schedulingP95Ms || 0,
            schedulerCpuPercentAvg: m.schedulerCpuPercentAvg || 0,
            schedulerRssMbAvg: m.schedulerRssMbAvg || 0,
            schedulerRssMbMax: m.schedulerRssMbMax || 0
        });
    }
}

const groups = new Map();
for (const row of rows) {
    if (!groups.has(row.name)) groups.set(row.name, []);
    groups.get(row.name).push(row);
}

const summary = [];
for (const [name, g] of [...groups.entries()].sort()) {
    const first = g[0];
    const pick = k => g.map(x => x[k]);
    summary.push({
        name,
        repeats: g.length,
        maxActive: first.maxActive,
        scdWindow: first.scdWindow,
        hotAccountCount: first.hotAccountCount,
        committedMean: mean(pick('committed')),
        committedStd: std(pick('committed')),
        queueLengthAvgMean: mean(pick('queueLengthAvg')),
        queueLengthMaxMean: mean(pick('queueLengthMax')),
        schedulingAvgMsMean: mean(pick('schedulingAvgMs')),
        schedulingAvgMsStd: std(pick('schedulingAvgMs')),
        schedulingP95MsMean: mean(pick('schedulingP95Ms')),
        schedulingP95MsStd: std(pick('schedulingP95Ms')),
        cpuAvgMean: mean(pick('schedulerCpuPercentAvg')),
        rssAvgMean: mean(pick('schedulerRssMbAvg')),
        rssMaxMean: mean(pick('schedulerRssMbMax'))
    });
}

const csvHeader = [
    'name', 'repeats', 'max_active', 'scd_window', 'hot_account_count',
    'committed_mean', 'committed_std', 'queue_length_avg_mean', 'queue_length_max_mean',
    'scheduling_avg_ms_mean', 'scheduling_avg_ms_std', 'scheduling_p95_ms_mean',
    'scheduling_p95_ms_std', 'cpu_avg_percent_mean', 'rss_avg_mb_mean', 'rss_max_mb_mean'
];
const csv = [
    csvHeader.join(','),
    ...summary.map(r => [
        r.name, r.repeats, r.maxActive, r.scdWindow, r.hotAccountCount,
        fmt(r.committedMean, 1), fmt(r.committedStd, 1), fmt(r.queueLengthAvgMean, 2), fmt(r.queueLengthMaxMean, 1),
        fmt(r.schedulingAvgMsMean, 4), fmt(r.schedulingAvgMsStd, 4), fmt(r.schedulingP95MsMean, 4),
        fmt(r.schedulingP95MsStd, 4), fmt(r.cpuAvgMean, 2), fmt(r.rssAvgMean, 2), fmt(r.rssMaxMean, 2)
    ].join(','))
];

const md = [
    '| Setting | maxActive | window | hot accounts | queue avg | queue max | scheduling avg (ms) | scheduling P95 (ms) | CPU avg (%) | RSS avg (MB) |',
    '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ...summary.map(r => `| ${r.name} | ${r.maxActive} | ${r.scdWindow} | ${r.hotAccountCount} | ${fmt(r.queueLengthAvgMean, 2)} | ${fmt(r.queueLengthMaxMean, 1)} | ${fmt(r.schedulingAvgMsMean, 4)} +/- ${fmt(r.schedulingAvgMsStd, 4)} | ${fmt(r.schedulingP95MsMean, 4)} +/- ${fmt(r.schedulingP95MsStd, 4)} | ${fmt(r.cpuAvgMean, 2)} | ${fmt(r.rssAvgMean, 2)} |`)
];

fs.mkdirSync(path.dirname(outPrefix), { recursive: true });
fs.writeFileSync(`${outPrefix}.raw.json`, JSON.stringify(rows, null, 2));
fs.writeFileSync(`${outPrefix}.summary.json`, JSON.stringify(summary, null, 2));
fs.writeFileSync(`${outPrefix}.csv`, `${csv.join('\n')}\n`);
fs.writeFileSync(`${outPrefix}.md`, `${md.join('\n')}\n`);
console.log(JSON.stringify({ root, runs: rows.length, groups: summary.length, outPrefix }, null, 2));
