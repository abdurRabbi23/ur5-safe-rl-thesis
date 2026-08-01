#!/usr/bin/env python3
"""
Per-seed training results tables for the matrix-v2 3-arm batch.

Reads the per-run / per-tag CSVs in `Comparison_test/results/tb_csv/` (written by
`ur5_grasp/tools/summarize_runs.py`) and emits one table per training seed comparing
`ppo`, `ctrl` and `cppo` on the metrics requested for the thesis appendix.

For every metric and arm three values are reported:
    final     value at the last logged iteration (1499)
    mean      arithmetic mean over ALL logged iterations (the "average over the 1500
              iterations" figure) - note this includes the untrained early phase and is
              therefore a learning-curve-area number, not a converged-performance number
    tail      mean over the final 10% of iterations - this is the statistic used in
              `MATRIX_V2_PARTIAL_3ARM.md` and in Chapter 4, and is the one to quote

Two data traps are handled explicitly, both documented in
`Comparison_test/results/MATRIX_V2_PARTIAL_3ARM.md` section 5:

 1. `logs/rsl_rl/ur5e_lift_cppo/` also holds three SUPERSEDED pre-audit `cppo_s1/s2/s3` runs
    dated 2026-07-30 (gradient-clip-bug era) under the same run labels as the good ones.
    tb_csv therefore contains two files per tag for those labels. Runs are selected by
    RUN_DATE_PREFIX below, never by label.
 2. `Loss/mean_episode_cost` is written only by the Lagrangian runner, so the `ppo` arm has
    no such tag at all. Because Chapter 4 section 4.2 establishes that `ppo` and `ctrl` are
    bitwise identical (all 68 actor + reward-critic tensors byte-for-byte equal, on all ten
    seeds, reconfirmed at evaluation), `ctrl`'s value is a valid stand-in for `ppo`'s and is
    substituted here, flagged with a dagger. See COST_SUBSTITUTION below.

Usage:
    python3 make_per_seed_tables.py                 # writes markdown + json next to this script
    python3 make_per_seed_tables.py --arms ppo ctrl cppo cppo15   # once cppo15 completes

Output:
    results/PER_SEED_TRAINING_TABLES.md
    results/per_seed_training_tables.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

# --------------------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
TB_CSV = RESULTS / "tb_csv"

# Only runs whose directory name starts with this are the matrix-v2 batch. This is the
# filter that excludes the superseded 2026-07-30 cppo runs. Filter by DATE, never by label.
RUN_DATE_PREFIX = "2026-08-01"

# Runs started at or after this time-of-day on 2026-08-01 belong to the cppo15 arm / smoke
# tests, not to the 3-arm matrix. The matrix ran 00:01-06:51.
MATRIX_TIME_MAX = "07-00-00"

DEFAULT_ARMS = ["ppo", "ctrl", "cppo"]
SEEDS = [1, 2, 3, 4, 5, 50, 51, 52, 53, 54]

TAIL_FRACTION = 0.10  # last 10% of iterations, matching MATRIX_V2_PARTIAL_3ARM.md

# (display label, tb_csv tag suffix, number of decimal places)
METRICS = [
    ("Mean reward",                      "Train__mean_reward",              2),
    ("Mean episode cost",                "Loss__mean_episode_cost",         2),
    ("Violation - singularity",          "safety__viol_singularity",        4),
    ("Violation - joint limit",          "safety__viol_joint_limit",        4),
    ("Violation - collision",            "safety__viol_collision",          4),
    ("Reward term - lifting_object",     "Episode_Reward__lifting_object",  3),
    ("Reward term - reaching_object",    "Episode_Reward__reaching_object", 3),
]

# metric tag -> arm that has no such tag, and the arm to borrow from
COST_SUBSTITUTION = {"Loss__mean_episode_cost": ("ppo", "ctrl")}


# --------------------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------------------

def run_dir_name(path: Path) -> str:
    """'2026-08-01_00-01-25_ppo_s1__Train__mean_reward.csv' -> run dir portion."""
    return path.name.split("__", 1)[0]


def parse_run(run: str) -> tuple[str, str, str] | None:
    """Return (date, time, label) for a run dir name, or None if unparseable."""
    m = re.match(r"^(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_(.+)$", run)
    return (m.group(1), m.group(2), m.group(3)) if m else None


def in_matrix_batch(run: str) -> bool:
    parsed = parse_run(run)
    if parsed is None:
        return False
    date, time, _ = parsed
    return date == RUN_DATE_PREFIX and time < MATRIX_TIME_MAX


def find_csv(arm: str, seed: int, tag: str) -> Path | None:
    """Locate the tb_csv file for one (arm, seed, tag), restricted to the matrix batch."""
    label = f"{arm}_s{seed}"
    hits = []
    for p in TB_CSV.glob(f"*_{label}__{tag}.csv"):
        run = run_dir_name(p)
        parsed = parse_run(run)
        # guard against 'cppo_s1' glob-matching a run labelled e.g. 'xcppo_s1'
        if parsed is None or parsed[2] != label:
            continue
        if in_matrix_batch(run):
            hits.append(p)
    if not hits:
        return None
    if len(hits) > 1:
        raise RuntimeError(
            f"ambiguous: {len(hits)} matrix-batch files for {label} / {tag}: "
            + ", ".join(h.name for h in hits)
            + " -- resolve before trusting any number"
        )
    return hits[0]


def read_series(path: Path) -> list[float]:
    with path.open() as fh:
        return [float(row["value"]) for row in csv.DictReader(fh)]


def summarise(values: list[float]) -> dict[str, float | int]:
    n = len(values)
    tail_n = max(1, int(round(n * TAIL_FRACTION)))
    tail = values[-tail_n:]
    return {
        "final": values[-1],
        "mean": sum(values) / n,
        "tail": sum(tail) / len(tail),
        "n_iter": n,
        "n_tail": tail_n,
    }


# --------------------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------------------

def collect(arms: list[str]) -> tuple[dict, list[str]]:
    data: dict = {}
    notes: list[str] = []
    for seed in SEEDS:
        data[seed] = {}
        for label, tag, _dp in METRICS:
            data[seed][tag] = {}
            for arm in arms:
                src_arm = arm
                substituted = False
                path = find_csv(arm, seed, tag)
                if path is None and tag in COST_SUBSTITUTION:
                    missing_arm, borrow_from = COST_SUBSTITUTION[tag]
                    if arm == missing_arm:
                        path = find_csv(borrow_from, seed, tag)
                        src_arm, substituted = borrow_from, True
                if path is None:
                    data[seed][tag][arm] = None
                    notes.append(f"MISSING: {arm}_s{seed} / {tag}")
                    continue
                s = summarise(read_series(path))
                s["substituted"] = substituted
                s["source_run"] = run_dir_name(path)
                s["source_arm"] = src_arm
                data[seed][tag][arm] = s
    return data, notes


def fmt(v: float, dp: int) -> str:
    return f"{v:.{dp}f}"


def render_markdown(data: dict, arms: list[str]) -> str:
    out: list[str] = []
    A = "Add" if False else None  # noqa
    out.append("# Per-seed training results — matrix-v2, 3-arm batch\n")
    out.append(
        "Generated by `results/scripts/make_per_seed_tables.py` from `results/tb_csv/`.\n"
        "Source runs: commit `567e4c0`, tag `matrix-v2`, task `Isaac-Lift-Cube-UR5e-v0`, "
        "1500 iterations at `num_envs = 4096`, `rsl_rl` 3.0.1.\n"
    )
    out.append(
        "**Three values per arm.** `final` is the value at the last logged iteration (1499). "
        "`mean` is the arithmetic mean over all 1500 logged points — it includes the "
        "untrained early phase, so it measures learning-curve area rather than converged "
        "performance. `tail` is the mean over the final 10% of iterations, which is the "
        "statistic used in `MATRIX_V2_PARTIAL_3ARM.md` and in Chapter 4 — **quote `tail`, "
        "not `mean`, when comparing against those documents.**\n"
    )
    out.append(
        "**† Mean episode cost for `ppo`.** `Loss/mean_episode_cost` is written only by the "
        "Lagrangian runner, so the `ppo` arm never logged it. The value shown is `ctrl`'s, "
        "which is valid because `ppo` and `ctrl` were shown to be bitwise identical — all 68 "
        "actor and reward-critic tensors byte-for-byte equal, on all ten seeds, reconfirmed "
        "independently at evaluation time (`MATRIX_V2_PARTIAL_3ARM.md` §2). `ctrl` exists "
        "precisely to measure the episodic cost of a policy that does not act on it.\n"
    )
    out.append(
        "**Violation rows** are soft-margin step fractions from training telemetry, i.e. the "
        "fraction of control steps on which a continuous margin fell the wrong side of a "
        "threshold, measured on a still-exploring policy. They are *not* the frozen-policy "
        "safety numbers reported in Chapter 4 §4.5, which count true singularity crossings "
        "(w < 1e-4) and per-episode joint-limit contact over 30,000 evaluation episodes. "
        "Do not substitute one for the other.\n"
    )
    out.append("---\n")

    for seed in SEEDS:
        out.append(f"## Seed {seed}\n")
        header = "| Metric | " + " | ".join(
            f"{a} final | {a} mean | {a} tail" for a in arms
        ) + " |"
        sep = "|---|" + "---|" * (3 * len(arms))
        out.append(header)
        out.append(sep)
        for label, tag, dp in METRICS:
            cells = []
            row_label = label
            for arm in arms:
                s = data[seed][tag].get(arm)
                if s is None:
                    cells += ["n/a", "n/a", "n/a"]
                    continue
                mark = "†" if s.get("substituted") else ""
                cells += [
                    fmt(s["final"], dp) + mark,
                    fmt(s["mean"], dp),
                    fmt(s["tail"], dp),
                ]
            out.append(f"| {row_label} | " + " | ".join(cells) + " |")
        out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=DEFAULT_ARMS)
    args = ap.parse_args()

    data, notes = collect(args.arms)

    md = RESULTS / "PER_SEED_TRAINING_TABLES.md"
    md.write_text(render_markdown(data, args.arms))

    js = RESULTS / "per_seed_training_tables.json"
    js.write_text(json.dumps(data, indent=2, default=str))

    print(f"wrote {md}")
    print(f"wrote {js}")
    if notes:
        print("\nNOTES:")
        for n in notes:
            print("  " + n)


if __name__ == "__main__":
    main()
