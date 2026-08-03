#!/usr/bin/env python3
"""
Per-seed episodic cost figure for the Results chapter (Table 4.5 as a graphic).

Design decision, 2026-08-02: this is a PAIRED (dumbbell) plot, not a sorted-band plot.
The band plot makes the variance collapse look stronger, but it hides the direction of
each seed's change. Section 4.6 states plainly that the band is entered from BOTH
directions, so the figure must show that too or it would overstate the result.

Provenance
  Source    : Comparison_test/results/tb_csv/2026-08-01_*_{arm}_s{seed}__Loss__mean_episode_cost.csv
  Statistic : tail mean over the final 10 % of 1500 logged iterations (last 150 points)
  Exclusion : 2026-07-30 cppo runs are superseded pre-audit runs and are NEVER globbed here.
  Verified  : all 20 values reproduce Table 4.5 / MATRIX_V2_PARTIAL_3ARM.md exactly.

Output: Thesis_LaTeX/figures/per_seed_cost.pdf (vector, used by the book) and .png
"""

import csv, glob, os, statistics, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(RESULTS))
OUTDIR = os.path.join(REPO, "Thesis_LaTeX", "figures")

SEEDS = [1, 2, 3, 4, 5, 50, 51, 52, 53, 54]
BUDGET = 25.0

# Cross-check values, from MATRIX_V2_PARTIAL_3ARM.md (the batch's source of truth).
PAPER = {
    "ctrl": dict(zip(SEEDS, [102.1, 7.7, 162.3, 30.0, 19.1, 8.6, 1.8, 106.9, 18.8, 7.9])),
    "cppo": dict(zip(SEEDS, [18.0, 16.6, 11.9, 19.7, 24.1, 23.9, 17.0, 9.5, 23.5, 12.0])),
}


def tail_mean(arm, seed, frac=0.10):
    pat = os.path.join(RESULTS, "tb_csv",
                       f"2026-08-01_*_{arm}_s{seed}__Loss__mean_episode_cost.csv")
    hits = sorted(glob.glob(pat))
    if not hits:
        raise SystemExit(f"missing run: {arm} seed {seed}")
    vals = []
    with open(hits[-1]) as f:
        for row in csv.DictReader(f):
            key = [c for c in row if c.lower() in ("value", "val")]
            vals.append(float(row[key[0]]) if key else float(list(row.values())[-1]))
    n = max(1, int(len(vals) * frac))
    return statistics.fmean(vals[-n:])


def main():
    ctrl = {s: tail_mean("ctrl", s) for s in SEEDS}
    cppo = {s: tail_mean("cppo", s) for s in SEEDS}

    # Refuse to emit a figure that disagrees with the reported table.
    for arm, got in (("ctrl", ctrl), ("cppo", cppo)):
        for s in SEEDS:
            if abs(got[s] - PAPER[arm][s]) > 0.15:
                raise SystemExit(
                    f"MISMATCH {arm} s{s}: computed {got[s]:.2f} vs table {PAPER[arm][s]:.2f}")
    print("all 20 values match Table 4.5")

    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"],
        "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 9,
        "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "legend.fontsize": 8,
    })

    DOWN, UP, GREY = "#1F4E79", "#C1662F", "#8A8A8A"
    fig, ax = plt.subplots(figsize=(6.1, 3.5))
    x = range(len(SEEDS))

    ax.axhline(BUDGET, color=GREY, lw=1.0, ls="--", zorder=1)
    ax.text(len(SEEDS) - 0.42, BUDGET * 1.06, f"budget = {BUDGET:.0f}",
            fontsize=7.5, color=GREY, ha="right", va="bottom")

    n_up = 0
    for i, s in enumerate(SEEDS):
        a, b = ctrl[s], cppo[s]
        rose = b > a
        n_up += rose
        ax.plot([i, i], [a, b], color=(UP if rose else DOWN), lw=1.3, alpha=0.55, zorder=2)
        ax.plot(i, a, "o", ms=5.2, mfc="white", mec=GREY, mew=1.3, zorder=3)
        ax.plot(i, b, "o", ms=5.2, color=(UP if rose else DOWN), zorder=4)

    ax.set_yscale("log")
    ax.set_xticks(list(x))
    ax.set_xticklabels(SEEDS)
    ax.set_xlim(-0.6, len(SEEDS) - 0.4)
    ax.set_xlabel("Training seed")
    ax.set_ylabel("Episodic safety cost (tail mean)")
    ax.grid(axis="y", ls=":", lw=0.5, color="#CCCCCC", zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    handles = [
        Line2D([], [], marker="o", ls="", ms=5.2, mfc="white", mec=GREY, mew=1.3,
               label="ctrl (unconstrained)"),
        Line2D([], [], marker="o", ls="", ms=5.2, color=DOWN, label="cPPO, cost reduced"),
        Line2D([], [], marker="o", ls="", ms=5.2, color=UP, label="cPPO, cost increased"),
    ]
    ax.legend(handles=handles, loc="upper right", frameon=False, ncol=1,
              handletextpad=0.4, borderaxespad=0.2)

    fig.tight_layout(pad=0.4)
    os.makedirs(OUTDIR, exist_ok=True)
    for ext in ("pdf", "png"):
        out = os.path.join(OUTDIR, f"per_seed_cost.{ext}")
        fig.savefig(out, dpi=300, bbox_inches="tight")
        print("wrote", out)
    print(f"seeds where cPPO ended higher: {n_up} of {len(SEEDS)}")


if __name__ == "__main__":
    main()
