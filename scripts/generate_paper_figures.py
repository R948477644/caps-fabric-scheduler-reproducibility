from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper_cn_latex" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

font_manager.fontManager.addfont(r"C:\Windows\Fonts\msyh.ttc")
plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.dpi"] = 320

INK = "#1F2937"
MUTED = "#667085"
GRID = "#D0D5DD"
LOCK = "#6B7280"
PA = "#2F8F6B"
DBS = "#2F5E9E"
PAC = "#D8752A"
ED = "#7A5AF8"
DRT = "#B54708"
BAD = "#B42318"
GOOD = "#027A48"
PAPER = "#FFFFFF"
LIGHT_LOCK = "#F2F4F7"
LIGHT_PA = "#E9F6F0"
LIGHT_DBS = "#EAF1FB"
LIGHT_PAC = "#FFF0E4"
LIGHT_BAD = "#FDECEC"


def save(fig, name):
    fig.savefig(OUT / name, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)


def style_axes(ax, ygrid=True):
    if ygrid:
        ax.grid(True, axis="y", color=GRID, alpha=0.75, linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#98A2B3")
    ax.spines["bottom"].set_color("#98A2B3")
    ax.tick_params(colors="#344054", labelsize=9)
    ax.title.set_color(INK)
    ax.xaxis.label.set_color("#344054")
    ax.yaxis.label.set_color("#344054")


def panel_label(ax, label):
    ax.text(
        -0.08,
        1.06,
        label,
        transform=ax.transAxes,
        fontsize=11,
        weight="bold",
        color=INK,
        va="bottom",
    )


def annotate_pct(ax, x, y, text, color=GOOD, dy=0):
    ax.annotate(
        text,
        xy=(x, y),
        xytext=(0, 8 + dy),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=8.5,
        color=color,
        weight="bold",
    )


def box(ax, xy, w, h, text, fc, ec, fontsize=9.5, weight="normal"):
    patch = FancyBboxPatch(
        xy,
        w,
        h,
        boxstyle="round,pad=0.018,rounding_size=0.025",
        fc=fc,
        ec=ec,
        lw=1.15,
    )
    ax.add_patch(patch)
    ax.text(
        xy[0] + w / 2,
        xy[1] + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=INK,
        weight=weight,
        linespacing=1.25,
    )


def arrow(ax, p1, p2, color=MUTED, lw=1.4, style="-|>", ls="-"):
    ax.add_patch(
        FancyArrowPatch(
            p1,
            p2,
            arrowstyle=style,
            mutation_scale=13,
            lw=lw,
            color=color,
            linestyle=ls,
            shrinkA=4,
            shrinkB=4,
        )
    )


def fig_pipeline():
    fig, ax = plt.subplots(figsize=(11.5, 5.3))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.text(0.02, 0.93, "Native Fabric: 冲突在验证阶段暴露", fontsize=13, weight="bold", color=DBS)
    native = [
        ("客户端\n提交提案", LIGHT_LOCK),
        ("背书节点\n模拟执行", LIGHT_DBS),
        ("排序服务\n打包区块", LIGHT_DBS),
        ("Peer 验证\nVSCC/MVCC", LIGHT_PAC),
        ("账本提交\n无效交易留痕", LIGHT_LOCK),
    ]
    xs = [0.04, 0.23, 0.42, 0.61, 0.80]
    for x, (text, fc) in zip(xs, native):
        box(ax, (x, 0.68), 0.135, 0.13, text, fc, DBS, fontsize=9.3)
    for i in range(len(xs) - 1):
        arrow(ax, (xs[i] + 0.135, 0.745), (xs[i + 1], 0.745), DBS)
    ax.add_patch(Rectangle((0.585, 0.64), 0.18, 0.21, fill=False, ec=BAD, lw=1.4, ls="--"))
    ax.text(0.59, 0.60, "热点冲突交易已经消耗背书、排序和广播资源", fontsize=9, color=BAD)

    ax.text(0.02, 0.45, "CAPS: 提交前完成访问集级调度", fontsize=13, weight="bold", color=PA)
    pa_flow = [
        ("客户端\n请求", LIGHT_LOCK),
        ("访问集\n预声明", LIGHT_PA),
        ("压力感知\n准入控制", LIGHT_PAC),
        ("依赖图\n批调度", LIGHT_PA),
        ("Fabric\n提交确认", LIGHT_DBS),
    ]
    for x, (text, fc) in zip(xs, pa_flow):
        box(ax, (x, 0.22), 0.135, 0.13, text, fc, PA, fontsize=9.3)
    for i in range(len(xs) - 1):
        arrow(ax, (xs[i] + 0.135, 0.285), (xs[i + 1], 0.285), PA)

    box(ax, (0.30, 0.045), 0.22, 0.09, "准入拒绝\n或排队超时", "#FFF7E8", PAC, fontsize=9)
    arrow(ax, (0.31, 0.22), (0.36, 0.135), PAC)
    arrow(ax, (0.50, 0.22), (0.45, 0.135), PAC)
    ax.text(0.61, 0.155, "只将互相兼容的交易送入 Fabric", fontsize=9.5, color=GOOD, weight="bold")

    custom = [
        Line2D([0], [0], color=DBS, lw=2, label="Fabric 原生路径"),
        Line2D([0], [0], color=PA, lw=2, label="CAPS 调度路径"),
        Line2D([0], [0], color=PAC, lw=2, label="过载背压路径"),
    ]
    ax.legend(handles=custom, loc="lower right", frameon=False, fontsize=9)
    save(fig, "fig_pipeline.png")


def fig_architecture():
    fig, ax = plt.subplots(figsize=(11.5, 5.8))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    box(ax, (0.035, 0.42), 0.13, 0.16, "100 clients\nHTTP 负载生成", LIGHT_LOCK, MUTED, weight="bold")
    box(ax, (0.22, 0.68), 0.18, 0.14, "ACG\n预声明访问集\n冲突安全检查", LIGHT_PA, PA)
    box(ax, (0.22, 0.43), 0.18, 0.14, "等待窗口\n队列上限 500\n窗口 256", "#F8FAFC", MUTED)
    box(ax, (0.22, 0.18), 0.18, 0.14, "PAC\n压力函数 Pt\n负载削减/超时", LIGHT_PAC, PAC)
    box(ax, (0.49, 0.43), 0.18, 0.14, "DBS\n依赖图选择\n兼容批提交", LIGHT_PA, PA)

    ax.add_patch(FancyBboxPatch((0.72, 0.08), 0.23, 0.82, boxstyle="round,pad=0.02", fc="#F8FAFC", ec=DBS, lw=1.3))
    ax.text(0.835, 0.84, "真实 Fabric 网络", ha="center", va="center", fontsize=12, weight="bold", color=DBS)
    box(ax, (0.755, 0.62), 0.16, 0.12, "4 peers\n背书/提交", LIGHT_DBS, DBS)
    box(ax, (0.755, 0.39), 0.16, 0.12, "1 Raft orderer\n排序服务", LIGHT_DBS, DBS)
    box(ax, (0.755, 0.17), 0.16, 0.12, "World state\n账本状态", LIGHT_DBS, DBS)

    arrow(ax, (0.165, 0.50), (0.22, 0.74), MUTED)
    arrow(ax, (0.31, 0.68), (0.31, 0.57), MUTED)
    arrow(ax, (0.40, 0.50), (0.49, 0.50), PA, lw=1.8)
    arrow(ax, (0.67, 0.50), (0.755, 0.68), DBS)
    arrow(ax, (0.67, 0.50), (0.755, 0.45), DBS)
    arrow(ax, (0.835, 0.39), (0.835, 0.29), DBS)
    arrow(ax, (0.31, 0.43), (0.31, 0.32), PAC)
    arrow(ax, (0.40, 0.25), (0.49, 0.44), PAC)
    arrow(ax, (0.22, 0.24), (0.165, 0.44), PAC)
    ax.text(0.07, 0.34, "准入拒绝\n显式背压", fontsize=9, color=PAC, weight="bold")
    ax.text(0.51, 0.62, "兼容交易批次", fontsize=9.5, color=PA, weight="bold")
    save(fig, "fig_architecture.png")


def fig_pressure():
    q = np.arange(0, 501)
    qmax = 500
    qla = 128
    theta_q = 0.3
    p_queue = q / (theta_q * qmax)
    p_hot = np.where(q >= qla, 1.12, 0.0)
    p = np.maximum(p_queue, p_hot)

    fig, axes = plt.subplots(1, 2, figsize=(11.3, 4.4), gridspec_kw={"width_ratios": [1.3, 1]})
    ax = axes[0]
    ax.plot(q, p_queue, color=DBS, lw=2.2, label=r"队列压力 $Q_t/(0.3Q_{max})$")
    ax.plot(q, p_hot, color=PAC, lw=2.2, label="热点门控项")
    ax.plot(q, p, color=PA, lw=2.8, label=r"综合压力 $P_t$")
    ax.axhline(1, color=BAD, lw=1.4, linestyle="--", label="模式切换阈值")
    ax.axvline(qla, color=PAC, lw=1.2, linestyle=":")
    ax.axvline(theta_q * qmax, color=DBS, lw=1.2, linestyle=":")
    ax.fill_between(q, 0, 1, where=p < 1, color=LIGHT_PA, alpha=0.65)
    ax.fill_between(q, 0, np.minimum(p, 3.4), where=p >= 1, color="#FFF4ED", alpha=0.8)
    ax.set_xlabel("等待队列长度 $Q_t$")
    ax.set_ylabel("归一化压力")
    ax.set_title("压力函数触发准入策略切换")
    ax.set_ylim(0, 3.4)
    style_axes(ax)
    ax.legend(frameon=False, fontsize=8.7, loc="upper left")
    panel_label(ax, "(a)")

    ax = axes[1]
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    box(ax, (0.09, 0.70), 0.82, 0.16, "普通模式\n队列上限 Qmax=500", LIGHT_PA, PA, fontsize=10, weight="bold")
    box(ax, (0.09, 0.42), 0.82, 0.16, "压力控制模式\n准入窗口 Qla=128", LIGHT_PAC, PAC, fontsize=10, weight="bold")
    box(ax, (0.09, 0.14), 0.82, 0.16, "主动负载削减\n热点准入拒绝 / 排队超时", LIGHT_BAD, BAD, fontsize=10, weight="bold")
    arrow(ax, (0.50, 0.70), (0.50, 0.58), MUTED)
    arrow(ax, (0.50, 0.42), (0.50, 0.30), MUTED)
    ax.text(0.50, 0.62, r"$P_t \geq 1$", ha="center", fontsize=10, color=BAD, weight="bold")
    ax.text(0.50, 0.34, "队列满或热点积压", ha="center", fontsize=9.5, color=BAD)
    panel_label(ax, "(b)")
    save(fig, "fig_pressure_modes.png")


def fig_exp1():
    rates = np.array([100, 150, 200, 300, 400, 500])
    lock_ok = np.array([1922, 1922, 1942, 1904, 1822, 2002])
    pa_ok = np.array([2000, 3000, 4000, 4320, 3915, 4435])
    lock_rej = np.array([78, 1078, 2058, 4096, 6178, 7998])
    pa_rej = np.array([0, 0, 0, 1680, 4085, 5565])
    lock_lat = np.array([10164.30, 7949.89, 6313.99, 3447.98, 3250.04, 2678.59])
    pa_lat = np.array([325.86, 108.69, 215.34, 636.06, 574.90, 411.31])
    ok_gain = (pa_ok / lock_ok - 1) * 100
    lat_drop = (1 - pa_lat / lock_lat) * 100

    fig, axes = plt.subplots(2, 2, figsize=(12.0, 7.6))
    x = np.arange(len(rates))
    w = 0.36

    ax = axes[0, 0]
    ax.bar(x - w / 2, lock_ok, w, color=LOCK, label="Traditional Lock")
    ax.bar(x + w / 2, pa_ok, w, color=PA, label="CAPS")
    for i in [2, 3, 5]:
        annotate_pct(ax, x[i] + w / 2, pa_ok[i], f"+{ok_gain[i]:.0f}%")
    ax.set_xticks(x, rates)
    ax.set_ylabel("已提交交易数")
    ax.set_title("成功提交交易")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9)
    panel_label(ax, "(a)")

    ax = axes[0, 1]
    ax.bar(x - w / 2, lock_rej, w, color="#A3AAB8", label="Traditional Lock")
    ax.bar(x + w / 2, pa_rej, w, color=PAC, label="CAPS")
    ax.set_xticks(x, rates)
    ax.set_ylabel("准入拒绝交易数")
    ax.set_title("过载下的主动负载削减")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9)
    panel_label(ax, "(b)")

    ax = axes[1, 0]
    ax.plot(rates, lock_lat, marker="o", lw=2.4, color=LOCK, label="Traditional Lock")
    ax.plot(rates, pa_lat, marker="s", lw=2.4, color=PA, label="CAPS")
    for i in [0, 1, 5]:
        annotate_pct(ax, rates[i], pa_lat[i], f"-{lat_drop[i]:.0f}%", GOOD, dy=-2)
    ax.set_yscale("log")
    ax.set_xlabel("输入负载 (tx/s)")
    ax.set_ylabel("平均延迟 (ms, log)")
    ax.set_title("客户端平均延迟")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9)
    panel_label(ax, "(c)")

    ax = axes[1, 1]
    ax.plot(rates, ok_gain, marker="o", lw=2.2, color=PA, label="已提交交易数提升")
    ax.plot(rates, lat_drop, marker="s", lw=2.2, color=DBS, label="延迟下降")
    ax.axhline(0, color=GRID, lw=1)
    ax.set_xlabel("输入负载 (tx/s)")
    ax.set_ylabel("相对 Traditional Lock (%)")
    ax.set_title("相对收益随负载变化")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9)
    panel_label(ax, "(d)")

    fig.tight_layout()
    save(fig, "fig_exp1_main.png")


def fig_exp2():
    hot = np.array([20, 50, 100, 200, 500])
    lock_ok = np.array([702, 1512, 2122, 2012, 1982])
    pa_ok = np.array([272, 3865, 3942, 4303, 3720])
    lock_lat = np.array([9208.71, 8137.64, 4243.59, 2026.48, 1974.22])
    pa_lat = np.array([528.95, 587.79, 660.95, 519.51, 777.72])
    lock_q = np.array([65162.71, 31292.96, 11331.51, 5537.19, 5493.37])
    pa_q = np.array([1478.01, 697.52, 600.50, 527.63, 604.00])
    ok_gain = (pa_ok / lock_ok - 1) * 100
    lat_drop = (1 - pa_lat / lock_lat) * 100

    fig, axes = plt.subplots(2, 2, figsize=(12.0, 7.6))
    x = np.arange(len(hot))
    w = 0.36

    ax = axes[0, 0]
    ax.bar(x - w / 2, lock_ok, w, color=LOCK, label="Traditional Lock")
    ax.bar(x + w / 2, pa_ok, w, color=PA, label="CAPS")
    ax.set_xticks(x, hot)
    ax.set_ylabel("已提交交易数")
    ax.set_title("热点账户数变化下的成功提交")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9)
    panel_label(ax, "(a)")

    ax = axes[0, 1]
    ax.plot(x, lock_lat, marker="o", lw=2.3, color=LOCK, label="Traditional Lock")
    ax.plot(x, pa_lat, marker="s", lw=2.3, color=PA, label="CAPS")
    ax.set_yscale("log")
    ax.set_xticks(x, hot)
    ax.set_ylabel("平均延迟 (ms, log)")
    ax.set_title("冲突率降低时的延迟变化")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9)
    panel_label(ax, "(b)")

    ax = axes[1, 0]
    ax.plot(x, lock_q, marker="o", lw=2.3, color=LOCK, label="Traditional Lock")
    ax.plot(x, pa_q, marker="s", lw=2.3, color=PA, label="CAPS")
    ax.set_yscale("log")
    ax.set_xticks(x, hot)
    ax.set_xlabel("hotAccountCount")
    ax.set_ylabel("平均排队时间 (ms, log)")
    ax.set_title("队列压力被显著压缩")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9)
    panel_label(ax, "(c)")

    ax = axes[1, 1]
    ax.bar(x - w / 2, ok_gain, w, color=np.where(ok_gain >= 0, PA, BAD), label="已提交交易数提升")
    ax.bar(x + w / 2, lat_drop, w, color=DBS, label="延迟下降")
    ax.axhline(0, color=GRID, lw=1)
    ax.set_xticks(x, hot)
    ax.set_xlabel("hotAccountCount")
    ax.set_ylabel("相对 Traditional Lock (%)")
    ax.set_title("收益与极端热点边界")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9)
    panel_label(ax, "(d)")

    fig.tight_layout()
    save(fig, "fig_exp2_conflict.png")


def fig_exp3():
    methods = ["Lock", "ACG+DBS", "ACG+PAC", "CAPS"]
    colors = [LOCK, DBS, PAC, PA]
    ok_300 = np.array([1995, 4606, 3910, 4117])
    lat_300 = np.array([4281.90, 1711.48, 645.86, 619.37])
    q_300 = np.array([12149.94, 1946.64, 591.31, 589.50])
    ok_500 = np.array([1796, 4522, 3783, 3643])
    lat_500 = np.array([2160.40, 1143.43, 367.45, 371.89])
    q_500 = np.array([11131.30, 2220.76, 641.61, 678.35])

    fig, axes = plt.subplots(2, 2, figsize=(11.8, 7.4))
    x = np.arange(len(methods))

    ax = axes[0, 0]
    ax.bar(x, ok_300, color=colors)
    ax.set_xticks(x, methods, rotation=12)
    ax.set_ylabel("已提交交易数")
    ax.set_title("300 tx/s: 模块对有效提交的贡献")
    style_axes(ax)
    panel_label(ax, "(a)")

    ax = axes[0, 1]
    ax.bar(x, lat_300, color=colors)
    ax.set_xticks(x, methods, rotation=12)
    ax.set_ylabel("平均延迟 (ms)")
    ax.set_title("300 tx/s: PAC 压缩排队延迟")
    style_axes(ax)
    panel_label(ax, "(b)")

    ax = axes[1, 0]
    ax.plot(methods, q_300, marker="o", color=DBS, lw=2.2, label="300 tx/s")
    ax.plot(methods, q_500, marker="s", color=PAC, lw=2.2, label="500 tx/s")
    ax.set_yscale("log")
    ax.set_ylabel("平均排队时延 (ms, log)")
    ax.set_title("调度模块对队列压力的影响")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9)
    panel_label(ax, "(c)")

    ax = axes[1, 1]
    w = 0.36
    ax.bar(x - w / 2, ok_500, w, color=colors, alpha=0.75, label="已提交交易")
    ax2 = ax.twinx()
    ax2.plot(x + w / 2, lat_500, marker="o", color=BAD, lw=2.2, label="Latency")
    ax.set_xticks(x, methods, rotation=12)
    ax.set_ylabel("已提交交易数")
    ax2.set_ylabel("平均延迟 (ms)")
    ax.set_title("500 tx/s: 极端过载下的边界")
    style_axes(ax)
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.spines["right"].set_color("#98A2B3")
    ax2.tick_params(colors="#344054", labelsize=9)
    panel_label(ax, "(d)")

    fig.tight_layout()
    save(fig, "fig_exp3_ablation.png")


def fig_exp4():
    labels = ["default\n300", "default\n500", "OR\n300", "OR\n500"]
    ok_gain = np.array([125.2, 116.9, 132.9, 128.9])
    lat_drop = np.array([85.1, 85.0, 86.4, 87.2])
    comp_gain = np.array([298.0, 315.9, 309.0, 366.2])
    x = np.arange(len(labels))
    w = 0.27
    fig, ax = plt.subplots(figsize=(9.3, 4.8))
    ax.bar(x - w, ok_gain, width=w, color=PA, label="已提交交易数提升")
    ax.bar(x, lat_drop, width=w, color=DBS, label="延迟下降")
    ax.bar(x + w, comp_gain, width=w, color=PAC, label="有效吞吐量提升")
    ax.set_xticks(x, labels)
    ax.set_ylabel("相对 Traditional Lock (%)")
    ax.set_title("背书策略变化下收益保持稳定")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.14))
    save(fig, "fig_exp4_policy.png")


def fig_exp5():
    labels = ["B10\n300", "B10\n500", "B5\n300", "B5\n500", "B50\n300", "B50\n500"]
    lock_ok = np.array([1922, 1902, 2187, 2027, 755, 787])
    pa_ok = np.array([4751, 4683, 4195, 4830, 367, 338])
    lock_lat = np.array([3935.11, 2369.74, 2762.51, 1540.37, 4283.05, 2661.31])
    pa_lat = np.array([523.34, 351.49, 1537.71, 478.06, 632.32, 400.17])
    lock_q = np.array([406.59, 416.81, 419.66, 421.94, 313.62, 320.79])
    pa_q = np.array([118.48, 120.50, 120.05, 121.95, 84.43, 79.56])
    ttl = np.array([13, 13, 10, 11, 315, 360])

    fig, axes = plt.subplots(2, 2, figsize=(12.0, 7.6))
    x = np.arange(len(labels))
    w = 0.36

    ax = axes[0, 0]
    ax.bar(x - w / 2, lock_ok, w, color=LOCK, label="Traditional Lock")
    ax.bar(x + w / 2, pa_ok, w, color=PA, label="CAPS")
    ax.set_xticks(x, labels)
    ax.set_ylabel("已提交交易数")
    ax.set_title("不同出块参数下的成功提交")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9)
    panel_label(ax, "(a)")

    ax = axes[0, 1]
    ax.plot(x, lock_lat, marker="o", lw=2.3, color=LOCK, label="Traditional Lock")
    ax.plot(x, pa_lat, marker="s", lw=2.3, color=PA, label="CAPS")
    ax.set_yscale("log")
    ax.set_xticks(x, labels)
    ax.set_ylabel("平均延迟 (ms, log)")
    ax.set_title("延迟收益不依赖单一参数")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9)
    panel_label(ax, "(b)")

    ax = axes[1, 0]
    ax.bar(x - w / 2, lock_q, w, color="#A3AAB8", label="Traditional Lock")
    ax.bar(x + w / 2, pa_q, w, color=PA, label="CAPS")
    ax.set_xticks(x, labels)
    ax.set_xlabel("参数组 / 输入负载")
    ax.set_ylabel("平均排队时延 (ms)")
    ax.set_title("排队时延保持低位")
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9)
    panel_label(ax, "(c)")

    ax = axes[1, 1]
    ax.bar(x, ttl, color=np.where(ttl > 100, BAD, PAC))
    ax.set_xticks(x, labels)
    ax.set_xlabel("参数组 / 输入负载")
    ax.set_ylabel("排队超时交易数")
    ax.set_title("大区块参数触发超时保护")
    style_axes(ax)
    panel_label(ax, "(d)")

    fig.tight_layout()
    save(fig, "fig_exp5_params.png")


if __name__ == "__main__":
    fig_pipeline()
    fig_architecture()
    fig_pressure()
    fig_exp1()
    fig_exp2()
    fig_exp3()
    fig_exp4()
    fig_exp5()
    print(f"generated figures in {OUT}")


