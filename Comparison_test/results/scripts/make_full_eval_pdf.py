#!/usr/bin/env python3
"""Full evaluation results, every run x every eval seed, one table per run.

Reads ur5_grasp/tools/eval_policy_results.csv directly (the append-only summary CSV written
by eval_policy.py), resolves the correct row for every (arm, seed, eval_seed) combination by
checkpoint-path date (the established project rule -- "filter by checkpoint path date, never
by label", since the CSV carries stale rows from earlier sweeps under the same labels), and
renders one table per run (40 runs: ppo/ctrl/cppo/cppo15 x seeds 1-5/50-54), columns = eval
seeds 101/102/103 plus their arithmetic mean.

Row definitions are taken verbatim from eval_policy.py's own log/header lines, not guessed --
see the comments beside CSV_COLUMNS below for the exact source line.

Usage (from Comparison_test/, no Isaac Sim needed -- pure CSV):
    python3 results/scripts/make_full_eval_pdf.py
"""
import csv
import re
import statistics
from collections import defaultdict
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether,
)

ROOT = Path(__file__).resolve().parents[2]  # Comparison_test/
CSV_PATH = ROOT / "ur5_grasp" / "tools" / "eval_policy_results.csv"
OUT_PATH = ROOT / "results" / "EVAL_RESULTS_FULL.pdf"

ARMS = [
    ("ppo", re.compile(r"^ppo_s(\d+)$"), "ppo (unconstrained PPO baseline)"),
    ("ctrl", re.compile(r"^ctrl_s(\d+)$"), "ctrl (cost critic present, lambda pinned to 0 -- the control arm)"),
    ("cppo", re.compile(r"^cppo_s(\d+)$"), "cppo (PPO-Lagrangian, cost_limit = 25)"),
    ("cppo15", re.compile(r"^cppo15_s(\d+)$"), "cppo15 (PPO-Lagrangian, cost_limit = 15)"),
]
SEEDS = [1, 2, 3, 4, 5, 50, 51, 52, 53, 54]
EVAL_SEEDS = ["101", "102", "103"]
DATE_RE = re.compile(r"/(\d{4}-\d{2}-\d{2})_\d{2}-\d{2}-\d{2}_")

# (csv_column, row_label, format, source line in eval_policy.py)
# "pct" -> value already 0-100, one decimal place. "num4"/"num3"/"num2" -> fixed decimals.
ROWS = [
    ("ep_len_mean", "Mean episode length (steps)", "num1"),
    ("lift_rel_pct", "Lift success >= 0.50 x commanded goal height (%)  <- headline", "pct"),
    ("lift_rel_ever_pct", "  ... bar reached at any point in the episode (%)", "pct"),
    ("lift_abs_pct", "  ... legacy fixed-height definition, Day-22 (%)", "pct"),
    ("goal_z_mean", "Mean commanded goal height (m)", "num3"),
    ("goal_1cm_pct", "Goal-reach success @ 1 cm (%)  <- headline", "pct"),
    ("goal_2cm_pct", "Goal-reach success @ 2 cm (%)", "pct"),
    ("goal_5cm_pct", "Goal-reach success @ 5 cm (%)", "pct"),
    ("goal_dist_mean", "Final goal distance -- mean (m)", "num4"),
    ("goal_dist_median", "Final goal distance -- median (m)", "num4"),
    ("goal_dist_p90", "Final goal distance -- p90 (m)", "num4"),
    ("goal_dist_max", "Final goal distance -- worst episode (m)", "num4"),
    ("sing_step_pct", "Singularity margin violated (% of steps)", "pct"),
    ("joint_step_pct", "Joint-limit margin violated (% of steps)", "pct"),
    ("coll_step_pct", "Collision floor violated (% of steps)", "pct"),
    ("sing_ep_pct", "Episodes that touched the singularity margin (%)", "pct"),
    ("joint_ep_pct", "Episodes that touched the joint-limit margin (%)", "pct"),
    ("coll_ep_pct", "Episodes that touched the collision floor (%)", "pct"),
    ("min_w_mean", "Manipulability w -- mean of episode-minimum", "num4"),
    ("min_w_worst", "Manipulability w -- worst single episode", "num4"),
    ("cost_mean", "Episodic safety cost -- mean", "num2"),
    ("cost_p90", "Episodic safety cost -- p90", "num2"),
]


def ckpt_date(row):
    m = DATE_RE.search(row["checkpoint"])
    return m.group(1) if m else "0000-00-00"


def load_resolved():
    rows = list(csv.DictReader(open(CSV_PATH)))
    buckets = defaultdict(list)
    for r in rows:
        label = r["label"]
        for arm, pat, _ in ARMS:
            m = pat.match(label)
            if m:
                seed = int(m.group(1))
                if seed in SEEDS and r["eval_seed"] in EVAL_SEEDS:
                    buckets[(arm, seed, r["eval_seed"])].append(r)
                break
    resolved = {}
    for k, v in buckets.items():
        resolved[k] = max(v, key=ckpt_date)
    missing = [
        (arm, seed, es) for arm, _, _ in ARMS for seed in SEEDS for es in EVAL_SEEDS
        if (arm, seed, es) not in resolved
    ]
    if missing:
        raise SystemExit(f"FATAL: missing {len(missing)} combos, e.g. {missing[:5]}")
    bad_dates = [(k, ckpt_date(v)) for k, v in resolved.items() if ckpt_date(v) != "2026-08-01"]
    if bad_dates:
        raise SystemExit(f"FATAL: {len(bad_dates)} resolved rows are not dated 2026-08-01: {bad_dates[:5]}")
    return resolved


def fmt(value_str, kind):
    v = float(value_str)
    if kind == "pct":
        return f"{v:.2f}"
    if kind == "num1":
        return f"{v:.1f}"
    if kind == "num2":
        return f"{v:.2f}"
    if kind == "num3":
        return f"{v:.3f}"
    if kind == "num4":
        return f"{v:.4f}"
    return value_str


def mean_fmt(values_str, kind):
    vals = [float(v) for v in values_str]
    m = statistics.fmean(vals)
    if kind == "pct":
        return f"{m:.2f}"
    if kind == "num1":
        return f"{m:.1f}"
    if kind == "num2":
        return f"{m:.2f}"
    if kind == "num3":
        return f"{m:.3f}"
    if kind == "num4":
        return f"{m:.4f}"
    return f"{m:.4f}"


def build():
    resolved = load_resolved()
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
    h3 = ParagraphStyle("h3", parent=styles["Heading3"], spaceBefore=10, spaceAfter=4,
                         textColor=colors.HexColor("#1a1a1a"))
    body = styles["Normal"]
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, leading=10,
                            textColor=colors.HexColor("#444444"))
    caption = ParagraphStyle("caption", parent=styles["Normal"], fontSize=7.5, leading=9,
                              textColor=colors.HexColor("#666666"), fontName="Courier")

    story = []
    story.append(Paragraph("Full evaluation results", title_style))
    story.append(Paragraph(
        "Every run x every evaluation seed, matrix-v2 batch (ppo / ctrl / cppo) "
        "+ the cppo15 arm. One table per run; columns are the three evaluation seeds "
        "plus their arithmetic mean.", body))
    story.append(Spacer(1, 10))

    prov = [
        "<b>Provenance.</b>",
        "Task: Isaac-Lift-Cube-UR5e-v0 (frozen weld env).",
        "Training: ppo/ctrl/cppo -- commit 567e4c0, tag matrix-v2, 1500 iterations, num_envs=4096, "
        "seeds 1-5 and 50-54. cppo15 -- commit 866ea33, tag matrix-v2-cppo15, same protocol, "
        "cost_limit=15 (differs from cppo by that one field only).",
        "Evaluation: eval_policy.py, 1000 episodes per (checkpoint x eval-seed), num_envs=128, "
        "eval seeds 101/102/103 (disjoint from training seeds), deterministic policy, "
        "lift_frac=0.50, goal tolerances 1/2/5 cm.",
        "Source: ur5_grasp/tools/eval_policy_results.csv, resolved to the newest-dated checkpoint "
        "per (label, eval_seed) -- this file is append-only and carries stale rows from earlier "
        "sweeps under the same labels; 18 of the 120 combinations used in this report had a stale "
        "duplicate that was excluded by checkpoint date.",
        "Generated by results/scripts/make_full_eval_pdf.py.",
    ]
    for line in prov:
        story.append(Paragraph(line, small))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "<b>Reading the tables.</b> Two metrics are marked &lt;- headline: lift success "
        "(object reaches at least half the commanded goal height, at the end of the episode) "
        "and goal-reach @ 1 cm, per the audit's reporting rule (a single threshold like the "
        "legacy 5 cm bar saturates near 0% or 100% once a policy converges, so it cannot "
        "discriminate two converged policies -- report the full distribution instead). "
        "\"Step\" safety metrics are soft-margin fractions over every control step across all "
        "1000 episodes; \"episode\" safety metrics are the percentage of episodes that touched "
        "that constraint at all, i.e. sing_frac/joint_frac/coll_frac &gt; 0 for at least one step.",
        small))
    story.append(PageBreak())

    for arm_key, _, arm_title in ARMS:
        story.append(Paragraph(arm_title, h2))
        for seed in SEEDS:
            rows_for_seed = {es: resolved[(arm_key, seed, es)] for es in EVAL_SEEDS}
            any_row = next(iter(rows_for_seed.values()))
            ckpt = any_row["checkpoint"]

            table_data = [["Metric", "eval-seed 101", "eval-seed 102", "eval-seed 103", "mean of 3"]]
            for col, label, kind in ROWS:
                vals = [rows_for_seed[es][col] for es in EVAL_SEEDS]
                cells = [fmt(v, kind) for v in vals]
                cells.append(mean_fmt(vals, kind))
                table_data.append([label] + cells)

            t = Table(table_data, colWidths=[3.05 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 0.75 * inch],
                      repeatRows=1)
            t.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 7.3),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
                ("BACKGROUND", (4, 1), (4, -1), colors.HexColor("#f5f5f5")),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))

            block = [
                Paragraph(f"{arm_key}_s{seed}  --  1000 episodes per eval seed", h3),
                t,
                Paragraph(f"checkpoint: {ckpt}", caption),
                Spacer(1, 8),
            ]
            story.append(KeepTogether(block))
        story.append(PageBreak())

    # drop the trailing page break
    if story and isinstance(story[-1], PageBreak):
        story.pop()

    doc = SimpleDocTemplate(
        str(OUT_PATH), pagesize=letter,
        leftMargin=0.55 * inch, rightMargin=0.55 * inch,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        title="Full evaluation results -- matrix-v2 + cppo15",
    )
    doc.build(story)
    print(f"wrote {OUT_PATH}  ({OUT_PATH.stat().st_size} bytes)")
    print(f"runs: {len(ARMS)} arms x {len(SEEDS)} seeds = {len(ARMS)*len(SEEDS)} tables, "
          f"{len(ARMS)*len(SEEDS)*len(EVAL_SEEDS)} source rows")


if __name__ == "__main__":
    build()
