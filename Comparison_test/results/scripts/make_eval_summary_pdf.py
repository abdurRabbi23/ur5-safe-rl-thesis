#!/usr/bin/env python3
"""Evaluation results, SUMMARY subset -- same runs/eval-seeds as EVAL_RESULTS_FULL.pdf, but
only the rows Touhid asked to keep (2026-08-01, Day 24 cont. 2 session):
  mean commanded goal height, lift success, goal-reach @ 1/2/5 cm, final goal distance
  (mean + worst episode), singularity/joint-limit/collision violated (% of steps -- his
  choice over % of episodes touched), episodic safety cost (mean).

Same source, same dedup-by-checkpoint-date logic, same table-per-run layout as
make_full_eval_pdf.py -- deliberately not refactored into a shared module, matching this
project's existing pattern of small standalone report scripts (make_layer1_figs.py,
make_per_seed_tables.py, make_full_eval_pdf.py).

Usage (from Comparison_test/, no Isaac Sim needed -- pure CSV):
    python3 results/scripts/make_eval_summary_pdf.py
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
OUT_PATH = ROOT / "results" / "EVAL_RESULTS_SUMMARY.pdf"

ARMS = [
    ("ppo", re.compile(r"^ppo_s(\d+)$"), "ppo (unconstrained PPO baseline)"),
    ("ctrl", re.compile(r"^ctrl_s(\d+)$"), "ctrl (cost critic present, lambda pinned to 0 -- the control arm)"),
    ("cppo", re.compile(r"^cppo_s(\d+)$"), "cppo (PPO-Lagrangian, cost_limit = 25)"),
    ("cppo15", re.compile(r"^cppo15_s(\d+)$"), "cppo15 (PPO-Lagrangian, cost_limit = 15)"),
]
SEEDS = [1, 2, 3, 4, 5, 50, 51, 52, 53, 54]
EVAL_SEEDS = ["101", "102", "103"]
DATE_RE = re.compile(r"/(\d{4}-\d{2}-\d{2})_\d{2}-\d{2}-\d{2}_")

# Subset selected by Touhid, in the order requested. Step-fraction chosen over episode-touched
# for the three violation rows (his call, 2026-08-01).
ROWS = [
    ("goal_z_mean", "Mean commanded goal height (m)", "num3"),
    ("lift_rel_pct", "Lift success >= 0.50 x commanded goal height (%)", "pct"),
    ("goal_1cm_pct", "Goal-reach success @ 1 cm (%)", "pct"),
    ("goal_2cm_pct", "Goal-reach success @ 2 cm (%)", "pct"),
    ("goal_5cm_pct", "Goal-reach success @ 5 cm (%)", "pct"),
    ("goal_dist_mean", "Final goal distance -- mean (m)", "num4"),
    ("goal_dist_max", "Final goal distance -- worst episode (m)", "num4"),
    ("sing_step_pct", "Singularity margin violated (% of steps)", "pct"),
    ("joint_step_pct", "Joint-limit margin violated (% of steps)", "pct"),
    ("coll_step_pct", "Collision floor violated (% of steps)", "pct"),
    ("cost_mean", "Episodic safety cost -- mean", "num2"),
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
    story.append(Paragraph("Evaluation results -- summary", title_style))
    story.append(Paragraph(
        "Same 40 runs and eval-seed breakdown as EVAL_RESULTS_FULL.pdf, trimmed to a "
        "requested subset of rows: goal height, lift success, goal-reach at three "
        "tolerances, final goal distance (mean and worst episode), the three safety "
        "constraints as step-in-violation fractions, and mean episodic cost.", body))
    story.append(Spacer(1, 10))

    prov = [
        "<b>Provenance.</b> Identical source and resolution logic to EVAL_RESULTS_FULL.pdf "
        "(results/scripts/make_full_eval_pdf.py) -- see that file for the full provenance "
        "block. Task: Isaac-Lift-Cube-UR5e-v0. Training: ppo/ctrl/cppo at tag matrix-v2 "
        "(commit 567e4c0); cppo15 at tag matrix-v2-cppo15 (commit 866ea33), cost_limit=15 "
        "vs cppo's 25. Evaluation: 1000 episodes per (checkpoint x eval-seed), eval seeds "
        "101/102/103, num_envs=128, deterministic policy.",
        "Violation rows show the % of individual control steps in violation (soft margin), "
        "not the % of episodes that touched the constraint at all -- Touhid's choice, "
        "2026-08-01. The full report has both variants if the episode-level view is needed.",
        "Generated by results/scripts/make_eval_summary_pdf.py.",
    ]
    for line in prov:
        story.append(Paragraph(line, small))
    story.append(Spacer(1, 14))

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

            t = Table(table_data, colWidths=[2.55 * inch, 0.95 * inch, 0.95 * inch, 0.95 * inch, 0.85 * inch],
                      repeatRows=1)
            t.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
                ("BACKGROUND", (4, 1), (4, -1), colors.HexColor("#f5f5f5")),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
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

    if story and isinstance(story[-1], PageBreak):
        story.pop()

    doc = SimpleDocTemplate(
        str(OUT_PATH), pagesize=letter,
        leftMargin=0.55 * inch, rightMargin=0.55 * inch,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        title="Evaluation results summary -- matrix-v2 + cppo15",
    )
    doc.build(story)
    print(f"wrote {OUT_PATH}  ({OUT_PATH.stat().st_size} bytes)")
    print(f"runs: {len(ARMS)} arms x {len(SEEDS)} seeds = {len(ARMS)*len(SEEDS)} tables")


if __name__ == "__main__":
    build()
