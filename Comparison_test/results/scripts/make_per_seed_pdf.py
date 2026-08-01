#!/usr/bin/env python3
"""
Render the per-seed training results tables to a PDF for the thesis appendix.

Consumes `results/per_seed_training_tables.json`, written by `make_per_seed_tables.py`.
Run that script first.

Thesis formatting conventions (logbook/06_writing.md): Times New Roman body, tables and
captions centre-aligned, a few purposeful colours only. Landscape A4 is used because each
table is 10 columns wide (3 arms x 3 statistics, plus the metric label).

Usage:
    python3 make_per_seed_pdf.py
Output:
    results/PER_SEED_TRAINING_TABLES.pdf
"""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
DATA = RESULTS / "per_seed_training_tables.json"
OUT = RESULTS / "PER_SEED_TRAINING_TABLES.pdf"

SEEDS = [1, 2, 3, 4, 5, 50, 51, 52, 53, 54]
ARMS = ["ppo", "ctrl", "cppo"]
ARM_LABEL = {"ppo": "PPO", "ctrl": "ctrl", "cppo": "cPPO"}

METRICS = [
    ("Mean reward",                    "Train__mean_reward",              2),
    ("Mean episode cost",              "Loss__mean_episode_cost",         2),
    ("Violation — singularity",   "safety__viol_singularity",        4),
    ("Violation — joint limit",   "safety__viol_joint_limit",        4),
    ("Violation — collision",     "safety__viol_collision",          4),
    ("Reward — lifting_object",   "Episode_Reward__lifting_object",  3),
    ("Reward — reaching_object",  "Episode_Reward__reaching_object", 3),
]

# purposeful colour only: one accent for headers, one tint for the arm the thesis argues for
ACCENT = colors.HexColor("#1F3864")
TINT_CPPO = colors.HexColor("#DCE7F5")
TINT_ALT = colors.HexColor("#F2F2F2")
RULE = colors.HexColor("#9AA5B1")

# Times New Roman is not present in this sandbox; ReportLab's Times-Roman is the same
# metric-compatible family and is what the thesis body font should be matched to on export.
FONT = "Times-Roman"
FONT_B = "Times-Bold"
FONT_I = "Times-Italic"


def styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=ss["Title"], fontName=FONT_B,
                                fontSize=17, leading=21, textColor=ACCENT,
                                spaceAfter=2 * mm),
        "sub": ParagraphStyle("s", parent=ss["Normal"], fontName=FONT_I,
                              fontSize=10, leading=13, alignment=TA_CENTER,
                              textColor=colors.HexColor("#444444"), spaceAfter=5 * mm),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName=FONT_B,
                             fontSize=12.5, leading=15, textColor=ACCENT,
                             spaceBefore=3 * mm, spaceAfter=2 * mm),
        "body": ParagraphStyle("b", parent=ss["Normal"], fontName=FONT,
                               fontSize=9.5, leading=13, alignment=TA_JUSTIFY,
                               spaceAfter=2.5 * mm),
        "cap": ParagraphStyle("c", parent=ss["Normal"], fontName=FONT,
                              fontSize=8.5, leading=11, alignment=TA_CENTER,
                              textColor=colors.HexColor("#444444"),
                              spaceBefore=1.5 * mm),
        # header cells sit on the dark accent fill, so they need their own light colour —
        # a TableStyle TEXTCOLOR command does NOT override a Paragraph's own textColor
        "hdr": ParagraphStyle("hd", parent=ss["Normal"], fontName=FONT_B,
                              fontSize=9, leading=11, alignment=TA_CENTER,
                              textColor=colors.white),
        "rowlab": ParagraphStyle("rl", parent=ss["Normal"], fontName=FONT,
                                 fontSize=8.5, leading=10.5, alignment=TA_CENTER,
                                 textColor=colors.black),
        "note": ParagraphStyle("n", parent=ss["Normal"], fontName=FONT,
                               fontSize=8.5, leading=11.5, alignment=TA_JUSTIFY,
                               spaceAfter=2 * mm),
    }


def fmt(v, dp):
    return f"{v:.{dp}f}"


def seed_table(data, seed, st):
    hdr1 = [Paragraph("Metric", st["hdr"])]
    for a in ARMS:
        hdr1.append(Paragraph(ARM_LABEL[a], st["hdr"]))
        hdr1 += ["", ""]
    hdr2 = [""] + [Paragraph(x, st["hdr"]) for x in ("final", "mean", "tail")] * len(ARMS)

    rows = [hdr1, hdr2]
    dagger_cells = []
    for r, (label, tag, dp) in enumerate(METRICS, start=2):
        row = [Paragraph(label, st["rowlab"])]
        for i, arm in enumerate(ARMS):
            s = data[str(seed)][tag].get(arm)
            if s is None:
                row += ["n/a", "n/a", "n/a"]
                continue
            cell = fmt(s["final"], dp)
            if s.get("substituted"):
                cell += " †"
                dagger_cells.append((1 + 3 * i, r))
            row += [cell, fmt(s["mean"], dp), fmt(s["tail"], dp)]
        rows.append(row)

    w = [46 * mm] + [22 * mm] * (3 * len(ARMS))
    t = Table(rows, colWidths=w, repeatRows=2, hAlign="CENTER")

    cmds = [
        ("FONTNAME", (0, 0), (-1, 1), FONT_B),
        ("FONTNAME", (0, 2), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BACKGROUND", (0, 0), (-1, 1), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 1), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("LINEBELOW", (0, 1), (-1, 1), 0.9, colors.white),
    ]
    # merge each arm's 3 statistic columns under one header cell
    for i in range(len(ARMS)):
        c0 = 1 + 3 * i
        cmds.append(("SPAN", (c0, 0), (c0 + 2, 0)))
    cmds.append(("SPAN", (0, 0), (0, 1)))
    # heavier separator between arms
    for i in range(1, len(ARMS)):
        c0 = 1 + 3 * i
        cmds.append(("LINEBEFORE", (c0, 0), (c0, -1), 1.1, colors.white))
        cmds.append(("LINEBEFORE", (c0, 2), (c0, -1), 1.1, ACCENT))
    cmds.append(("LINEBEFORE", (1, 2), (1, -1), 1.1, ACCENT))
    # tint the cPPO block and alternate metric rows
    c0 = 1 + 3 * (len(ARMS) - 1)
    cmds.append(("BACKGROUND", (c0, 2), (c0 + 2, -1), TINT_CPPO))
    for r in range(2, 2 + len(METRICS)):
        if r % 2 == 1:
            cmds.append(("BACKGROUND", (0, r), (c0 - 1, r), TINT_ALT))
    t.setStyle(TableStyle(cmds))
    return t


def build():
    data = json.loads(DATA.read_text())
    st = styles()
    doc = SimpleDocTemplate(
        str(OUT), pagesize=landscape(A4),
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title="Per-seed training results — matrix-v2 3-arm batch",
        author="Md. Abdur Rabbi Touhid",
    )
    story = []

    story.append(Paragraph(
        "Per-Seed Training Results — PPO vs ctrl vs cPPO", st["title"]))
    story.append(Paragraph(
        "Matrix-v2, 3-arm batch · commit <b>567e4c0</b>, tag <b>matrix-v2</b> · "
        "10 seeds · 1500 iterations · <i>Isaac-Lift-Cube-UR5e-v0</i>", st["sub"]))

    story.append(Paragraph("Scope and provenance", st["h2"]))
    story.append(Paragraph(
        "This appendix reports <b>training-time</b> telemetry for every individual seed of the "
        "matrix-v2 three-arm batch, so that the pooled statistics quoted in the Results chapter "
        "can be audited seed by seed. Each arm was trained for 1500 iterations at "
        "<i>num_envs</i> = 4096 using rsl_rl 3.0.1 against the frozen weld environment. The "
        "three arms differ from one another by exactly one variable: <b>PPO</b> is the "
        "unconstrained baseline; <b>ctrl</b> adds the cost critic but pins the Lagrange "
        "multiplier to zero, so the constraint cannot influence the policy; <b>cPPO</b> "
        "releases the multiplier against an episodic cost budget of 25.", st["body"]))
    story.append(Paragraph(
        "All values are read from the per-run TensorBoard exports in "
        "<i>results/tb_csv/</i> by <i>results/scripts/make_per_seed_tables.py</i>. Runs are "
        "selected by dated directory path, never by run label, because three superseded "
        "pre-audit cPPO runs from 2026-07-30 still carry the same labels as the current ones. "
        "All thirty source runs used here were confirmed to be 2026-08-01 runs.", st["body"]))

    story.append(Paragraph("How to read the three columns per arm", st["h2"]))
    story.append(Paragraph(
        "<b>final</b> is the value at the last logged iteration (1499). <b>mean</b> is the "
        "arithmetic mean over all 1500 logged iterations — it includes the untrained early "
        "phase, so it describes the area under the learning curve rather than converged "
        "performance, and it is systematically pessimistic for reward and optimistic for cost. "
        "<b>tail</b> is the mean over the final 10% of iterations (150 points). "
        "<b>The tail column is the one to quote:</b> it is the statistic used throughout "
        "<i>MATRIX_V2_PARTIAL_3ARM.md</i> and the Results chapter, and it is the only one of "
        "the three that will cross-reference against those documents.", st["body"]))

    story.append(Paragraph("Notes on specific rows", st["h2"]))
    story.append(Paragraph(
        "<b>† Mean episode cost, PPO column.</b> The tag <i>Loss/mean_episode_cost</i> is "
        "written only by the Lagrangian runner, so the PPO arm never logged it and the value "
        "shown is <b>ctrl's</b>. This substitution is valid, not a convenience: PPO and ctrl "
        "were shown to be bitwise identical — all 68 actor and reward-critic tensors "
        "byte-for-byte equal inside the two checkpoints, on all ten seeds, reconfirmed "
        "independently at evaluation time. The ctrl arm exists precisely to measure the "
        "episodic cost incurred by a policy that does not act on it. Note that PPO and ctrl "
        "are consequently identical in <i>every</i> row of <i>every</i> table below; this was "
        "verified numerically across all seeds, metrics and statistics, and is the batch's "
        "central validity check rather than a duplication error.", st["note"]))
    story.append(Paragraph(
        "<b>Violation rows.</b> These are soft-margin step fractions — the fraction of "
        "control steps on which a continuous safety margin fell the wrong side of a threshold, "
        "measured on a still-exploring policy during training. They are <b>not</b> the "
        "frozen-policy safety figures reported in the Results chapter, which count true "
        "singularity crossings (w &lt; 1e-4) and per-episode joint-limit contact over 30,000 "
        "deterministic evaluation episodes. The two must not be substituted for one another; "
        "the soft-margin fraction exaggerates differences by testing a binary threshold on a "
        "continuous quantity.", st["note"]))
    story.append(Paragraph(
        "<b>Dispersion convention.</b> Where this appendix's per-seed values are pooled and "
        "compared against <i>MATRIX_V2_PARTIAL_3ARM.md</i>, note that the standard deviations "
        "in that document are population standard deviations (ddof = 0). Sample standard "
        "deviations computed from the ten seeds here are larger by a factor of "
        "√(10/9) ≈ 1.054. Both are correct; state which convention is used.", st["note"]))
    story.append(Paragraph(
        "<b>Scope limit.</b> This is a three-of-five-arm batch. The cppo10/cppo15 "
        "binding-budget arm and the SAC arm are not included, so nothing here speaks to the "
        "effect of an actively binding safety budget.", st["note"]))

    story.append(PageBreak())

    for n, seed in enumerate(SEEDS):
        block = [
            Paragraph(f"Seed {seed}", st["h2"]),
            seed_table(data, seed, st),
            Paragraph(
                f"Table A.{n + 1} — Training metrics for seed {seed}: PPO, ctrl and cPPO "
                f"(budget 25). Values are final / full-run mean / final-10% tail mean over "
                f"1500 iterations.", st["cap"]),
        ]
        story.append(KeepTogether(block))
        story.append(Spacer(1, 5 * mm))
        if n % 2 == 1 and n != len(SEEDS) - 1:
            story.append(PageBreak())

    doc.build(story)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
