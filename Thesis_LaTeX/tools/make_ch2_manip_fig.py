#!/usr/bin/env python3
"""Figure 2.4 for Chapter 2: Yoshikawa's measure for a planar two-link arm.

Plots w = l1 * l2 * |sin(theta2)| against the elbow angle, which is the closed form
Yoshikawa (1985) gives for the simplest multijoint mechanism. The point of the figure
is the shape, not the numbers: w collapses to zero at the fully extended and fully
folded postures and peaks at a right angle, so a straightened arm is a weak arm.

Black line art only, no colour and no fill, to match the chapter's formatting rule.
Output: Thesis_LaTeX/figures/lit_twolink_w.pdf

Run from anywhere:  python3 Thesis_LaTeX/tools/make_ch2_manip_fig.py
"""

from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Nimbus Roman No9 L", "Liberation Serif", "DejaVu Serif"],
    "text.color": "black",
    "axes.edgecolor": "black",
    "axes.labelcolor": "black",
    "xtick.color": "black",
    "ytick.color": "black",
})

OUT = Path(__file__).resolve().parents[1] / "figures" / "lit_twolink_w.pdf"

L1 = L2 = 0.425          # equal links, the posture Yoshikawa notes for a human arm
th2 = np.linspace(-180.0, 180.0, 1441)
w = L1 * L2 * np.abs(np.sin(np.radians(th2)))

fig, ax = plt.subplots(figsize=(5.4, 2.5))
ax.plot(th2, w, color="black", linewidth=1.3)

# Mark the two failure postures and the best one.
for x in (-180.0, 0.0, 180.0):
    ax.plot([x], [0.0], marker="o", markersize=3.6, color="black",
            markerfacecolor="white", markeredgewidth=0.9, zorder=3)
for x in (-90.0, 90.0):
    ax.plot([x], [L1 * L2], marker="o", markersize=3.6, color="black", zorder=3)

ax.annotate("fully folded", xy=(0.0, 0.0), xytext=(0.0, 0.082),
            ha="center", fontsize=8.4,
            arrowprops=dict(arrowstyle="-", linewidth=0.7, color="black"))
ax.annotate("fully extended", xy=(180.0, 0.0), xytext=(145.0, 0.088),
            ha="center", fontsize=8.4,
            arrowprops=dict(arrowstyle="-", linewidth=0.7, color="black"))
ax.annotate(r"best posture, $\theta_2=\pm 90^\circ$", xy=(90.0, L1 * L2),
            xytext=(90.0, L1 * L2 + 0.028), ha="center", fontsize=8.4,
            arrowprops=dict(arrowstyle="-", linewidth=0.7, color="black"))

ax.set_xlim(-190, 190)
ax.set_ylim(0, 0.245)
ax.set_xticks([-180, -90, 0, 90, 180])
ax.set_xticklabels([r"$-180^\circ$", r"$-90^\circ$", r"$0^\circ$",
                    r"$90^\circ$", r"$180^\circ$"])
ax.set_xlabel(r"elbow angle $\theta_2$", fontsize=9.5)
ax.set_ylabel(r"manipulability $w$", fontsize=9.5)
ax.tick_params(labelsize=8.6)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_linewidth(0.8)

fig.tight_layout(pad=0.3)
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, format="pdf", bbox_inches="tight", pad_inches=0.02)
print(f"wrote {OUT}")
