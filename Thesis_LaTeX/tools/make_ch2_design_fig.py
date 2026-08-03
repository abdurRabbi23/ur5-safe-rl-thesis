#!/usr/bin/env python3
"""Figure 2.5 for Chapter 2: the three trained arms and the difference they decompose.

Colour convention (revised 2026-08-04, superseding the earlier "black line art only" rule --
see Thesis_LaTeX/figures/README.md). Each arm's box is drawn in that arm's book-wide colour:
ctrl red, cppo blue, cppo15 green, identical to the Chapter 4 plots. This is the point of
recolouring rather than decoration -- a reader who meets the three arms here carries the same
colour key into every results figure.

Output: Thesis_LaTeX/figures/lit_arms.pdf (vector, so it stays sharp at any size).

The arm names and settings here MUST match Chapter 3, Table 3.11 (sec:m-arms):
    ctrl    cost_limit 25, lambda_max 0   -> reported as "PPO (baseline)"
    cppo    cost_limit 25, lambda_max 100
    cppo15  cost_limit 15, lambda_max 100
A plain PPO arm was also trained on the same seeds; its stored weights proved
byte-identical to ctrl's, which is why ctrl stands in for it and why the
implementation term is zero by verification rather than by assumption.

Run from anywhere:  python3 Thesis_LaTeX/tools/make_ch2_design_fig.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyArrowPatch, Rectangle

# Book-wide palette, identical to Comparison_test/results/scripts/make_final_results_figs.py.
RED, BLUE, GREEN, INK = "#D11A1A", "#1257A8", "#17803D", "#1A1A1A"
ARM_COLOR = [RED, BLUE, GREEN]          # ctrl, cppo, cppo15 -- order matches `arms` below

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
})

OUT = Path(__file__).resolve().parents[1] / "figures" / "lit_arms.pdf"

fig, ax = plt.subplots(figsize=(6.3, 3.6))
ax.set_xlim(0, 100)
ax.set_ylim(-2, 61)
ax.axis("off")

BOX_W, BOX_H, BOX_Y = 25.0, 17.0, 26.0
xs = [1.0, 37.5, 74.0]

arms = [
    (r"$\bf{ctrl}$", ["reported as PPO (baseline)", "cost critic present",
                      r"$\lambda$ ceiling $=0$"]),
    (r"$\bf{cppo}$", ["cost critic present", r"$\lambda$ free", r"budget $d=25$"]),
    (r"$\bf{cppo15}$", ["cost critic present", r"$\lambda$ free", r"budget $d=15$"]),
]

for x, (title, lines), col in zip(xs, arms, ARM_COLOR):
    ax.add_patch(Rectangle((x, BOX_Y), BOX_W, BOX_H, fill=False,
                           edgecolor=col, linewidth=1.8))
    ax.text(x + BOX_W / 2, BOX_Y + BOX_H - 3.4, title, ha="center", va="center",
            fontsize=11.5, color=col)
    for i, ln in enumerate(lines):
        ax.text(x + BOX_W / 2, BOX_Y + BOX_H - 7.8 - 3.4 * i, ln,
                ha="center", va="center", fontsize=9.0, color=INK)

# The separately trained plain-PPO arm, sitting above ctrl. Drawn in ctrl's red because the
# whole point of the box is that the two are the same policy.
PX, PY, PW, PH = xs[0], BOX_Y + BOX_H + 8.0, BOX_W, 8.0
ax.add_patch(Rectangle((PX, PY), PW, PH, fill=False, edgecolor=ARM_COLOR[0],
                       linewidth=1.4, linestyle=(0, (4, 2))))
ax.text(PX + PW / 2, PY + PH / 2 + 1.6, r"$\bf{ppo}$ (plain)", ha="center",
        va="center", fontsize=10.4, color=ARM_COLOR[0])
ax.text(PX + PW / 2, PY + PH / 2 - 2.4, "trained, not reported separately",
        ha="center", va="center", fontsize=8.6, color=INK)

# Double line marking the verified identity between ppo and ctrl.
for dx in (-0.55, 0.55):
    ax.plot([PX + PW / 2 + dx, PX + PW / 2 + dx], [PY, BOX_Y + BOX_H],
            color=ARM_COLOR[0], linewidth=1.1)
ax.text(PX + PW + 2.5, PY + PH + 0.5,
        "stored weights byte-identical,\n"
        "so the implementation term is\n"
        r"$0$ by verification, not assumption",
        ha="left", va="top", fontsize=8.4, linespacing=1.3)

# What changes between adjacent arms.
for xa, xb, label in [(xs[0] + BOX_W, xs[1], "activate\nthe budget"),
                      (xs[1] + BOX_W, xs[2], "tighten\nthe budget")]:
    ax.add_patch(FancyArrowPatch((xa + 0.6, BOX_Y + BOX_H / 2),
                                 (xb - 0.6, BOX_Y + BOX_H / 2),
                                 arrowstyle="-|>", mutation_scale=11,
                                 linewidth=0.9, color="black"))
    ax.text((xa + xb) / 2, BOX_Y + BOX_H / 2 + 5.8, label, ha="center",
            va="center", fontsize=8.4, linespacing=1.15)


def brace(x0, x1, y, label, drop=2.0, fs=9.2):
    """A flat square brace under the span x0..x1, labelled below it."""
    ax.plot([x0, x0, x1, x1], [y, y - drop, y - drop, y],
            color="black", linewidth=0.9, solid_joinstyle="miter")
    ax.text((x0 + x1) / 2, y - drop - 2.4, label, ha="center", va="top",
            fontsize=fs, linespacing=1.2)


brace(xs[0] + 1.5, xs[1] + BOX_W - 1.5, BOX_Y - 1.5,
      "constraint term\n(the effect being claimed)")
brace(xs[1] + 1.5, xs[2] + BOX_W - 1.5, BOX_Y - 13.5,
      "budget sensitivity\n(does the effect scale with $d$?)")

ax.text(50, -1.8, "Five seeds per arm (1, 3, 4, 52, 54), so fifteen trained policies. "
                 "Every quantity is\nreported with its spread across seeds.",
        ha="center", va="bottom", fontsize=8.6, style="italic", linespacing=1.25)

fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, format="pdf", bbox_inches="tight", pad_inches=0.02)
print(f"wrote {OUT}")
