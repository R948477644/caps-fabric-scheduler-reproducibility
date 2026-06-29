from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "vectorized_favorite_figures_20260627"


plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif", "Times"]
plt.rcParams["mathtext.fontset"] = "dejavuserif"
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42

mpl.rcParams.update(
    {
        "font.size": 10,
        "axes.linewidth": 1.0,
        "savefig.dpi": 600,
    }
)


GREEN = "#0B6E1A"
BLUE = "#052C91"
BLUE2 = "#1139B7"
ORANGE = "#E56700"
RED = "#E21A00"
BLACK = "#111111"
GRAY = "#555555"


def ensure_out() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def save(fig: plt.Figure, name: str) -> None:
    ensure_out()
    for ext in ("svg", "pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def rounded_box(ax, xy, w, h, text="", ec=BLACK, fc="white", lw=1.1, r=0.08, fontsize=10, weight=None, style=None, color=BLACK):
    box = FancyBboxPatch(
        xy,
        w,
        h,
        boxstyle=f"round,pad=0.03,rounding_size={r}",
        ec=ec,
        fc=fc,
        lw=lw,
    )
    ax.add_patch(box)
    if text:
        ax.text(
            xy[0] + w / 2,
            xy[1] + h / 2,
            text,
            ha="center",
            va="center",
            fontsize=fontsize,
            fontweight=weight,
            fontstyle=style,
            color=color,
            linespacing=1.15,
        )
    return box


def arrow(ax, p1, p2, color=BLACK, lw=1.4, ls="-", ms=12, z=4, rad=0):
    ax.add_patch(
        FancyArrowPatch(
            p1,
            p2,
            arrowstyle="-|>",
            mutation_scale=ms,
            lw=lw,
            linestyle=ls,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
            zorder=z,
        )
    )


def line(ax, p1, p2, color=BLACK, lw=1.2, ls="-", z=2):
    ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color, lw=lw, ls=ls, zorder=z)


def figure_architecture():
    fig, ax = plt.subplots(figsize=(14, 7.2))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 10)
    ax.axis("off")

    rounded_box(ax, (3.35, 1.7), 9.4, 7.9, "", ec=BLACK, lw=1.2, r=0.12)
    ax.text(8.05, 9.25, "CAPS Scheduler", ha="center", va="center", fontsize=18, fontweight="bold")

    rounded_box(ax, (0.2, 5.0), 1.95, 2.4, "100 Clients /\nHTTP Load\nGenerator", ec=BLACK, lw=1.1, r=0.10, fontsize=13, weight="bold")
    rounded_box(
        ax,
        (4.3, 7.35),
        2.9,
        1.25,
        "ACG\nAccess-set Declaration\nConflict-safe Check",
        ec=BLACK,
        lw=1.1,
        r=0.10,
        fontsize=12,
        weight="bold",
    )
    ax.text(5.75, 7.02, "Parse declared read/write sets", ha="center", fontsize=10, fontstyle="italic")

    rounded_box(
        ax,
        (3.8, 4.9),
        3.8,
        1.35,
        "Waiting Window\nQueue Limit: 500\nCandidate Window: 256",
        ec=BLACK,
        lw=1.1,
        r=0.10,
        fontsize=12,
        weight="bold",
    )
    rounded_box(
        ax,
        (8.45, 4.9),
        3.55,
        1.35,
        "DBS\nDependency-aware Selection\nCompatible Batch Submission",
        ec=BLUE2,
        lw=1.25,
        r=0.10,
        fontsize=10,
        weight="bold",
    )
    ax.text(10.22, 4.35, "Select conflict-compatible\ntransactions", ha="center", fontsize=10, fontstyle="italic")

    rounded_box(
        ax,
        (3.8, 2.2),
        3.9,
        1.35,
        "PAC\nPressure Function $P_t$\nLoad Shedding & Queue Timeout",
        ec=ORANGE,
        lw=1.25,
        r=0.10,
        fontsize=11,
        weight="bold",
    )
    ax.text(5.75, 1.85, "Overload protection", ha="center", fontsize=10, fontstyle="italic")

    rounded_box(ax, (14.3, 1.7), 5.45, 7.9, "", ec=BLUE, lw=1.35, r=0.12)
    ax.text(17.0, 9.25, "Real Fabric Network", ha="center", va="center", fontsize=16, fontweight="bold", color=BLUE)
    rounded_box(ax, (14.7, 6.65), 4.65, 1.9, "", ec=BLUE, lw=1.2, r=0.12)
    ax.text(17.0, 8.15, "4 Peers", ha="center", fontsize=13, fontweight="bold", color=BLUE)
    ax.text(17.0, 7.82, "Endorsement & Ledger Commit", ha="center", fontsize=10, fontstyle="italic")
    for i in range(4):
        rounded_box(ax, (14.9 + i * 1.15, 7.0), 0.9, 0.55, f"Peer {i+1}", ec=BLUE, lw=1.1, r=0.05, fontsize=10)
    rounded_box(ax, (14.65, 4.45), 2.85, 1.25, "1 Raft Orderer\nOrdering Service", ec=BLUE, lw=1.2, r=0.08, fontsize=12, weight="bold")
    rounded_box(ax, (14.7, 2.0), 4.65, 1.15, "World State\nLedger State", ec=BLUE, lw=1.2, r=0.08, fontsize=12, weight="bold")

    # Data path.
    line(ax, (2.15, 6.45), (2.9, 6.45), GREEN, 1.8)
    line(ax, (2.9, 6.45), (2.9, 7.98), GREEN, 1.8)
    arrow(ax, (2.9, 7.98), (4.3, 7.98), GREEN, 1.8, ms=14)
    arrow(ax, (5.75, 7.35), (5.75, 6.25), GREEN, 1.8, ms=14)
    arrow(ax, (7.6, 5.58), (8.45, 5.58), GREEN, 1.8, ms=14)
    line(ax, (12.0, 5.58), (13.95, 5.58), GREEN, 1.8)
    line(ax, (13.95, 5.58), (13.95, 7.65), GREEN, 1.8)
    arrow(ax, (13.95, 7.65), (14.7, 7.65), GREEN, 1.8, ms=14)
    ax.text(13.25, 6.45, "Submit\ncompatible\nbatch", ha="center", va="center", fontsize=11, color=GREEN)

    arrow(ax, (15.85, 6.65), (15.85, 5.7), GREEN, 1.8, ms=14)
    arrow(ax, (15.85, 4.45), (15.85, 3.15), GREEN, 1.8, ms=14)
    arrow(ax, (18.75, 6.65), (18.75, 3.15), GREEN, 1.8, ms=14)

    # Control paths.
    arrow(ax, (5.75, 4.9), (5.75, 3.55), ORANGE, 1.5, "--", ms=12)
    ax.text(4.55, 4.05, "Queue pressure /\nbacklog", fontsize=10, fontstyle="italic", color=ORANGE)
    line(ax, (7.7, 2.9), (10.2, 2.9), ORANGE, 1.5, "--")
    arrow(ax, (10.2, 2.9), (10.2, 4.35), ORANGE, 1.5, "--", ms=12)
    ax.text(8.15, 2.45, "Scheduling mode /\npressure-aware control", fontsize=10, fontstyle="italic", color=ORANGE)

    line(ax, (3.8, 2.9), (1.15, 2.9), RED, 1.5, "--")
    arrow(ax, (1.15, 2.9), (1.15, 5.0), RED, 1.5, "--", ms=12)
    ax.text(0.95, 2.18, "Admission Rejection /\nExplicit Backpressure", fontsize=10, fontstyle="italic", color=RED)

    ax.text(12.9, 4.35, "Forward only\nadmitted and\ncompatible\ntransactions", ha="center", fontsize=10, fontstyle="italic")

    # Legend.
    y = 0.75
    arrow(ax, (0.55, y), (1.65, y), GREEN, 1.7, ms=12)
    ax.text(1.8, y, "Main CAPS data path", va="center", fontsize=9)
    arrow(ax, (4.2, y), (5.2, y), ORANGE, 1.5, ms=12)
    ax.text(5.35, y, "PAC / backpressure /\noverload control", va="center", fontsize=9)
    arrow(ax, (7.85, y), (8.85, y), ORANGE, 1.5, "--", ms=12)
    ax.text(9.0, y, "PAC control /\nscheduler guidance", va="center", fontsize=9)
    arrow(ax, (11.25, y), (12.25, y), RED, 1.5, "--", ms=12)
    ax.text(12.4, y, "Rejection / timeout\nfeedback", va="center", fontsize=9)
    rounded_box(ax, (14.3, y - 0.25), 0.85, 0.45, "", ec=BLUE, lw=1.0, r=0.05)
    ax.text(15.25, y, "Fabric network\ncomponents", va="center", fontsize=9)
    rounded_box(ax, (17.35, y - 0.25), 0.85, 0.45, "", ec=BLUE2, lw=1.0, r=0.05)
    ax.text(18.45, y, "DBS module", va="center", fontsize=9)

    save(fig, "fig2_architecture_favorite_vector")


def lifeline(ax, x, label):
    ax.text(x, 9.35, label, ha="center", va="bottom", fontsize=8)
    line(ax, (x, 0.9), (x, 9.25), BLACK, 0.8, "--")


def activation(ax, x, y, h, color=BLACK):
    ax.add_patch(Rectangle((x - 0.055, y), 0.11, h, ec=color, fc="white", lw=0.7, zorder=5))


def msg(ax, x1, y1, x2, y2, text, color, lw=0.9, ls="-", fontsize=6.2, above=True):
    arrow(ax, (x1, y1), (x2, y2), color=color, lw=lw, ls=ls, ms=7)
    ax.text(
        (x1 + x2) / 2,
        y1 + (0.13 if above else -0.20),
        text,
        ha="center",
        va="bottom" if above else "top",
        fontsize=fontsize,
        color=color if color in (GREEN, RED) else BLACK,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.86, "pad": 0.45},
        zorder=8,
    )


def figure_eov_flow():
    fig, ax = plt.subplots(figsize=(18.5, 8.5))
    ax.set_xlim(0, 21.6)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Clean manuscript version: keep the argument of the original sequence
    # diagram, but remove dense step labels that collide at journal width.
    ax.text(5.0, 9.75, "(a) Native Fabric", ha="center", fontsize=18)
    ax.text(15.55, 9.75, "(b) Fabric with CAPS", ha="center", fontsize=18)

    def swimlane(x0, x1, y, label, color="#2458FF"):
        line(ax, (x0, y), (x1, y), color, 0.9, "--")
        ax.text(x1 + 0.12, y + 0.02, label, fontsize=9, va="bottom", color=BLACK)

    def actor(x, y, text, color=BLACK):
        rounded_box(ax, (x - 0.62, y - 0.28), 1.24, 0.56, text, ec=color, lw=1.0, r=0.05, fontsize=8)

    def step_box(x, y, w, h, text, color=BLACK, fc="white", fontsize=8.5):
        rounded_box(ax, (x, y), w, h, text, ec=color, fc=fc, lw=1.05, r=0.05, fontsize=fontsize)

    # Phase separators.
    for y, label in [(6.45, "Execution"), (4.45, "Ordering"), (2.25, "Validation and commit")]:
        swimlane(0.35, 9.7, y, label)
        swimlane(10.35, 20.25, y, label)

    # Native Fabric flow.
    native_x = [0.9, 2.45, 4.1, 5.75, 7.35, 8.95]
    native_labels = ["Client", "Gateway", "Endorsers", "Orderer", "Committers", "Ledger"]
    for x, lab in zip(native_x, native_labels):
        actor(x, 8.45, lab)
    arrow(ax, (1.52, 8.45), (1.83, 8.45), BLUE2, 1.4, ms=10)
    msg(ax, 0.9, 7.95, 2.45, 7.95, "proposal", BLUE2, fontsize=7)
    msg(ax, 2.45, 7.45, 4.1, 7.45, "endorsement simulation", BLUE2, fontsize=7)
    step_box(3.15, 6.78, 1.9, 0.48, "read/write set", BLACK, "#FFFFFF", fontsize=7.4)
    msg(ax, 4.1, 5.85, 2.45, 5.85, "endorsement response", BLUE2, fontsize=7)
    msg(ax, 2.45, 5.1, 7.35, 5.1, "submit signed transaction", BLUE2, fontsize=7)
    step_box(6.25, 4.58, 2.2, 0.5, "consensus and block cut", BLACK, "#FFFFFF", fontsize=7.4)
    msg(ax, 7.35, 3.65, 8.35, 3.65, "block broadcast", BLUE2, fontsize=7)
    rounded_box(
        ax,
        (5.62, 2.72),
        3.55,
        0.92,
        "VSCC and MVCC validation\nconflict detected late",
        ec=RED,
        fc="#FFF6F5",
        lw=1.2,
        r=0.05,
        fontsize=8.1,
        color=RED,
    )
    msg(ax, 8.35, 1.75, 2.45, 1.75, "commit event", BLUE2, fontsize=7)
    ax.text(
        5.05,
        0.72,
        "Endorsement, ordering, broadcast, and validation resources\nare already consumed before MVCC invalidation is known.",
        ha="center",
        fontsize=8.2,
        color=RED,
        fontstyle="italic",
    )

    # CAPS flow.
    caps_x = [10.85, 12.65, 14.35, 16.05, 17.75, 19.35]
    caps_labels = ["Client", "CAPS", "Gateway", "Endorsers", "Orderer", "Ledger"]
    for x, lab in zip(caps_x, caps_labels):
        actor(x, 8.45, lab, BLUE if lab == "CAPS" else BLACK)
    msg(ax, 10.85, 7.95, 12.65, 7.95, "request", GREEN, fontsize=7)
    rounded_box(
        ax,
        (11.58, 6.78),
        2.15,
        0.92,
        "derive access sets\ncheck conflicts and pressure",
        ec=BLUE,
        fc="#F7FAFF",
        lw=1.15,
        r=0.05,
        fontsize=7.6,
        color=BLUE,
    )
    rounded_box(
        ax,
        (10.62, 5.18),
        2.08,
        0.88,
        "reject or timeout\nbefore Fabric",
        ec=RED,
        fc="#FFF6F5",
        lw=1.1,
        r=0.05,
        fontsize=7.4,
        color=RED,
    )
    arrow(ax, (12.12, 6.78), (11.66, 6.06), RED, 1.1, "--", ms=8)
    msg(ax, 12.65, 5.55, 14.35, 5.55, "admitted compatible transaction", GREEN, fontsize=7)
    msg(ax, 14.35, 5.05, 16.05, 5.05, "endorsement simulation", GREEN, fontsize=7)
    step_box(15.18, 4.62, 1.85, 0.48, "read/write set", BLACK, "#FFFFFF", fontsize=7.4)
    msg(ax, 16.05, 3.85, 14.35, 3.85, "endorsement response", GREEN, fontsize=7)
    msg(ax, 14.35, 3.18, 17.75, 3.18, "submit transaction", GREEN, fontsize=7)
    step_box(16.82, 2.56, 1.96, 0.5, "consensus and block cut", BLACK, "#FFFFFF", fontsize=7.4)
    msg(ax, 17.75, 2.05, 19.0, 2.05, "block broadcast", GREEN, fontsize=7)
    rounded_box(
        ax,
        (17.08, 0.98),
        2.82,
        0.78,
        "validation and commit\n(no CAPS-admitted MVCC conflict\nunder conservative prediction)",
        ec=GREEN,
        fc="#F5FFF6",
        lw=1.15,
        r=0.05,
        fontsize=7.0,
        color=GREEN,
    )
    msg(ax, 19.0, 0.55, 14.35, 0.55, "commit event", GREEN, fontsize=7)
    ax.text(
        15.55,
        0.17,
        "CAPS moves conflict and overload decisions before Gateway submission.",
        ha="center",
        fontsize=8.2,
        color=GREEN,
        fontstyle="italic",
    )

    # The simplified manuscript version above is intentionally not emitted here:
    # keep the user's original detailed sequence-diagram structure and only fix
    # text collisions in that original layout.
    ax.clear()
    ax.set_xlim(0, 21.6)
    ax.set_ylim(0, 10)
    ax.axis("off")

    ax.text(4.8, 9.85, "(a) Native Fabric", ha="center", fontsize=16)
    ax.text(15.1, 9.85, "(b) Fabric with CAPS", ha="center", fontsize=16)

    # Left panel.
    xs = [0.5, 1.8, 3.3, 4.65, 5.8, 7.0, 8.1]
    labels = ["Client", "Fabric\nGateway", "Endorsing\nPeer 1", "Endorsing\nPeer 2", "Ordering\nService", "Committing\nPeer 1", "Committing\nPeer 2"]
    for x, lab in zip(xs, labels):
        lifeline(ax, x, lab)
    for y in [4.55, 3.15]:
        line(ax, (0.15, y), (9.05, y), "#2458FF", 0.9, "--")
    phase_box = {"facecolor": "white", "edgecolor": "none", "alpha": 0.92, "pad": 0.5}
    ax.text(8.9, 7.35, "Execution\nPhase", rotation=-90, fontsize=9.2, va="center", ha="center", bbox=phase_box)
    ax.text(8.9, 3.85, "Ordering\nPhase", rotation=-90, fontsize=9.2, va="center", ha="center", bbox=phase_box)
    ax.text(8.9, 2.10, "Validation and\nCommit Phase", rotation=-90, fontsize=8.7, va="center", ha="center", bbox=phase_box)

    activation(ax, 0.5, 8.4, 0.4)
    activation(ax, 1.8, 5.15, 3.45)
    activation(ax, 3.3, 7.45, 0.35)
    activation(ax, 4.65, 6.85, 0.35)
    activation(ax, 3.3, 6.25, 0.45)
    activation(ax, 3.7, 5.65, 0.45)
    activation(ax, 5.8, 3.15, 1.0)
    activation(ax, 7.0, 1.95, 1.2)
    activation(ax, 8.1, 2.7, 0.45)

    msg(ax, 0.55, 8.55, 1.75, 8.55, "1. Transaction\nproposal", BLUE2)
    msg(ax, 1.8, 8.15, 3.25, 8.15, "2. Proposal", BLUE2)
    msg(ax, 1.8, 7.55, 4.6, 7.55, "3. Proposal", BLUE2)
    ax.text(3.52, 6.75, "4. Chaincode execution\nRead-write set", fontsize=6.0, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 0.3})
    ax.text(3.9, 6.13, "5. Chaincode execution\nRead-write set", fontsize=6.0, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 0.3})
    msg(ax, 3.25, 5.55, 1.85, 5.55, "6. Endorsement response", BLUE2)
    msg(ax, 4.6, 5.18, 1.85, 5.18, "7. Endorsement response", BLUE2)
    ax.text(2.05, 4.33, "8. Collect endorsements\nSigned transaction", fontsize=5.8, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.88, "pad": 0.25})
    msg(ax, 1.8, 4.9, 5.75, 4.9, "9. Submit transaction", BLUE2, fontsize=5.8)
    ax.text(5.92, 4.05, "10. Consensus\nBlock generation", fontsize=5.7, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 0.25})
    msg(ax, 5.85, 3.75, 8.02, 3.75, "11. Block broadcast", BLUE2)
    msg(ax, 5.85, 3.35, 8.05, 3.35, "12. Block broadcast", BLUE2)
    rounded_box(ax, (4.6, 2.05), 3.75, 0.75, "", ec=RED, fc="white", lw=0.9, r=0.05)
    ax.text(
        5.55,
        2.42,
        "13. VSCC validation\nMVCC validation\nCommit",
        ha="center",
        va="center",
        fontsize=5.6,
        color=RED,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.94, "pad": 0.35},
        zorder=9,
    )
    ax.text(
        7.15,
        2.42,
        "14. VSCC validation\nMVCC validation\nCommit",
        ha="center",
        va="center",
        fontsize=5.6,
        color=RED,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.94, "pad": 0.35},
        zorder=9,
    )
    msg(ax, 5.8, 1.78, 1.85, 1.78, "15. Commit event", BLUE2)
    msg(ax, 7.0, 1.55, 0.55, 1.55, "16. Commit event", BLUE2)
    ax.add_patch(Rectangle((4.55, 1.05), 2.4, 8.1, fc="#F9D8D4", ec="none", alpha=0.25, zorder=0))
    ax.text(
        6.95,
        3.02,
        "Conflicts are detected after\nendorsement and ordering",
        color=RED,
        fontsize=6.3,
        fontstyle="italic",
        ha="center",
        va="center",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.92, "pad": 0.35},
        zorder=9,
    )
    ax.text(4.85, 0.72, "Endorsement, ordering, broadcast,\nand validation resources have\nalready been consumed", color=RED, fontsize=7, fontstyle="italic", ha="left")

    # Right panel.
    xs2 = [10.0, 11.45, 13.1, 14.25, 15.4, 16.6, 17.85, 18.95]
    labels2 = ["Client", "CAPS\nScheduler", "Fabric\nGateway", "Endorsing\nPeer 1", "Endorsing\nPeer 2", "Ordering\nService", "Committing\nPeer 1", "Committing\nPeer 2"]
    for x, lab in zip(xs2, labels2):
        lifeline(ax, x, lab)
    for y in [4.55, 3.15]:
        line(ax, (9.75, y), (20.15, y), "#2458FF", 0.9, "--")
    ax.text(20.02, 7.0, "Execution\nPhase", rotation=-90, fontsize=9.2, va="center", ha="center", bbox=phase_box)
    ax.text(20.02, 3.85, "Ordering\nPhase", rotation=-90, fontsize=9.2, va="center", ha="center", bbox=phase_box)
    ax.text(20.02, 2.05, "Validation and\nCommit Phase", rotation=-90, fontsize=8.7, va="center", ha="center", bbox=phase_box)

    activation(ax, 10.0, 8.5, 0.25)
    activation(ax, 11.45, 8.2, 0.55)
    activation(ax, 13.1, 2.1, 4.05)
    activation(ax, 14.25, 7.3, 0.3)
    activation(ax, 15.4, 6.75, 0.35)
    activation(ax, 16.6, 3.35, 0.8)
    activation(ax, 17.85, 2.2, 1.05)
    activation(ax, 18.95, 2.5, 0.45)

    msg(ax, 10.05, 8.6, 11.38, 8.6, "1. Transaction\nrequest", GREEN)
    rounded_box(ax, (10.15, 6.05), 1.08, 1.8, "ACG: Access-set\nConflict Guard\n\nPAC: Pressure-\nadaptive Admission\nControl\n\nDBS: Dependency-\naware Batch\nScheduling", ec=BLUE, lw=0.8, r=0.06, fontsize=5.2, color=BLUE)
    ax.text(11.55, 8.25, "2. Access-set declaration\nDerive R(T), W(T)", fontsize=5.7, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.86, "pad": 0.3})
    ax.text(11.55, 7.55, "3. Conflict check", fontsize=5.7, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.86, "pad": 0.3})
    ax.text(11.55, 6.85, "4. Pressure evaluation $P_t$", fontsize=5.7, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.86, "pad": 0.3})
    ax.text(11.55, 6.15, "5. Select compatible batch", fontsize=5.7, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.86, "pad": 0.3})
    rounded_box(ax, (9.45, 3.8), 2.6, 2.1, "", ec=BLACK, lw=0.8, r=0.05)
    line(ax, (9.45, 5.2), (12.05, 5.2), BLACK, 0.7, "--")
    line(ax, (9.45, 4.5), (12.05, 4.5), BLACK, 0.7, "--")
    ax.text(9.55, 5.55, "[Compatible and\nadmitted]", color=GREEN, fontsize=6)
    ax.text(9.55, 4.82, "[Overloaded or\nhotspot backlog]", color=RED, fontsize=6)
    ax.text(9.55, 4.12, "[Queue deadline\nexceeded]", color=RED, fontsize=6)
    msg(ax, 11.45, 5.28, 13.02, 5.28, "6. Forward admitted\ntransaction", GREEN, fontsize=5.6)
    msg(ax, 11.45, 4.75, 10.55, 4.75, "Admission\nRejection", RED, ls="--", fontsize=5.5)
    msg(ax, 11.45, 4.05, 10.55, 4.05, "Queue\nTimeout", RED, ls="--", fontsize=5.5)
    ax.text(12.55, 5.78, "Compatible and\nadmitted requests\nenter Fabric", color=GREEN, fontsize=5.9, fontstyle="italic", ha="center", bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 0.35})

    msg(ax, 13.1, 7.55, 14.2, 7.55, "7. Proposal", GREEN)
    msg(ax, 13.1, 7.05, 15.35, 7.05, "8. Proposal", GREEN)
    ax.text(15.5, 6.62, "9. Chaincode execution\nRead-write set", fontsize=5.7, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.84, "pad": 0.3})
    ax.text(15.5, 5.95, "10. Chaincode execution\nRead-write set", fontsize=5.7, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.84, "pad": 0.3})
    msg(ax, 15.35, 5.55, 13.15, 5.55, "11. Endorsement response", GREEN)
    msg(ax, 14.2, 5.18, 13.15, 5.18, "12. Endorsement response", GREEN)
    ax.text(13.25, 4.82, "13. Collect endorsements\nSigned transaction", fontsize=5.7, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.84, "pad": 0.3})
    msg(ax, 13.1, 4.55, 16.55, 4.55, "14. Submit transaction", GREEN)
    ax.text(16.58, 3.95, "15. Consensus\nBlock generation", fontsize=5.6, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 0.25})
    msg(ax, 16.65, 3.55, 18.9, 3.55, "16. Block broadcast", GREEN)
    msg(ax, 16.65, 3.25, 18.9, 3.25, "17. Block broadcast", GREEN)
    rounded_box(ax, (15.55, 2.1), 2.75, 0.7, "", ec=GREEN, fc="white", lw=0.9, r=0.05)
    ax.text(
        16.25,
        2.43,
        "18. VSCC validation\nMVCC validation\nCommit",
        ha="center",
        va="center",
        fontsize=5.1,
        color=GREEN,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.94, "pad": 0.3},
        zorder=9,
    )
    ax.text(
        17.45,
        2.43,
        "19. VSCC validation\nMVCC validation\nCommit",
        ha="center",
        va="center",
        fontsize=5.1,
        color=GREEN,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.94, "pad": 0.3},
        zorder=9,
    )
    msg(ax, 17.85, 1.75, 13.15, 1.75, "20. Commit event", GREEN)
    msg(ax, 11.45, 1.4, 10.05, 1.4, "22. Commit event", GREEN)
    msg(ax, 13.1, 1.55, 11.45, 1.55, "21. Commit event", GREEN)
    ax.text(18.62, 1.72, "No CAPS-admitted\nMVCC conflict\nunder conservative\nprediction", color=GREEN, fontsize=5.8, fontstyle="italic", ha="left", bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.88, "pad": 0.35})

    save(fig, "fig1_eov_flow_favorite_vector")


def figure_pressure():
    fig = plt.figure(figsize=(14, 7.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.45, 1.0], wspace=0.08)
    ax = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    q = np.linspace(0, 500, 501)
    queue_pressure = q / (0.3 * 500)
    delay_term = np.clip((q - 70) / 210, 0, None)
    hotspot = np.where(q < 128, 0, 1.18)
    combined = np.maximum.reduce([queue_pressure, delay_term, hotspot])
    ax.axhspan(0, 1, color="#EAF6EA", zorder=0)
    ax.axhspan(1, 3.5, color="#F9E6D6", zorder=0)
    ax.plot(q, queue_pressure, color="#0B5FA5", lw=2.1, label=r"Queue pressure: $Q_t/(0.3Q_{max})$")
    ax.plot(q, delay_term, color="#7A5195", lw=1.8, ls="-.", label=r"Recent queueing delay: $W_t/\theta_w$")
    ax.plot(q, hotspot, color="#FF6A00", lw=2.1, label="Hotspot gating term")
    ax.plot(q, combined, color="#0B7F25", lw=2.1, label=r"Combined pressure $P_t=\max(\cdots)$")
    ax.axhline(1, color="red", lw=1.8, ls="--", label=r"Mode-switch threshold $P_t=1$")
    ax.axvline(128, color=BLACK, lw=1.1, ls=":")
    ax.axvline(150, color=BLACK, lw=1.1, ls=":")
    ax.text(125, 0.08, r"$Q_t=128$", ha="right", va="bottom", fontsize=9)
    ax.text(153, 0.08, r"$Q_t=150$", ha="left", va="bottom", fontsize=9)
    ax.text(360, 1.45, r"$P_t \geq 1$", color=ORANGE, fontsize=15)
    ax.text(360, 0.48, r"$P_t < 1$", color=GREEN, fontsize=15)
    ax.set_xlim(0, 500)
    ax.set_ylim(0, 3.5)
    ax.set_xticks([0, 128, 150, 500])
    ax.set_yticks([0, 0.5, 1.0, 1.12, 1.5, 2.0, 2.5, 3.0, 3.5])
    ax.set_xlabel(r"Queue length $Q_t$", fontsize=15)
    ax.set_ylabel("Normalized pressure", fontsize=15)
    ax.tick_params(labelsize=13)
    ax.legend(loc="upper left", frameon=True, fancybox=False, edgecolor="none", fontsize=12)
    ax.set_title("(a) Pressure function", fontsize=18, pad=14)

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis("off")
    ax2.set_title("(b) Low-latency admission mode switching", fontsize=18, pad=14)
    rounded_box(ax2, (0.18, 0.78), 0.64, 0.14, "Normal Mode\nQueue limit $Q_{max}=500$", ec="#174F86", lw=2.0, r=0.04, fontsize=15, weight="bold")
    rounded_box(ax2, (0.18, 0.43), 0.64, 0.14, "Pressure-control Mode\nQueue limit $Q_{pa}=128$", ec="#16822E", lw=2.0, r=0.04, fontsize=15, weight="bold")
    rounded_box(ax2, (0.18, 0.07), 0.64, 0.14, "Explicit Backpressure\nHotspot admission rejection /\nQueue timeout", ec="#F03B20", lw=2.0, r=0.04, fontsize=14, weight="bold")
    arrow(ax2, (0.5, 0.78), (0.5, 0.57), BLACK, lw=1.4, ms=14)
    ax2.text(0.54, 0.66, r"$P_t \geq 1$", fontsize=14)
    arrow(ax2, (0.5, 0.43), (0.5, 0.21), BLACK, lw=1.4, ms=14)
    ax2.text(0.55, 0.31, "Queue full or\npersistent hotspot backlog", fontsize=12)
    line(ax2, (0.82, 0.50), (0.90, 0.50), GREEN, 1.4, "--")
    ax2.text(0.92, 0.57, "Low-latency\nadmission\nbecomes\nstricter after\nmode switching.", fontsize=12, va="top")

    save(fig, "fig3_pressure_favorite_vector")


def main():
    ensure_out()
    figure_architecture()
    figure_eov_flow()
    figure_pressure()
    print(f"Wrote vector figures to {OUT}")


if __name__ == "__main__":
    main()
