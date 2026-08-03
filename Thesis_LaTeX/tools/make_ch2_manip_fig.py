#!/usr/bin/env python3
"""Figure 2.4 for Chapter 2: Yoshikawa's measure for a planar two-link arm.

Plots w = l1 * l2 * |sin(theta2)| against the elbow angle, which is the closed form
Yoshikawa (1985) gives for the simplest multijoint mechanism. The point of the figure
is the shape, not the numbers: w collapses to zero at the fully extended and fully
folded postures and peaks at a right angle, so a straightened arm is a weak arm.

Colour convention (revised 2026-08-04, superseding the earlier "black line art only" rule --
see Thesis_LaTeX/figures/README.md): the curve carries the book's cPPO blue, the two singular
postures are marked in the book's baseline red, and the best posture in the cPPO green. That is
the same semantic mapping the Chapter 4 figures use, where red marks the unsafe condition.

Output: Thesis_LaTeX/figures/lit_twolink_w.pdf

Run from anywhere:  python3 Thesis_LaTeX/tools/make_ch2_manip_fig.py
"""

from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

# Book-wide palette, identical to Comparison_test/results/scripts/make_final_results_figs.py.
RED, BLUE, GREEN, INK = "#D11A1A", "#1257A8", "#17803D", "#1A1A1A"

_FONTDIR = Path(__file__).resolve().parents[1] / "fonts"
for _f in sorted(_FONTDIR.glob("*.ttf")):
    try:
        fm.fontManager.addfont(str(_f))
    except Exception:
        pass
_HAVE_TNR = "Times New Roman" in {f.name for f in fm.fontManager.ttflist}
print("Font:", "Times New Roman" if _HAVE_TNR else "Liberation Serif (TNR not in fonts/)")

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": (["Times New Roman"] if _HAVE_TNR else [])
                  + ["Liberation Serif", "Nimbus Roman", "DejaVu Serif"],
    "text.color": INK,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
})

OUT = Path(__file__).resolve().parents[1] / "figures" / "lit_twolink_w.pdf"

L1 = L2 = 0.425          # equal links, the posture Yoshikawa notes for a human arm
th2 = np.linspace(-180.0, 180.0, 1441)
w = L1 * L2 * np.abs(np.sin(np.radians(th2)))

fig, ax = plt.subplots(figsize=(5.8, 2.7))
ax.plot(th2, w, color=BLUE, linewidth=1.9, zorder=2)

# Mark the two failure postures (red, the book's unsafe colour) and the best one (green).
for x in (-180.0, 0.0, 180.0):
    ax.plot([x], [0.0], marker="o", markersize=5.2, color=RED,
            markerfacecolor="white", markeredgewidth=1.6, zorder=3)
for x in (-90.0, 90.0):
    ax.plot([x], [L1 * L2], marker="o", markersize=5.2, color=GREEN, zorder=3)

ax.annotate("fully folded", xy=(0.0, 0.0), xytext=(0.0, 0.082),
            ha="center", fontsize=9.6, color=INK,
            arrowprops=dict(arrowstyle="-", linewidth=0.8, color=INK))
ax.annotate("fully extended", xy=(180.0, 0.0), xytext=(163.0, 0.125),
            ha="center", fontsize=9.6, color=INK,
            arrowprops=dict(arrowstyle="-", linewidth=0.8, color=INK))
ax.annotate(r"best posture, $\theta_2=\pm 90^\circ$", xy=(90.0, L1 * L2),
            xytext=(90.0, L1 * L2 + 0.028), ha="center", fontsize=9.6, color=INK,
            arrowprops=dict(arrowstyle="-", linewidth=0.8, color=INK))

ax.set_xlim(-190, 190)
ax.set_ylim(0, 0.245)
ax.set_xticks([-180, -90, 0, 90, 180])
ax.set_xticklabels([r"$-180^\circ$", r"$-90^\circ$", r"$0^\circ$",
                    r"$90^\circ$", r"$180^\circ$"])
ax.set_xlabel(r"elbow angle $\theta_2$", fontsize=11.0)
ax.set_ylabel(r"manipulability $w$", fontsize=11.0)
ax.tick_params(labelsize=10.0)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_linewidth(1.0)

fig.tight_layout(pad=0.3)
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, format="pdf", bbox_inches="tight", pad_inches=0.02)
print(f"wrote {OUT}")
