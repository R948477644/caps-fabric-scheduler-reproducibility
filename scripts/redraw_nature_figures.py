from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nature_redraw_figures_20260627"


plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42

mpl.rcParams.update(
    {
        "figure.dpi": 140,
        "savefig.dpi": 600,
        "font.size": 7.5,
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.7,
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
        "grid.linewidth": 0.45,
        "grid.color": "#D8D8D8",
        "grid.alpha": 0.8,
        "legend.frameon": False,
    }
)


COL = {
    "Native Fabric": "#9A9A9A",
    "Traditional Lock": "#4E79A7",
    "ED-MVCC-Reimpl": "#F2B447",
    "DRT-Reimpl": "#59A14F",
    "CAPS": "#C44E52",
    "ACG+DBS": "#76B7B2",
    "ACG+PAC": "#2E8B57",
    "Committed": "#2E8B57",
    "MVCC-invalid": "#C44E52",
    "Admission rejected": "#F2B447",
    "Queue timeout": "#8E6BBE",
    "Other/client error": "#B8B8B8",
    "dark": "#2B2B2B",
    "line": "#5A5A5A",
}


def ensure_out() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def save(fig: plt.Figure, name: str) -> None:
    ensure_out()
    for ext in ("svg", "pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def panel(ax: plt.Axes, label: str) -> None:
    ax.text(-0.08, 1.04, label, transform=ax.transAxes, fontweight="bold", fontsize=9, va="bottom")


def grouped_bars(ax, xlabels, data, errors, methods, ylabel, ylim=None, log=False, annotate=False):
    x = np.arange(len(xlabels), dtype=float)
    width = min(0.78 / len(methods), 0.18)
    offsets = (np.arange(len(methods)) - (len(methods) - 1) / 2) * width
    for i, m in enumerate(methods):
        vals = np.array(data[m], dtype=float)
        err = np.array(errors.get(m, np.zeros_like(vals)), dtype=float)
        ax.bar(
            x + offsets[i],
            vals,
            width=width,
            yerr=err,
            label=m,
            color=COL[m],
            edgecolor="#333333",
            linewidth=0.45,
            capsize=2,
            error_kw={"elinewidth": 0.65, "capthick": 0.65},
        )
        if annotate:
            for xx, v in zip(x + offsets[i], vals):
                ax.text(xx, v * (1.015 if log else 1.02), f"{v:.1f}", ha="center", va="bottom", fontsize=6)
    ax.set_xticks(x)
    ax.set_xticklabels(xlabels)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y")
    if ylim:
        ax.set_ylim(*ylim)
    if log:
        ax.set_yscale("log")
    return ax


def make_figure1():
    fig, ax = plt.subplots(figsize=(7.05, 3.25))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.text(0.1, 5.75, "a", fontweight="bold", fontsize=10)

    def box(x, y, w, h, text, fc="#FFFFFF", ec="#333333"):
        r = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.06", fc=fc, ec=ec, lw=0.8)
        ax.add_patch(r)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7)
        return r

    def arrow(x1, y1, x2, y2, color="#555555", style="-|>"):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=8, lw=0.8, color=color))

    ax.text(2.4, 5.45, "Native Fabric EOV", ha="center", fontweight="bold", fontsize=8.5)
    ax.text(7.5, 5.45, "CAPS-assisted EOV", ha="center", fontweight="bold", fontsize=8.5)
    phases = ["Endorse", "Order", "Validate", "Commit"]
    for i, p in enumerate(phases):
        y = 4.6 - i * 1.0
        box(0.9, y, 1.5, 0.45, p, fc="#F7F7F7")
        box(6.0, y, 1.5, 0.45, p, fc="#F7F7F7")
    box(2.9, 2.55, 1.9, 0.55, "MVCC conflict\nfound late", fc="#F7E0DF", ec=COL["CAPS"])
    box(7.9, 4.6, 1.7, 0.55, "ACG + PAC\nbefore Fabric", fc="#EAF3ED", ec=COL["Committed"])
    box(7.9, 3.55, 1.7, 0.55, "DBS selects\ncompatible batch", fc="#EEF3F7", ec=COL["Traditional Lock"])
    for x0 in (1.65, 6.75):
        arrow(x0, 4.55, x0, 1.55)
    arrow(2.4, 2.8, 2.9, 2.8, color=COL["CAPS"])
    arrow(7.5, 4.83, 7.9, 4.83, color=COL["Committed"])
    arrow(8.75, 4.55, 8.75, 4.10, color=COL["Traditional Lock"])
    arrow(8.75, 3.55, 7.55, 3.05, color=COL["Traditional Lock"])
    ax.text(1.65, 0.72, "Conflict handling occurs after\nendorsement and ordering cost.", ha="center", fontsize=7, color="#555555")
    ax.text(7.5, 0.72, "Conflict and overload are filtered\nbefore scarce Fabric resources.", ha="center", fontsize=7, color="#555555")
    save(fig, "fig1_eov_comparison_nature")


def make_figure2():
    fig, ax = plt.subplots(figsize=(7.05, 3.2))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.text(0.1, 5.75, "a", fontweight="bold", fontsize=10)

    def box(x, y, w, h, text, fc, ec="#444444"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.08", fc=fc, ec=ec, lw=0.8))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7)

    def arrow(x1, y1, x2, y2, color="#555555"):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=9, lw=0.85, color=color))

    box(0.4, 2.65, 1.45, 0.7, "Client\nrequests", "#F7F7F7")
    box(2.25, 3.65, 1.7, 0.8, "ACG\naccess-set guard", "#EEF3F7", COL["Traditional Lock"])
    box(4.35, 3.65, 1.7, 0.8, "DBS\nbatch selection", "#F2F7F2", COL["Committed"])
    box(6.45, 3.65, 1.7, 0.8, "PAC\npressure control", "#F8EFE5", COL["Admission rejected"])
    box(8.55, 3.65, 1.2, 0.8, "Fabric\nGateway", "#F7F7F7")
    box(3.0, 1.25, 2.0, 0.65, "waiting queue", "#FFFFFF")
    box(5.35, 1.25, 2.0, 0.65, "active submissions", "#FFFFFF")
    box(8.0, 1.25, 1.65, 0.65, "commit events", "#FFFFFF")
    for a in [(1.85, 3.0, 2.25, 4.05), (3.95, 4.05, 4.35, 4.05), (6.05, 4.05, 6.45, 4.05), (8.15, 4.05, 8.55, 4.05)]:
        arrow(*a)
    arrow(3.1, 3.65, 3.75, 1.9)
    arrow(5.2, 3.65, 6.2, 1.9)
    arrow(8.6, 3.65, 8.85, 1.9)
    arrow(8.0, 1.55, 6.9, 3.65, color=COL["line"])
    ax.text(5.0, 5.25, "Conflict-aware admission, compatible-batch selection,\nand explicit overload feedback", ha="center", fontsize=8.5, fontweight="bold")
    ax.text(5.0, 0.55, "All methods use the same Fabric network; CAPS changes only the external submission scheduler.", ha="center", fontsize=7, color="#555555")
    save(fig, "fig2_architecture_nature")


def make_figure3():
    t = np.arange(0, 24)
    q = np.clip((np.sin(t / 3) + 1.1) / 2.0 + np.maximum(0, t - 10) / 22, 0, 1.45)
    w = np.clip((np.cos(t / 4) + 1.0) / 2.8 + np.maximum(0, t - 13) / 35, 0, 1.2)
    h = np.where((t > 8) & (t < 18), 0.35, 0.08)
    p = 0.45 * q + 0.35 * w + 0.20 * h
    fig, ax = plt.subplots(figsize=(7.05, 2.85))
    ax.plot(t, q, color=COL["Traditional Lock"], lw=1.7, label="queue pressure")
    ax.plot(t, w, color=COL["Admission rejected"], lw=1.7, label="waiting-time pressure")
    ax.plot(t, h, color=COL["DRT-Reimpl"], lw=1.7, label="hotspot backlog")
    ax.plot(t, p, color=COL["CAPS"], lw=2.1, label="combined pressure")
    ax.axhline(1.0, color="#444444", lw=0.8, ls="--")
    ax.fill_between(t, 1.0, p, where=p >= 1.0, color=COL["CAPS"], alpha=0.14, linewidth=0)
    ax.set_xlabel("scheduler time window")
    ax.set_ylabel("normalized pressure")
    ax.set_ylim(0, 1.55)
    ax.grid(axis="y")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.22))
    panel(ax, "a")
    ax.text(17.0, 1.28, "tighten admission\nand return backpressure", fontsize=7, color=COL["CAPS"])
    save(fig, "fig3_pressure_control_nature")


WORKLOADS = ["SC-W1-300", "SC-W1-500", "SC-W2-300", "SC-W2-500", "SC-W3-300", "SC-W3-500"]
METHODS4 = ["Native Fabric", "Traditional Lock", "ED-MVCC-Reimpl", "CAPS"]


def make_figure4a():
    committed = {
        "Native Fabric": [4769.3, 8124.3, 2566.7, 5246.5, 1684.2, 3367.9],
        "Traditional Lock": [2153.8, 2148.4, 1884.0, 1879.0, 778.9, 822.9],
        "ED-MVCC-Reimpl": [4458.2, 4725.6, 3153.2, 3798.6, 1739.9, 2722.7],
        "CAPS": [4334.2, 4392.0, 4387.0, 4240.9, 2609.2, 3562.8],
    }
    committed_sd = {
        "Native Fabric": [169.3412, 558.9276, 233.23, 293.0033, 48.4888, 27.2674],
        "Traditional Lock": [59.4602, 21.9606, 46.619, 13.1825, 18.1108, 5.7441],
        "ED-MVCC-Reimpl": [349.9444, 303.9171, 28.2992, 76.255, 17.573, 15.8532],
        "CAPS": [378.573, 342.1946, 63.407, 30.5003, 2.1499, 54.3103],
    }
    goodput = {
        "Native Fabric": [127.0952, 108.9127, 74.6651, 80.2801, 43.6944, 52.7247],
        "Traditional Lock": [72.6566, 73.0155, 8.2424, 8.3965, 28.6034, 33.1183],
        "ED-MVCC-Reimpl": [203.3018, 207.0478, 144.6689, 181.9375, 77.0121, 122.6058],
        "CAPS": [192.636, 187.7728, 163.3561, 161.3483, 86.6432, 119.83],
    }
    goodput_sd = {
        "Native Fabric": [24.2635, 26.5779, 13.268, 13.5642, 2.6842, 6.2752],
        "Traditional Lock": [2.5375, 2.272, 0.8552, 0.528, 0.7566, 0.2923],
        "ED-MVCC-Reimpl": [19.1755, 15.958, 4.1975, 8.2092, 1.5291, 1.9611],
        "CAPS": [24.334, 20.7251, 4.0065, 1.8969, 6.5561, 4.733],
    }
    fig, axes = plt.subplots(2, 1, figsize=(7.05, 5.4), sharex=True)
    grouped_bars(axes[0], WORKLOADS, committed, committed_sd, METHODS4, "committed transactions")
    grouped_bars(axes[1], WORKLOADS, goodput, goodput_sd, METHODS4, "goodput (transactions/s)")
    panel(axes[0], "a")
    panel(axes[1], "b")
    axes[0].legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.26))
    axes[1].legend().remove()
    axes[1].tick_params(axis="x", labelrotation=0)
    save(fig, "fig4a_supply_chain_performance_nature")


def make_figure4b():
    latency = {
        "Native Fabric": [4611.6536, 15503.8094, 3571.5699, 14226.5818, 3908.7019, 14189.9775],
        "Traditional Lock": [1964.8103, 1182.9041, 7687.0963, 4656.7379, 1854.0899, 1115.8938],
        "ED-MVCC-Reimpl": [275.8621, 360.7961, 98.1658, 96.2415, 94.6461, 94.7148],
        "CAPS": [684.283, 566.7721, 535.6286, 358.6126, 188.5073, 163.8369],
    }
    latency_sd = {
        "Native Fabric": [2364.4764, 1849.4333, 956.4265, 1948.6733, 241.2739, 334.5293],
        "Traditional Lock": [0.7344, 5.1197, 34.0313, 84.8641, 8.5652, 2.7016],
        "ED-MVCC-Reimpl": [138.59, 180.4961, 0.8985, 1.0366, 0.4039, 0.6252],
        "CAPS": [222.6415, 252.7074, 14.2308, 21.4621, 1.5865, 6.5096],
    }
    outcomes = [
        ("SC-W1-300", "Native Fabric", 6000, 4769.3, 1065.5, 0, 0, 165.2),
        ("SC-W1-300", "Traditional Lock", 6000, 2153.8, 0, 3844.6, 0, 1.6),
        ("SC-W1-300", "ED-MVCC-Reimpl", 6000, 4458.2, 0, 1541.8, 0, 0),
        ("SC-W1-300", "CAPS", 6000, 4334.2, 0, 1665.0, 0, 0.8),
        ("SC-W1-500", "Native Fabric", 10000, 8124.3, 1534.0, 0, 0, 341.7),
        ("SC-W1-500", "Traditional Lock", 10000, 2148.4, 0, 7850.9, 0, 0.7),
        ("SC-W1-500", "ED-MVCC-Reimpl", 10000, 4725.6, 0, 5274.4, 0, 0),
        ("SC-W1-500", "CAPS", 10000, 4392.0, 0, 5608.0, 0, 0),
        ("SC-W2-300", "Native Fabric", 6000, 2566.7, 3119.9, 0, 0, 313.4),
        ("SC-W2-300", "Traditional Lock", 6000, 1884.0, 0, 4115.7, 0, 0.3),
        ("SC-W2-300", "ED-MVCC-Reimpl", 6000, 3153.2, 0, 2846.8, 0, 0),
        ("SC-W2-300", "CAPS", 6000, 4387.0, 0, 1613.0, 0, 0),
        ("SC-W2-500", "Native Fabric", 10000, 5246.5, 4025.0, 0, 0, 728.5),
        ("SC-W2-500", "Traditional Lock", 10000, 1879.0, 0, 8119.2, 0, 1.8),
        ("SC-W2-500", "ED-MVCC-Reimpl", 10000, 3798.6, 0, 6201.4, 0, 0),
        ("SC-W2-500", "CAPS", 10000, 4240.9, 0, 5759.1, 0, 0),
        ("SC-W3-300", "Native Fabric", 6000, 1684.2, 3998.1, 0, 0, 317.7),
        ("SC-W3-300", "Traditional Lock", 6000, 778.9, 0, 3456.4, 1757.3, 7.4),
        ("SC-W3-300", "ED-MVCC-Reimpl", 6000, 1739.9, 35.4, 4224.7, 0, 0),
        ("SC-W3-300", "CAPS", 6000, 2609.2, 0, 3390.8, 0, 0),
        ("SC-W3-500", "Native Fabric", 10000, 3367.9, 5826.6, 0, 0, 805.5),
        ("SC-W3-500", "Traditional Lock", 10000, 822.9, 0, 4698.7, 4476.6, 1.8),
        ("SC-W3-500", "ED-MVCC-Reimpl", 10000, 2722.7, 0, 7277.3, 0, 0),
        ("SC-W3-500", "CAPS", 10000, 3562.8, 0, 6437.2, 0, 0),
    ]
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.0), gridspec_kw={"height_ratios": [1.0, 1.35]})
    fig.subplots_adjust(hspace=0.42, top=0.90, bottom=0.12)
    grouped_bars(axes[0], WORKLOADS, latency, latency_sd, METHODS4, "mean latency (ms)", log=True)
    axes[0].legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.28))
    panel(axes[0], "a")
    axes[0].set_ylabel("mean latency (ms, log scale)")

    ax = axes[1]
    out_names = ["Committed", "MVCC-invalid", "Admission rejected", "Queue timeout", "Other/client error"]
    width = 0.16
    xbase = np.arange(len(WORKLOADS), dtype=float)
    offsets = (np.arange(len(METHODS4)) - 1.5) * width
    for j, method in enumerate(METHODS4):
        bottom = np.zeros(len(WORKLOADS))
        for k, outn in enumerate(out_names):
            vals = []
            for wl in WORKLOADS:
                row = next(r for r in outcomes if r[0] == wl and r[1] == method)
                generated = row[2]
                vals.append(row[3 + k] / generated * 100)
            ax.bar(xbase + offsets[j], vals, width=width, bottom=bottom, color=COL[outn], edgecolor="#333333", linewidth=0.35, label=outn if j == 0 else None)
            bottom += np.array(vals)
    ax.set_xticks(xbase)
    ax.set_xticklabels(WORKLOADS)
    ax.set_ylabel("share of generated transactions (%)")
    ax.set_ylim(0, 108)
    ax.grid(axis="y")
    ax.legend(
        ncol=5,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.14),
        columnspacing=1.1,
        handlelength=1.3,
        fontsize=6.6,
    )
    panel(ax, "b")
    save(fig, "fig4b_supply_chain_latency_cost_nature")


def make_figure5():
    hot = ["20", "50", "100", "200", "500"]
    data = {
        "Traditional Lock": [268.9, 1318.9, 1868.1, 1859.3, 1858.1],
        "CAPS": [255.8, 3834.7, 4541.8, 4520.7, 4598.6],
    }
    sd = {
        "Traditional Lock": [53.8546, 52.2014, 95.5132, 86.8448, 103.2424],
        "CAPS": [212.7287, 217.6164, 255.9239, 202.4143, 276.2765],
    }
    lat = {
        "Traditional Lock": [1895.2537, 1908.8658, 1870.3802, 1876.8337, 1859.3518],
        "CAPS": [591.6637, 573.461, 595.4065, 615.4817, 608.2049],
    }
    lat_sd = {
        "Traditional Lock": [88.2339, 58.9114, 34.6352, 44.3726, 66.3003],
        "CAPS": [39.9452, 26.5953, 58.5432, 74.3743, 48.5727],
    }
    fig, axes = plt.subplots(2, 1, figsize=(6.2, 4.7), sharex=True)
    grouped_bars(axes[0], hot, data, sd, ["Traditional Lock", "CAPS"], "committed transactions")
    panel(axes[0], "a")
    axes[0].legend(ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.22))
    x = np.arange(len(hot))
    for m in ["Traditional Lock", "CAPS"]:
        axes[1].errorbar(x, lat[m], yerr=lat_sd[m], marker="o", lw=1.5, capsize=2, color=COL[m], label=m)
    axes[1].set_yscale("log")
    axes[1].set_ylabel("mean latency (ms)")
    axes[1].set_xlabel("hotAccountCount")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(hot)
    axes[1].grid(axis="y")
    panel(axes[1], "b")
    save(fig, "fig5_conflict_sensitivity_nature")


def make_figure6():
    rates = ["300 tx/s", "500 tx/s"]
    variants = ["Traditional Lock", "ACG+DBS", "ACG+PAC", "CAPS"]
    commits = {
        "Traditional Lock": [1890.0, 1814.7],
        "ACG+DBS": [5153.8, 5104.0],
        "ACG+PAC": [3083.5, 4322.9],
        "CAPS": [4643.3, 3839.7],
    }
    commit_sd = {
        "Traditional Lock": [89.5185, 67.5969],
        "ACG+DBS": [261.0487, 344.6022],
        "ACG+PAC": [225.1248, 62.7065],
        "CAPS": [502.2609, 547.5881],
    }
    lat = {
        "Traditional Lock": [1865.4666, 1170.7849],
        "ACG+DBS": [1628.9818, 1286.2539],
        "ACG+PAC": [98.042, 41.3239],
        "CAPS": [568.8017, 625.5837],
    }
    lat_sd = {
        "Traditional Lock": [45.1442, 12.2287],
        "ACG+DBS": [151.9554, 135.09],
        "ACG+PAC": [79.1566, 0.8071],
        "CAPS": [76.3257, 232.3939],
    }
    fig, axes = plt.subplots(2, 1, figsize=(5.4, 4.8), sharex=True)
    grouped_bars(axes[0], rates, commits, commit_sd, variants, "committed transactions")
    grouped_bars(axes[1], rates, lat, lat_sd, variants, "mean latency (ms)", log=True)
    panel(axes[0], "a")
    panel(axes[1], "b")
    axes[0].legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.25))
    axes[1].legend().remove()
    save(fig, "fig6_ablation_nature")


def make_improvement_figure(name, title, settings, values, note):
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    x = np.arange(len(settings))
    width = 0.28
    ax.bar(x - width / 2, values["commit"], width=width, color=COL["Committed"], edgecolor="#333333", linewidth=0.45, label="commit gain")
    ax.bar(x + width / 2, values["latency"], width=width, color=COL["Traditional Lock"], edgecolor="#333333", linewidth=0.45, label="latency reduction")
    for xx, yy in zip(x - width / 2, values["commit"]):
        ax.text(xx, yy + 4, f"{yy:.1f}", ha="center", va="bottom", fontsize=6)
    for xx, yy in zip(x + width / 2, values["latency"]):
        ax.text(xx, yy + 4, f"{yy:.1f}", ha="center", va="bottom", fontsize=6)
    ax.set_xticks(x)
    ax.set_xticklabels(settings)
    ax.set_ylabel("improvement over Traditional Lock (%)")
    ax.set_ylim(0, max(max(values["commit"]), max(values["latency"])) * 1.28)
    ax.grid(axis="y")
    ax.legend(ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.17))
    panel(ax, "a")
    save(fig, name)


def make_figure7():
    make_improvement_figure(
        "fig7_endorsement_policy_nature",
        "Robustness under endorsement policies",
        ["Default\n300", "Default\n500", "OR\n300", "OR\n500"],
        {"commit": [129.4, 98.6, 117.3, 131.5], "latency": [67.0, 40.6, 62.7, 54.3]},
        "relative gains remain strong\nacross endorsement policies",
    )


def make_figure8():
    make_improvement_figure(
        "fig8_fabric_parameters_nature",
        "Robustness under block-cutting parameters",
        ["B5\n300", "B5\n500", "B10\n300", "B10\n500", "B50\n300", "B50\n500"],
        {"commit": [83.9, 88.7, 96.5, 119.5, 9.3, 8.4], "latency": [70.0, 64.2, 70.4, 70.5, 65.3, 66.4]},
        "B50 is a boundary case:\ngain shifts to latency control",
    )


def make_figure9():
    rates = ["300 tx/s", "500 tx/s"]
    methods = ["Traditional Lock", "ED-MVCC-Reimpl", "DRT-Reimpl", "CAPS"]
    commits = {
        "Traditional Lock": [2029.4, 1964.4],
        "ED-MVCC-Reimpl": [3102.7, 3869.6],
        "DRT-Reimpl": [4842.3, 4751.5],
        "CAPS": [4440.8, 4049.3],
    }
    commit_sd = {
        "Traditional Lock": [77.0674, 80.8595],
        "ED-MVCC-Reimpl": [75.3437, 111.6564],
        "DRT-Reimpl": [187.7439, 193.9726],
        "CAPS": [132.628, 195.2053],
    }
    lat = {
        "Traditional Lock": [1858.9587, 1149.0489],
        "ED-MVCC-Reimpl": [42.0441, 46.0748],
        "DRT-Reimpl": [1631.6141, 1110.1016],
        "CAPS": [521.3468, 339.5559],
    }
    lat_sd = {
        "Traditional Lock": [7.1312, 4.0666],
        "ED-MVCC-Reimpl": [3.7224, 1.9911],
        "DRT-Reimpl": [38.9807, 9.0129],
        "CAPS": [5.4826, 4.159],
    }
    fig, axes = plt.subplots(2, 1, figsize=(5.6, 4.8), sharex=True)
    grouped_bars(axes[0], rates, commits, commit_sd, methods, "committed transactions")
    grouped_bars(axes[1], rates, lat, lat_sd, methods, "mean latency (ms)", log=True)
    panel(axes[0], "a")
    panel(axes[1], "b")
    axes[0].legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.25))
    axes[1].legend().remove()
    save(fig, "fig9_literature_comparison_nature")


def make_figure10():
    labels = ["Strict\n300", "Strict\n500", "Default\n300", "Default\n500", "Relaxed\n300", "Relaxed\n500"]
    commits = [4012.7, 3925.8, 3665.9, 4114.2, 4242.8, 4166.5]
    commits_sd = [225.6, 239.4, 260.9, 190.0, 289.5, 267.1]
    latency = [350.68, 255.94, 635.30, 411.92, 1018.95, 790.42]
    latency_sd = [38.19, 53.22, 90.18, 66.17, 56.22, 148.72]
    colors = [COL["Traditional Lock"], COL["Traditional Lock"], COL["CAPS"], COL["CAPS"], COL["ACG+PAC"], COL["ACG+PAC"]]
    fig, axes = plt.subplots(1, 2, figsize=(7.05, 3.2))
    x = np.arange(len(labels))
    for ax, vals, errs, ylabel, log in [
        (axes[0], commits, commits_sd, "committed transactions", False),
        (axes[1], latency, latency_sd, "mean latency (ms)", True),
    ]:
        ax.bar(x, vals, yerr=errs, color=colors, edgecolor="#333333", linewidth=0.45, capsize=2, error_kw={"elinewidth": 0.65})
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y")
        if log:
            ax.set_yscale("log")
    panel(axes[0], "a")
    panel(axes[1], "b")
    save(fig, "fig10_pac_parameter_sensitivity_nature")


def main():
    ensure_out()
    make_figure1()
    make_figure2()
    make_figure3()
    make_figure4a()
    make_figure4b()
    make_figure5()
    make_figure6()
    make_figure7()
    make_figure8()
    make_figure9()
    make_figure10()
    print(f"Wrote figures to {OUT}")


if __name__ == "__main__":
    main()
