#!/usr/bin/env python3
import csv
import math
import os
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUPPLY = ROOT / "experiment7_supply_chain" / "formal_results_20260625" / "summary.csv"
SUPPORT = ROOT / "results" / "supporting_10repeats_20260626" / "supporting_10repeats_summary.csv"
OUT = ROOT / "results" / "paper_stat_tables"


def f1(x):
    return f"{float(x):,.1f}"


def f2(x):
    return f"{float(x):,.2f}"


def ci95(sd, n=10):
    return 1.96 * float(sd) / math.sqrt(n)


def read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_text(name, text):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(text, encoding="utf-8")


def supply_caps_lock_table(rows):
    by_key = {(r["workload"], r["scheduler"], int(r["offeredLoad"])): r for r in rows}
    lines = []
    for workload in ["sc-w1", "sc-w2", "sc-w3"]:
        for rate in [300, 500]:
            caps = by_key[(workload, "caps", rate)]
            lock = by_key[(workload, "traditional-lock", rate)]
            gain = (float(caps["committedMean"]) / float(lock["committedMean"]) - 1.0) * 100
            lat_red = (1.0 - float(caps["latencyAvgMsMean"]) / float(lock["latencyAvgMsMean"])) * 100
            lines.append(
                f"{workload.upper()} & {rate} & "
                f"{f1(caps['committedMean'])} $\\pm$ {f1(caps['committedStd'])} & "
                f"$\\pm$ {f1(ci95(caps['committedStd']))} & "
                f"{f1(lock['committedMean'])} $\\pm$ {f1(lock['committedStd'])} & "
                f"{gain:.1f}\\% & "
                f"{f1(caps['latencyAvgMsMean'])} $\\pm$ {f1(caps['latencyAvgMsStd'])} & "
                f"$\\pm$ {f1(ci95(caps['latencyAvgMsStd']))} & "
                f"{lat_red:.1f}\\% \\\\"
            )
    return "\n".join(lines)


def supply_full_table(rows):
    methods = [("native", "Native Fabric"), ("ed-mvcc", "ED-MVCC-Reimpl"), ("traditional-lock", "Traditional Lock"), ("caps", "CAPS")]
    by_key = {(r["workload"], r["scheduler"], int(r["offeredLoad"])): r for r in rows}
    lines = []
    for workload in ["sc-w1", "sc-w2", "sc-w3"]:
        for rate in [300, 500]:
            for method, label in methods:
                r = by_key[(workload, method, rate)]
                lines.append(
                    f"{workload.upper()} & {rate} & {label} & "
                    f"{f1(r['committedMean'])} $\\pm$ {f1(r['committedStd'])} & "
                    f"{f2(r['goodputMean'])} $\\pm$ {f2(r['goodputStd'])} & "
                    f"{f1(r['latencyAvgMsMean'])} $\\pm$ {f1(r['latencyAvgMsStd'])} & "
                    f"{f1(r['mvccFailuresMean'])} $\\pm$ {f1(r['mvccFailuresStd'])} \\\\"
                )
            if not (workload == "sc-w3" and rate == 500):
                lines.append("\\addlinespace")
    return "\n".join(lines)


def supply_admission_table(rows):
    methods = [("native", "Native Fabric"), ("ed-mvcc", "ED-MVCC"), ("traditional-lock", "Trad. Lock"), ("caps", "CAPS")]
    by_key = {(r["workload"], r["scheduler"], int(r["offeredLoad"])): r for r in rows}
    lines = []
    for workload in ["sc-w1", "sc-w2", "sc-w3"]:
        for rate in [300, 500]:
            generated = rate * 20
            for method, label in methods:
                r = by_key[(workload, method, rate)]
                rejected = float(r["admissionRejectedMean"])
                timeout = float(r["queueTimeoutMean"])
                dropped = float(r["localDroppedMean"])
                submitted = generated - rejected - timeout - dropped
                commit_ratio = float(r["committedMean"]) / generated * 100
                reject_ratio = rejected / generated * 100
                timeout_ratio = timeout / generated * 100
                lines.append(
                    f"{workload.upper()} & {rate} & {label} & "
                    f"{generated:,.0f} & {f1(submitted)} & "
                    f"{f1(r['committedMean'])} & {commit_ratio:.1f}\\% & "
                    f"{f1(rejected)} ({reject_ratio:.1f}\\%) & "
                    f"{f1(timeout)} ({timeout_ratio:.1f}\\%) \\\\"
                )
            if not (workload == "sc-w3" and rate == 500):
                lines.append("\\addlinespace")
    return "\n".join(lines)


def support_key(rows):
    return {(r["experiment"], r["scenario"], r["method"], int(r["rate"]), int(r["hot"])): r for r in rows}


def get(rows, exp, scenario, method, rate, hot=100):
    return support_key(rows)[(str(exp), scenario, method, int(rate), int(hot))]


def support_table(rows):
    key = support_key(rows)
    lines = []

    def gain(a, b, metric):
        return (float(a[metric]) / float(b[metric]) - 1.0) * 100

    def red(a, b, metric):
        return (1.0 - float(a[metric]) / float(b[metric])) * 100

    # Contention range: report hot=50--500 against Traditional Lock.
    gains = []
    reds = []
    for hot in [50, 100, 200, 500]:
        caps = key[("2", "contention", "pa-vscd", 300, hot)]
        lock = key[("2", "contention", "traditional-lock", 300, hot)]
        gains.append(gain(caps, lock, "committed_mean"))
        reds.append(red(caps, lock, "latency_ms_mean"))
    h20_caps = key[("2", "contention", "pa-vscd", 300, 20)]
    h20_lock = key[("2", "contention", "traditional-lock", 300, 20)]
    lines.append(
        "Contention sensitivity & W3, 300 tx/s, hot=50--500 & "
        f"CAPS increases commits by {min(gains):.1f}\\%--{max(gains):.1f}\\% "
        f"and reduces latency by {min(reds):.1f}\\%--{max(reds):.1f}\\%; "
        f"at hot=20 it reports {f1(h20_caps['committed_mean'])}$\\pm${f1(h20_caps['committed_sd'])} commits "
        f"with {f1(h20_caps['latency_ms_mean'])}$\\pm${f1(h20_caps['latency_ms_sd'])} ms latency. \\\\"
    )

    caps300 = key[("3", "ablation", "pa-vscd", 300, 100)]
    lock300 = key[("3", "ablation", "traditional-lock", 300, 100)]
    dbs300 = key[("3", "ablation", "pacc-dabs", 300, 100)]
    pac300 = key[("3", "ablation", "pacc-lpaac", 300, 100)]
    lines.append(
        "Module ablation & W3, 300 tx/s & "
        f"ACG+DBS commits {f1(dbs300['committed_mean'])}$\\pm${f1(dbs300['committed_sd'])} but has "
        f"{f1(dbs300['latency_ms_mean'])}$\\pm${f1(dbs300['latency_ms_sd'])} ms latency; "
        f"ACG+PAC has {f1(pac300['latency_ms_mean'])}$\\pm${f1(pac300['latency_ms_sd'])} ms latency; "
        f"CAPS improves commits by {gain(caps300, lock300, 'committed_mean'):.1f}\\% and latency by "
        f"{red(caps300, lock300, 'latency_ms_mean'):.1f}\\%. \\\\"
    )

    policy_gains = []
    policy_reds = []
    for scenario in ["default-policy", "or-policy"]:
        for rate in [300, 500]:
            caps = key[("4", scenario, "pa-vscd", rate, 100)]
            lock = key[("4", scenario, "traditional-lock", rate, 100)]
            policy_gains.append(gain(caps, lock, "committed_mean"))
            policy_reds.append(red(caps, lock, "latency_ms_mean"))
    lines.append(
        "Endorsement robustness & Default and OR policies, W3, 300/500 tx/s & "
        f"Across four settings, CAPS improves commits by {min(policy_gains):.1f}\\%--{max(policy_gains):.1f}\\% "
        f"and reduces latency by {min(policy_reds):.1f}\\%--{max(policy_reds):.1f}\\%. \\\\"
    )

    batch_gains = []
    batch_reds = []
    for scenario in ["batch10-timeout2s", "batch5-timeout1s", "batch50-timeout2s"]:
        for rate in [300, 500]:
            caps = key[("5", scenario, "pa-vscd", rate, 100)]
            lock = key[("5", scenario, "traditional-lock", rate, 100)]
            batch_gains.append(gain(caps, lock, "committed_mean"))
            batch_reds.append(red(caps, lock, "latency_ms_mean"))
    lines.append(
        "Block-cutting robustness & B5, B10, and B50, W3, 300/500 tx/s & "
        f"CAPS improves commits by {min(batch_gains):.1f}\\%--{max(batch_gains):.1f}\\%; "
        f"latency reduction ranges from {min(batch_reds):.1f}\\% to {max(batch_reds):.1f}\\%, with B50 remaining the boundary case. \\\\"
    )

    caps6_300 = key[("6", "related-baselines", "pa-vscd", 300, 100)]
    ed6_300 = key[("6", "related-baselines", "ed-mvcc", 300, 100)]
    drt6_300 = key[("6", "related-baselines", "drt", 300, 100)]
    caps6_500 = key[("6", "related-baselines", "pa-vscd", 500, 100)]
    drt6_500 = key[("6", "related-baselines", "drt", 500, 100)]
    lines.append(
        "Related-work baselines & W3, 300/500 tx/s & "
        f"At 300 tx/s, CAPS commits {f1(caps6_300['committed_mean'])}$\\pm${f1(caps6_300['committed_sd'])} "
        f"versus {f1(ed6_300['committed_mean'])}$\\pm${f1(ed6_300['committed_sd'])} for ED-MVCC; "
        f"relative to DRT, CAPS reduces latency by {red(caps6_300, drt6_300, 'latency_ms_mean'):.1f}\\% at 300 tx/s "
        f"and {red(caps6_500, drt6_500, 'latency_ms_mean'):.1f}\\% at 500 tx/s. \\\\"
    )
    return "\n".join(lines)


def main():
    supply_rows = read_csv(SUPPLY)
    support_rows = read_csv(SUPPORT)
    write_text("table_supply_caps_lock_rows.tex", supply_caps_lock_table(supply_rows))
    write_text("table_supply_full_rows.tex", supply_full_table(supply_rows))
    write_text("table_supply_admission_rows.tex", supply_admission_table(supply_rows))
    write_text("table_supporting_rows.tex", support_table(support_rows))
    print(OUT)


if __name__ == "__main__":
    main()
