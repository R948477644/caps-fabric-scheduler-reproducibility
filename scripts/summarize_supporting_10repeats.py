#!/usr/bin/env python3
import csv
import json
import math
import os
import re
import statistics
from pathlib import Path

DEFAULT_ROOT = r"C:\Users\94847\Documents\paper_2026\results\supporting_10repeats_20260626"


def resolve_root():
    raw = os.environ.get("SUPPORTING_RESULTS_ROOT", DEFAULT_ROOT)
    if os.name != "nt" and re.match(r"^[A-Za-z]:\\", raw):
        drive = raw[0].lower()
        rest = raw[2:].replace("\\", "/").lstrip("/")
        return Path(f"/mnt/{drive}/{rest}")
    return Path(raw)


ROOT = resolve_root()
OUT_RAW = ROOT / "supporting_10repeats_raw.csv"
OUT_SUMMARY = ROOT / "supporting_10repeats_summary.csv"

NAME_RE = re.compile(
    r"exp(?P<exp>\d+)-(?P<scenario>.+)-w3-(?P<method>.+)-hot(?P<hot>\d+)-(?P<rate>\d+)tps-rep(?P<rep>\d+)-client\.json$"
)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_status(client, code):
    return int(client.get("statusCounts", {}).get(str(code), 0))


def mean(values):
    return statistics.mean(values) if values else 0.0


def sd(values):
    return statistics.stdev(values) if len(values) > 1 else 0.0


def ci95(values):
    if len(values) < 2:
        return 0.0
    return 1.96 * sd(values) / math.sqrt(len(values))


def collect_rows():
    rows = []
    for client_path in ROOT.rglob("*-client.json"):
        match = NAME_RE.match(client_path.name)
        if not match:
            continue
        info = match.groupdict()
        metrics_path = client_path.with_name(client_path.name.replace("-client.json", "-metrics.json"))
        if not metrics_path.exists():
            continue
        client = load_json(client_path)
        metrics = load_json(metrics_path)
        rows.append(
            {
                "experiment": info["exp"],
                "scenario": info["scenario"],
                "method": info["method"],
                "hot": int(info["hot"]),
                "rate": int(info["rate"]),
                "repeat": int(info["rep"]),
                "sent": int(client.get("sent", 0)),
                "committed": get_status(client, 200),
                "admission_rejected": get_status(client, 429),
                "queue_timeout": get_status(client, 408),
                "client_error": get_status(client, 599),
                "completion_tps": float(client.get("completionRate", 0)),
                "latency_ms": float(client.get("latencyAvgMs", 0)),
                "latency_max_ms": float(client.get("latencyMaxMs", 0)),
                "mvcc_invalid": int(metrics.get("mvccFailures", 0)),
                "queue_wait_ms": float(metrics.get("queueWaitAvgMs", 0)),
                "fabric_ms": float(metrics.get("fabricAvgMs", 0)),
                "conflict_blocked": int(metrics.get("conflictBlocked", 0)),
                "scd_selected": int(metrics.get("scdSelected", 0)),
                "scd_edges": int(metrics.get("scdConflictEdges", 0)),
                "hot_key_rejected": int(metrics.get("hotKeyRejected", 0)),
                "ttl_expired": int(metrics.get("ttlExpired", 0)),
            }
        )
    return sorted(rows, key=lambda r: (int(r["experiment"]), r["scenario"], r["method"], r["rate"], r["hot"], r["repeat"]))


def write_raw(rows):
    if not rows:
        return
    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with OUT_RAW.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_summary(rows):
    OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    groups = {}
    for row in rows:
        key = (row["experiment"], row["scenario"], row["method"], row["rate"], row["hot"])
        groups.setdefault(key, []).append(row)

    metric_names = [
        "committed",
        "admission_rejected",
        "queue_timeout",
        "client_error",
        "completion_tps",
        "latency_ms",
        "latency_max_ms",
        "mvcc_invalid",
        "queue_wait_ms",
        "fabric_ms",
        "conflict_blocked",
        "scd_selected",
        "scd_edges",
        "hot_key_rejected",
        "ttl_expired",
    ]
    fields = ["experiment", "scenario", "method", "rate", "hot", "n"]
    for metric in metric_names:
        fields += [f"{metric}_mean", f"{metric}_sd", f"{metric}_ci95"]

    with OUT_SUMMARY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for key, items in sorted(groups.items(), key=lambda kv: (int(kv[0][0]), kv[0][1], kv[0][2], kv[0][3], kv[0][4])):
            exp, scenario, method, rate, hot = key
            out = {
                "experiment": exp,
                "scenario": scenario,
                "method": method,
                "rate": rate,
                "hot": hot,
                "n": len(items),
            }
            for metric in metric_names:
                values = [float(item[metric]) for item in items]
                out[f"{metric}_mean"] = mean(values)
                out[f"{metric}_sd"] = sd(values)
                out[f"{metric}_ci95"] = ci95(values)
            writer.writerow(out)


def main():
    rows = collect_rows()
    write_raw(rows)
    write_summary(rows)
    print(f"raw_rows={len(rows)}")
    print(f"raw={OUT_RAW}")
    print(f"summary={OUT_SUMMARY}")


if __name__ == "__main__":
    main()
