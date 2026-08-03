#!/usr/bin/env python3
"""
Chapter 4 figures, regenerated against the LOCKED final dataset (5 seeds, 3 arms: ctrl/cppo/cppo15).

Reads Comparison_test/results/final_results_summary.json (written by build_final_results_data.py
-- run that first if this file is missing or stale). Writes PDF+PNG into Thesis_LaTeX/figures/.

--------------------------------------------------------------------------------------------
DESIGN RULES (agreed with Touhid 2026-08-04) -- do not change these without asking.
--------------------------------------------------------------------------------------------
 * Colours are FIXED and mean the same thing in every figure:
       PPO (baseline)  = red    cPPO d=25 = blue    cPPO d=15 = green
   All lines solid, thick. Note for a black-and-white print run: red and green converge to
   near-identical grey, so a colour print (or a switch to distinct line styles) is required.
 * NO shaded +/- std bands on the curve figures. Curves show the across-seed MEAN only.
   The seed spread lives in its own two figures instead (fig_seed_variance, per_seed_cost),
   because a wash of three overlapping translucent bands was unreadable. The variance-collapse
   claim of Chapter 4 rests on those two figures -- do not delete them.
 * Curves are EMA-SMOOTHED (TensorBoard-style, with bias correction) purely for legibility.
   THIS MUST BE DISCLOSED IN EVERY CURVE-FIGURE CAPTION. The underlying data is untouched, and
   all numbers quoted in the text come from the unsmoothed JSON, never from these curves.
 * Text is near-black, not grey, and sized for print legibility.

FONT
   Literal Times New Roman is used if the four Monotype .ttf files are present in
   Thesis_LaTeX/fonts/ (times.ttf, timesbd.ttf, timesi.ttf, timesbi.ttf). See that folder's
   README for how to obtain them. If they are absent the script falls back to Liberation Serif
   (metrically identical to Times New Roman) and prints a clear warning. The font actually used
   is always printed, so there is never any ambiguity about what was rendered.
--------------------------------------------------------------------------------------------

Eleven figures:
  1. fig_mean_reward             training reward curve, 3 arms
  2. fig_mean_episode_cost       training episodic-cost curve, log y, budget reference lines
  3. fig_reaching_object         training reaching-object reward curve
  4. fig_lifting_object          training lifting-object reward curve
  5. fig_manipulability          training mean episode-minimum manipulability curve
  6. fig_constraints_components  cost split into singularity/joint-limit/collision (3 panels)
  7. lambda_traj                 Lagrange multiplier, per seed, one panel per constrained arm
                                  (replaces the black-line-art figure of the superseded
                                  make_ch4_figs.py; same filename, so Chapter 4 needs no edit)
  8. fig_seed_variance           NEW -- per-seed training cost, one panel per arm, all 5 runs
                                  drawn individually. This is where the variance evidence went
                                  when the +/- std bands were removed.
  9. per_seed_cost               per-seed episodic cost at evaluation, seed trajectories across arms
 10. fig_eval_task_performance   2 panels: zoomed success bars + log-scale failure-rate companion
 11. fig_eval_safety_violations  2x2 grid, one panel per safety metric, each on its own scale

Usage:
    python3 make_final_results_figs.py            # -> Thesis_LaTeX/figures/
    FIGS_OUTDIR=/tmp/scratch python3 make_final_results_figs.py   # -> elsewhere (dry run)
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.dirname(HERE)
COMPTEST = os.path.dirname(RESULTS)
REPO = os.path.dirname(COMPTEST)
FONTDIR = os.path.join(REPO, "Thesis_LaTeX", "fonts")
OUTDIR = os.environ.get("FIGS_OUTDIR", os.path.join(REPO, "Thesis_LaTeX", "figures"))

ARMS = ["ctrl", "cppo", "cppo15"]
LABEL = {"ctrl": "PPO (baseline)", "cppo": "cPPO (d = 25)", "cppo15": "cPPO (d = 15)"}
# Fixed, high-contrast. Red / blue / green as specified.
COLOR = {"ctrl": "#D11A1A", "cppo": "#1257A8", "cppo15": "#17803D"}
SEEDS = [1, 3, 4, 52, 54]
SEED_COLORS = ["#1257A8", "#D11A1A", "#17803D", "#7B3FA0", "#B07A00"]

INK = "#1A1A1A"      # near-black for all text and axis lines
GRID = "#D8D8D8"
RULE = "#4A4A4A"     # reference lines (budgets)

LW = 2.2             # main curve width
EMA_WEIGHT = 0.88    # "moderate" smoothing; disclosed in captions


# ----------------------------------------------------------------------------- font handling
def setup_font():
    """Register every .ttf in Thesis_LaTeX/fonts/ and use Times New Roman if it turns up.

    Filenames are deliberately NOT hard-coded: Windows ships the font as times.ttf / timesbd.ttf,
    while Ubuntu's ttf-mscorefonts-installer writes Times_New_Roman.ttf / Times_New_Roman_Bold.ttf.
    Registering everything present and then asking matplotlib which families it gained works for
    both, and for a file someone renamed by hand.
    """
    import glob as _glob
    ttfs = sorted(_glob.glob(os.path.join(FONTDIR, "*.ttf")) +
                  _glob.glob(os.path.join(FONTDIR, "*.TTF")))
    for path in ttfs:
        try:
            fm.fontManager.addfont(path)
        except Exception as exc:                      # a corrupt file must not kill the run
            print(f"NOTE: could not load {os.path.basename(path)}: {exc}")

    available = {f.name for f in fm.fontManager.ttflist}
    if "Times New Roman" in available:
        family = ["Times New Roman", "Liberation Serif", "Nimbus Roman", "DejaVu Serif"]
        print(f"Times New Roman registered from {len(ttfs)} file(s) in Thesis_LaTeX/fonts/.")
    else:
        family = ["Liberation Serif", "Nimbus Roman", "DejaVu Serif"]
        print("=" * 78)
        print("WARNING: Times New Roman not found in Thesis_LaTeX/fonts/.")
        print("         Falling back to Liberation Serif (metrically identical to TNR).")
        if ttfs:
            print(f"         {len(ttfs)} .ttf file(s) ARE present but none registered as")
            print("         'Times New Roman'. Files seen: "
                  + ", ".join(os.path.basename(p) for p in ttfs[:6]))
        print("         Ubuntu:  sudo apt install ttf-mscorefonts-installer, then copy")
        print("                  /usr/share/fonts/truetype/msttcorefonts/Times_New_Roman*.ttf")
        print("                  into Thesis_LaTeX/fonts/")
        print("         Windows: copy times*.ttf from C:\\Windows\\Fonts")
        print("         See Thesis_LaTeX/fonts/README.md.")
        print("=" * 78)

    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": family,
        "font.size": 13,
        "axes.labelsize": 14,
        "axes.titlesize": 14,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 12.5,
        "axes.linewidth": 1.1,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.major.width": 1.1,
        "ytick.major.width": 1.1,
        "figure.dpi": 150,
        "savefig.dpi": 600,
    })
    resolved = fm.FontProperties(family="serif").get_name()
    print(f"Font in use: {resolved}")
    return resolved


# ----------------------------------------------------------------------------- helpers
def ema(y, weight=EMA_WEIGHT):
    """TensorBoard-style exponential moving average with bias correction.

    Legibility only. Every number quoted in the thesis text comes from the raw JSON,
    never from a smoothed curve. Captions must say the curves are smoothed.
    """
    y = np.asarray(y, dtype=float)
    out = np.empty_like(y)
    last, debias = 0.0, 0.0
    for i, v in enumerate(y):
        last = last * weight + (1 - weight) * v
        debias = debias * weight + (1 - weight)
        out[i] = last / debias
    return out


def load():
    with open(os.path.join(RESULTS, "final_results_summary.json")) as f:
        return json.load(f)


def save(fig, name):
    os.makedirs(OUTDIR, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUTDIR, f"{name}.{ext}"), bbox_inches="tight")
    plt.close(fig)
    print("  wrote", name)


def style_axes(ax, grid_axis="y"):
    ax.grid(axis=grid_axis, ls=":", lw=0.7, color=GRID, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def arm_handles(arms=ARMS):
    return [Line2D([], [], color=COLOR[a], lw=LW, label=LABEL[a]) for a in arms]


# ----------------------------------------------------------------------------- curve figures
def training_curve_fig(D, metric, ylabel, name, ylog=False, ylim=None,
                       hlines=None, legend_loc="lower right", arms=ARMS):
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    for arm in arms:
        m = D["training"][arm][metric]
        steps = np.array(m["steps"])
        ax.plot(steps, ema(m["mean"]), color=COLOR[arm], lw=LW,
                solid_capstyle="round", zorder=3)
    handles = arm_handles(arms)
    if hlines:
        for y, txt in hlines:
            ax.axhline(y, color=RULE, lw=1.2, ls="--", zorder=1)
            handles.append(Line2D([], [], color=RULE, lw=1.2, ls="--", label=txt))
    if ylog:
        ax.set_yscale("log")
    if ylim:
        ax.set_ylim(*ylim)
    ax.set_xlabel("Training iteration")
    ax.set_ylabel(ylabel)
    ax.set_xlim(steps[0], steps[-1])
    style_axes(ax)
    ax.legend(handles=handles, loc=legend_loc, frameon=False)
    fig.tight_layout(pad=0.4)
    save(fig, name)


def fig_constraints_components(D):
    comps = [("cost_singularity", "(a) Singularity"),
             ("cost_joint_limit", "(b) Joint limit"),
             ("cost_collision", "(c) Collision")]
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 3.9))
    for ax, (metric, title) in zip(axes, comps):
        for arm in ARMS:
            m = D["training"][arm][metric]
            ax.plot(np.array(m["steps"]), ema(m["mean"]), color=COLOR[arm], lw=2.0, zorder=3)
        ax.set_title(title, pad=8)
        ax.set_xlabel("Training iteration")
        ax.set_xlim(0, 1500)
        style_axes(ax)
    axes[0].set_ylabel("Cost contribution")
    fig.legend(handles=arm_handles(), loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 1.10))
    fig.tight_layout(pad=0.5)
    save(fig, "fig_constraints_components")


def fig_lambda_traj(D):
    """Per-seed Lagrange multiplier, one panel per constrained arm, all five seeds drawn.

    Output filename is `lambda_traj`, replacing the black-line-art version produced by the
    superseded make_ch4_figs.py, so the \\includegraphics path in 04_results.tex is unchanged.

    Content is deliberately PER-SEED and NOT the across-seed mean: Section 4.7 quotes individual
    peak values ("15.84 to 48.05 at d = 25") and the caption says "all five seeds", so a mean
    curve would contradict the text it illustrates. Seeds are separated by line style as well as
    colour here, because five series in one panel is past what colour alone reads well.

    Not smoothed. Each trace is a single seed rather than an average, the feature of interest is
    one sharp peak, and smoothing would understate the peak values the prose quotes.
    """
    panels = [("cppo", r"(a) cPPO, $d = 25$"), ("cppo15", r"(b) cPPO, $d = 15$")]
    dashes = [(0, ()), (0, (5, 2)), (0, (1.5, 1.5)), (0, (6, 2, 1.5, 2)), (0, (3, 1.5, 1, 1.5))]

    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.2), sharey=True)
    for ax, (arm, title) in zip(axes, panels):
        for seed, dash in zip(SEEDS, dashes):
            lam = np.array(D["training"][arm]["_lambda_series"][str(seed)])
            ax.plot(np.arange(len(lam)), lam, color=COLOR[arm], lw=1.7,
                    linestyle=dash, label=f"seed {seed}", zorder=3)
        ax.set_xlim(0, 300)
        ax.set_title(title, pad=8)
        ax.set_xlabel("Training iteration")
        style_axes(ax)
    axes[0].set_ylabel(r"Lagrange multiplier $\lambda$")
    axes[1].legend(frameon=False, loc="upper right", handlelength=3.0, fontsize=11.5)
    fig.text(0.5, -0.02, r"$\lambda$ is zero for the remaining 1200 iterations in every run.",
             ha="center", fontsize=11.5, color=INK)
    fig.tight_layout(pad=0.5)
    save(fig, "lambda_traj")


def fig_seed_variance(D):
    """Per-seed training episodic cost, one panel per arm, every seed drawn individually.

    This figure carries the variance-collapse evidence that the removed +/- std bands used to
    show. Shared log y-axis so the three panels are directly comparable by eye.
    """
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 4.1), sharey=True)
    budget = {"ctrl": None, "cppo": 25, "cppo15": 15}
    panel = ["(a) ", "(b) ", "(c) "]
    for k, (ax, arm) in enumerate(zip(axes, ARMS)):
        m = D["training"][arm]["mean_episode_cost"]
        steps = np.array(m["steps"])
        per_seed = m["per_seed_tail"]
        for i, s in enumerate(SEEDS):
            ax.plot(steps, ema(D["training"][arm]["_seed_series"][str(s)]),
                    color=COLOR[arm], lw=1.0, alpha=0.45, zorder=2)
        ax.plot(steps, ema(m["mean"]), color=COLOR[arm], lw=2.6, zorder=4)
        if budget[arm]:
            ax.axhline(budget[arm], color=RULE, lw=1.2, ls="--", zorder=1)
            ax.text(1480, budget[arm] * 1.15, f"d = {budget[arm]}", fontsize=11,
                    color=RULE, ha="right", va="bottom")
        spread = max(per_seed.values()) / max(min(per_seed.values()), 1e-9)
        ax.set_title(f"{panel[k]}{LABEL[arm]}\nseed spread {spread:.0f}$\\times$", pad=8)
        ax.set_xlabel("Training iteration")
        ax.set_xlim(0, 1500)
        ax.set_yscale("log")
        ax.set_ylim(1, 500)
        style_axes(ax)
    axes[0].set_ylabel("Episodic safety cost")
    fig.legend(handles=[Line2D([], [], color=INK, lw=2.6, label="across-seed mean"),
                        Line2D([], [], color=INK, lw=1.0, alpha=0.45, label="individual seed")],
               loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.09))
    fig.tight_layout(pad=0.5)
    save(fig, "fig_seed_variance")


def fig_per_seed_cost(D):
    """Per-seed training episodic cost: one VERTICAL segment per seed joining its three arms.

    The layout is fixed by the text it illustrates. Section 4.6 says "each seed contributes one
    vertical segment joining its three arm values" and argues explicitly for this over three
    sorted bands, so seeds go on the x-axis and arms are distinguished by marker colour and
    shape. Do not transpose it to arms-on-x without rewriting that paragraph and the caption.

    Training tail means, matching Table 4.5's upper block, not the evaluation block.
    """
    tr = D["training"]
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    x = np.arange(len(SEEDS))
    marks = {"ctrl": ("o", 8.0), "cppo": ("o", 7.0), "cppo15": ("s", 6.8)}

    for i, seed in enumerate(SEEDS):                       # the joining segment
        ys = [tr[a]["mean_episode_cost"]["per_seed_tail"][str(seed)] for a in ARMS]
        ax.plot([i, i, i], ys, color="#9A9A9A", lw=1.2, zorder=2)
    for a in ARMS:                                          # the three arm markers
        ys = [tr[a]["mean_episode_cost"]["per_seed_tail"][str(s)] for s in SEEDS]
        mk, ms = marks[a]
        ax.plot(x, ys, linestyle="none", marker=mk, ms=ms, color=COLOR[a],
                mec="white", mew=1.1, label=LABEL[a], zorder=4)

    for b in (25, 15):
        ax.axhline(b, color=RULE, lw=1.3, ls="--", zorder=1)
        ax.text(len(SEEDS) - 0.55, b * 1.07, f"$d = {b}$", fontsize=11.5,
                color=RULE, ha="right", va="bottom")

    ax.set_xticks(x)
    ax.set_xticklabels([f"seed {s}" for s in SEEDS])
    ax.set_xlim(-0.45, len(SEEDS) - 0.55)
    ax.set_ylabel("Episodic safety cost (training tail mean)")
    ax.set_yscale("log")
    style_axes(ax)
    ax.legend(loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.15))
    fig.tight_layout(pad=0.5)
    save(fig, "per_seed_cost")


# ----------------------------------------------------------------------------- bar figures
def fig_eval_task_performance(D):
    """Left: success bars zoomed to the top of the range. Right: the same data as failure
    rate on a log axis, where the near-identical successes separate clearly.

    The zoomed baseline of panel (a) is declared in its title and reinforced by a hatched
    strip below the axis break, so a zoomed axis can never be misread as a full 0-100 scale.
    Layout is set explicitly rather than by tight_layout, which cannot solve this arrangement.
    """
    ev = D["evaluation"]
    metrics = [("lift_rel_pct", "Lift\nsuccess"),
               ("goal_reach_1cm_pct", "Goal-reach\n< 1 cm"),
               ("goal_reach_2cm_pct", "Goal-reach\n< 2 cm"),
               ("goal_reach_5cm_pct", "Goal-reach\n< 5 cm")]
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.6, 4.8))
    x = np.arange(len(metrics))
    width = 0.26
    base, top = 90.0, 102.4

    for j, arm in enumerate(ARMS):
        vals = [ev[arm][k] for k, _ in metrics]
        off = (j - 1) * width
        axL.bar(x + off, vals, width, color=COLOR[arm], zorder=3,
                edgecolor="white", linewidth=0.7)
        for xi, v in zip(x + off, vals):
            axL.text(xi, v + 0.16, f"{v:.2f}", ha="center", va="bottom", fontsize=10)
    # hatched strip marking the suppressed 0-90 % region
    axL.axhspan(base, base + 0.42, facecolor="white", edgecolor=INK,
                hatch="////", lw=0.0, zorder=5)
    axL.set_ylim(base, top)
    axL.set_yticks([90, 92, 94, 96, 98, 100])
    axL.set_xticks(x)
    axL.set_xticklabels([m[1] for m in metrics])
    axL.set_ylabel("Episodes (%)")
    axL.set_title("(a) Success rate (axis zoomed; 0--90 % suppressed)", pad=10)
    style_axes(axL)

    for j, arm in enumerate(ARMS):
        fails = [max(100.0 - ev[arm][k], 1e-3) for k, _ in metrics]
        off = (j - 1) * width
        axR.bar(x + off, fails, width, color=COLOR[arm], zorder=3,
                edgecolor="white", linewidth=0.7)
        for xi, v in zip(x + off, fails):
            axR.text(xi, v * 1.10, f"{v:.2f}", ha="center", va="bottom", fontsize=10)
    axR.set_yscale("log")
    axR.set_ylim(0.05, 20)
    axR.set_xticks(x)
    axR.set_xticklabels([m[1] for m in metrics])
    axR.set_ylabel("Failure rate (%), log scale")
    axR.set_title("(b) The same data as failure rate (lower is better)", pad=10)
    style_axes(axR)

    fig.legend(handles=arm_handles(), loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 0.99))
    fig.subplots_adjust(left=0.065, right=0.985, top=0.80, bottom=0.13, wspace=0.20)
    save(fig, "fig_eval_task_performance")


def fig_eval_safety_violations(D):
    """2 x 2 grid, one safety metric per panel, each on its own scale."""
    ev = D["evaluation"]
    panels = [
        ("sing_touched_pct", "(a) Singularity margin entered", "Episodes (%)", False),
        ("joint_touched_pct", "(b) Joint limit touched", "Episodes (%)", False),
        ("true_singularity_pct", r"(c) True singularity crossing ($w < 10^{-4}$)", "Episodes (%)", True),
        ("coll_touched_pct", "(d) Collision floor touched", "Episodes (%)", False),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11.4, 8.0))
    x = np.arange(len(ARMS))
    for ax, (key, title, ylab, ylog) in zip(axes.ravel(), panels):
        vals = [ev[a][key] for a in ARMS]
        for j, a in enumerate(ARMS):
            v = vals[j]
            ax.bar(j, max(v, 1e-4) if ylog else v, 0.58, color=COLOR[a], zorder=3,
                   edgecolor="white", linewidth=0.8)
        if ylog:
            ax.set_yscale("log")
            ax.set_ylim(1e-2, max(vals) * 4)
        else:
            ax.set_ylim(0, max(max(vals) * 1.30, 1e-3))
        for j, v in enumerate(vals):
            lab = "0.00" if v == 0 else (f"{v:.3f}" if v < 0.1 else f"{v:.2f}")
            ypos = (max(v, 1e-2) * 1.18) if ylog else (v + max(vals) * 0.04)
            ax.text(j, ypos, lab, ha="center", va="bottom", fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels([LABEL[a].replace(" (", "\n(") for a in ARMS])
        ax.set_ylabel(ylab)
        ax.set_title(title, pad=8)
        style_axes(ax)
    fig.tight_layout(pad=1.0, h_pad=2.6, w_pad=2.4)
    save(fig, "fig_eval_safety_violations")


# ----------------------------------------------------------------------------- main
def main():
    setup_font()
    D = load()
    if "_seed_series" not in D["training"]["ctrl"]:
        sys.exit("final_results_summary.json lacks per-seed series; re-run build_final_results_data.py")

    print(f"writing to {OUTDIR}")
    training_curve_fig(D, "mean_reward", "Mean episodic reward", "fig_mean_reward")
    # ylim clips an early-training transient that dips below 1; the untrained phase is not the
    # object of comparison and the full range would compress the converged region into a sliver.
    # The caption must say the axis is clipped.
    training_curve_fig(D, "mean_episode_cost", "Mean episodic safety cost", "fig_mean_episode_cost",
                       ylog=True, ylim=(1, 400), legend_loc="lower right",
                       hlines=[(25, "budget d = 25"), (15, "budget d = 15")])
    training_curve_fig(D, "reaching_object", "Reaching-object reward", "fig_reaching_object")
    training_curve_fig(D, "lifting_object", "Lifting-object reward", "fig_lifting_object")
    training_curve_fig(D, "manip_min", "Mean episode-minimum manipulability $w$",
                       "fig_manipulability", legend_loc="upper right")
    fig_constraints_components(D)
    fig_lambda_traj(D)
    fig_seed_variance(D)
    fig_per_seed_cost(D)
    fig_eval_task_performance(D)
    fig_eval_safety_violations(D)
    print(f"done -- 11 figures written to {OUTDIR}")
    print("REMINDER: curve-figure captions must state that curves are EMA-smoothed "
          f"(weight {EMA_WEIGHT}) for legibility.")


if __name__ == "__main__":
    main()
