#!/usr/bin/env python3
"""SUPERSEDED 2026-08-04 -- DO NOT RUN. Kept as a record only.

Running this script would overwrite Thesis_LaTeX/figures/per_seed_cost.pdf and lambda_traj.pdf
with the black-line-art versions below, reverting the colour convention Touhid set on
2026-08-04 and breaking the visual consistency with the other nine Chapter 4 figures.

Both figures are now produced, along with nine others, by
    Comparison_test/results/scripts/make_final_results_figs.py
See Thesis_LaTeX/figures/README.md for the palette and the two load-bearing layout constraints.

--- original header follows ---

The two Chapter 4 figures, both drawn from Comparison_test/final_results/ only.

Black line art, no colour and no fill, matching the book-wide rule set 2026-08-03 (WITHDRAWN).
Arms are distinguished by marker and line style, never by colour.

Outputs
  Thesis_LaTeX/figures/per_seed_cost.pdf   per-seed episodic cost, three arms, paired
  Thesis_LaTeX/figures/lambda_traj.pdf     Lagrange multiplier trajectories

Design decision carried over from the 2026-08-02 version and still binding: the cost
figure is PAIRED, not a sorted band. A band makes the variance collapse look stronger
but hides which direction each seed moved, and Section 4.6 has to state that one seed
moves the wrong way. The figure must show that or it overstates the result.

Usage:  python3 Comparison_test/results/scripts/make_ch4_figs.py
"""

from __future__ import annotations

import csv
import glob
import statistics as st
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve()
FINAL = HERE.parents[2] / "final_results"
FIGDIR = HERE.parents[3] / "Thesis_LaTeX" / "figures"

SEEDS = [1, 3, 4, 52, 54]
ARMS = [("PPO_baseline", "PPO (baseline)"), ("CPPO_25", r"cPPO, $d=25$"),
        ("CPPO15", r"cPPO, $d=15$")]
TAIL = 0.10

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Nimbus Roman No9 L", "Liberation Serif", "DejaVu Serif"],
    "text.color": "black", "axes.edgecolor": "black", "axes.labelcolor": "black",
    "xtick.color": "black", "ytick.color": "black",
})


def series(arm: str, seed: int, metric: str) -> list[float]:
    hits = sorted(glob.glob(str(FINAL / "training" / arm / f"seed_{seed}" / f"*__{metric}.csv")))
    hits = [h for h in hits if not h.endswith(f"{metric}__time.csv")]
    if not hits:
        return []
    with open(hits[0]) as fh:
        return [float(r["value"]) for r in csv.DictReader(fh)]


def tail_mean(xs: list[float]) -> float:
    n = max(1, int(round(len(xs) * TAIL)))
    return st.fmean(xs[-n:])


# ------------------------------------------------------------------ figure 1

def fig_per_seed_cost() -> None:
    cost = {a: [tail_mean(series(a, s, "Loss__mean_episode_cost")) for s in SEEDS]
            for a, _ in ARMS}

    fig, ax = plt.subplots(figsize=(6.1, 3.1))
    x = list(range(len(SEEDS)))
    styles = [dict(marker="o", mfc="white", mec="black", ms=7, mew=1.2),
              dict(marker="o", mfc="black", mec="black", ms=6.5),
              dict(marker="s", mfc="black", mec="black", ms=6)]

    for i in x:                                    # join the three arms for each seed
        ys = [cost[a][i] for a, _ in ARMS]
        ax.plot([i] * 3, ys, color="black", linewidth=0.8, zorder=1)

    for (arm, label), stl in zip(ARMS, styles):
        ax.plot(x, cost[arm], linestyle="none", color="black", label=label, zorder=3, **stl)

    for d, ls in ((25, (0, (5, 3))), (15, (0, (1.5, 2.5)))):
        ax.axhline(d, color="black", linewidth=0.8, linestyle=ls, zorder=0)
        ax.text(len(SEEDS) - 0.45, d * 1.06, f"$d={d}$", fontsize=8.2, va="bottom", ha="right")

    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([f"seed {s}" for s in SEEDS], fontsize=9)
    ax.set_ylabel("episodic safety cost", fontsize=9.5)
    ax.tick_params(labelsize=8.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=8.4, frameon=False, loc="upper right", ncol=3,
              handletextpad=0.4, columnspacing=1.2, bbox_to_anchor=(1.0, 1.16))
    fig.tight_layout(pad=0.4)
    out = FIGDIR / "per_seed_cost.pdf"
    fig.savefig(out, format="pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(out.with_suffix(".png"), dpi=200, bbox_inches="tight", pad_inches=0.02)
    print(f"wrote {out}")
    for a, lbl in ARMS:
        print(f"   {lbl:<16}" + "  ".join(f"s{s}={v:.2f}" for s, v in zip(SEEDS, cost[a])))


# ------------------------------------------------------------------ figure 2

def fig_lambda() -> None:
    panels = [("CPPO_25", r"cPPO, $d=25$"), ("CPPO15", r"cPPO, $d=15$")]
    dashes = [(0, ()), (0, (5, 2)), (0, (1.5, 1.5)), (0, (6, 2, 1.5, 2)), (0, (3, 1.5, 1, 1.5))]

    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.6), sharey=True)
    for ax, (arm, title) in zip(axes, panels):
        for seed, dash in zip(SEEDS, dashes):
            lam = series(arm, seed, "Loss__cost_lambda")
            ax.plot(range(len(lam)), lam, color="black", linewidth=1.0,
                    linestyle=dash, label=f"seed {seed}")
        ax.set_xlim(0, 300)
        ax.set_title(title, fontsize=9.5)
        ax.set_xlabel("training iteration", fontsize=9.2)
        ax.tick_params(labelsize=8.4)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].set_ylabel(r"Lagrange multiplier $\lambda$", fontsize=9.2)
    axes[1].legend(fontsize=7.8, frameon=False, loc="upper right", handlelength=2.6)
    fig.tight_layout(pad=0.4)
    out = FIGDIR / "lambda_traj.pdf"
    fig.savefig(out, format="pdf", bbox_inches="tight", pad_inches=0.02)
    print(f"wrote {out}")
    for arm, lbl in panels:
        for seed in SEEDS:
            lam = series(arm, seed, "Loss__cost_lambda")
            print(f"   {lbl:<14} seed {seed:<3} peak={max(lam):6.2f} at iter {lam.index(max(lam)):>4}"
                  f"  final={lam[-1]:.4f}  iters>0.01={sum(1 for v in lam if v > 0.01)}")


if __name__ == "__main__":
    import sys
    print(__doc__.split("--- original header follows ---")[0])
    if "--i-really-mean-it" not in sys.argv:
        sys.exit("Refusing to run: this script is superseded and would revert the figure "
                 "colour convention. Use make_final_results_figs.py instead.")
    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig_per_seed_cost()
    fig_lambda()
