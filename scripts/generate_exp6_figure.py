from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.ticker import NullFormatter


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper_cn_latex" / "figures"
CSV = ROOT / "experiment6_literature_comparison" / "experiment6_full_repeats_summary.csv"
OUT.mkdir(parents=True, exist_ok=True)

font_manager.fontManager.addfont(r"C:\Windows\Fonts\msyh.ttc")
plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.dpi"] = 320

INK = "#1F2937"
GRID = "#D0D5DD"
COLORS = {
    "Traditional Lock": "#6B7280",
    "ED-MVCC-Reimpl": "#7A5AF8",
    "DRT-Reimpl": "#B54708",
    "CAPS": "#2F8F6B",
}
SHORT = {
    "Traditional Lock": "Lock",
    "ED-MVCC-Reimpl": "ED-MVCC",
    "DRT-Reimpl": "DRT",
    "CAPS": "CAPS",
}


def style_axes(ax):
    ax.grid(True, axis="y", color=GRID, alpha=0.75, linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#98A2B3")
    ax.spines["bottom"].set_color("#98A2B3")
    ax.tick_params(colors="#344054", labelsize=9)
    ax.title.set_color(INK)


def panel_label(ax, label):
    ax.text(-0.08, 1.06, label, transform=ax.transAxes, fontsize=11, weight="bold", color=INK)


def bars_by_tps(ax, df, metric, sd, ylabel, title, log=False):
    methods = list(COLORS)
    x = np.arange(len(methods))
    width = 0.36
    for offset, tps, alpha, hatch in [(-width / 2, 300, 0.72, ""), (width / 2, 500, 1.0, "//")]:
        vals = [df[(df.method == m) & (df.tps == tps)][metric].iloc[0] for m in methods]
        errs = [df[(df.method == m) & (df.tps == tps)][sd].iloc[0] for m in methods]
        ax.bar(
            x + offset,
            vals,
            width,
            yerr=errs,
            capsize=3,
            color=[COLORS[m] for m in methods],
            alpha=alpha,
            hatch=hatch,
            edgecolor="white",
            linewidth=0.7,
            label=f"{tps} tx/s",
        )
    ax.set_xticks(x, [SHORT[m] for m in methods])
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if log:
        ax.set_yscale("log")
    style_axes(ax)


def main():
    df = pd.read_csv(CSV)
    df["method"] = df["method"].replace({"PA-VSCD": "CAPS"})

    fig, axes = plt.subplots(2, 2, figsize=(12.0, 7.6))
    bars_by_tps(axes[0, 0], df, "ok_mean", "ok_sd", "已提交交易数", "成功提交交易及其波动")
    panel_label(axes[0, 0], "(a)")

    bars_by_tps(axes[0, 1], df, "429_mean", "429_sd", "准入拒绝交易数", "主动负载削减")
    panel_label(axes[0, 1], "(b)")

    bars_by_tps(axes[1, 0], df, "latency_ms_mean", "latency_ms_sd", "平均延迟 (ms, log)", "客户端平均延迟", log=True)
    panel_label(axes[1, 0], "(c)")

    ax = axes[1, 1]
    markers = {300: "o", 500: "s"}
    for method in COLORS:
        for tps in [300, 500]:
            row = df[(df.method == method) & (df.tps == tps)].iloc[0]
            ax.scatter(
                row["latency_ms_mean"],
                row["ok_mean"],
                s=90,
                marker=markers[tps],
                color=COLORS[method],
                edgecolor="white",
                linewidth=0.8,
            )
            ax.text(
                row["latency_ms_mean"] * 1.05,
                row["ok_mean"],
                f"{SHORT[method]}-{tps}",
                fontsize=8,
                color=COLORS[method],
                va="center",
            )
    ax.set_xscale("log")
    ax.set_xlim(90, 6200)
    ax.set_xticks([100, 300, 600, 1000, 3000, 6000])
    ax.set_xticklabels(["100", "300", "600", "1000", "3000", "6000"])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("平均延迟 (ms, log)")
    ax.set_ylabel("已提交交易数")
    ax.set_title("吞吐-延迟折中位置")
    style_axes(ax)
    panel_label(ax, "(d)")

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles[:2], labels[:2], frameon=False, fontsize=9, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(OUT / "fig_exp6_literature_comparison.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(OUT / "fig_exp6_literature_comparison.png")


if __name__ == "__main__":
    main()


