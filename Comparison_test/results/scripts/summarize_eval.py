# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Aggregate ur5_grasp/tools/eval_policy_results.csv into the Layer-1 results table.

Pure python — no torch, no Isaac. Safe to run anywhere, any time.

Two variance sources are kept apart, which is the whole point of the Day-23 protocol:
  * EVAL-seed sd   -- spread of one frozen checkpoint over eval seeds 101/102/103.
                      This is "how noisy is the exam".
  * TRAINING-seed sd -- spread of an algorithm over its three training seeds, each one
                      first averaged over its eval seeds. This is "how reliable is the
                      algorithm". Reporting only the second, as Day 22 did, hides which
                      of the two a number came from.

DE-DUPLICATION IS NOT OPTIONAL. eval_policy.py APPENDS, deliberately, so a re-run
accumulates rather than overwrites. A partially-completed sweep therefore leaves stale
rows behind — the Day-23 file had two, from the attempt that crashed on the InferenceMode
bug. Averaging them in would silently double-weight two checkpoints. Last row wins, so a
re-run supersedes an older one.

    python3 results/scripts/summarize_eval.py            # print the table
    python3 results/scripts/summarize_eval.py --write    # also write results/LAYER1_RESULTS_eval.md
"""

from __future__ import annotations

import argparse
import csv
import os
import statistics as st

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))  # Comparison_test/
CSV_IN = os.path.join(_ROOT, "ur5_grasp", "tools", "eval_policy_results.csv")
MD_OUT = os.path.join(_ROOT, "results", "LAYER1_RESULTS_eval.md")

COST_LIMIT = 25.0  # from agents/rsl_rl_cppo_cfg.py — the episodic budget cPPO constrains
MANIP_FLOOR = 0.045  # from ur5e_lift_env.py

# (csv field, display name, format, "lower is better"?)
FIELDS = [
    ("lift_rel_pct", "Lift success (>=50% of goal height)", "{:.2f} %", False),
    ("goal_1cm_pct", "Goal-reach < 1 cm", "{:.2f} %", False),
    ("goal_2cm_pct", "Goal-reach < 2 cm", "{:.2f} %", False),
    ("goal_5cm_pct", "Goal-reach < 5 cm", "{:.2f} %", False),
    ("goal_dist_mean", "Final cube-goal distance (m)", "{:.4f}", True),
    ("sing_step_pct", "Singularity, % of steps", "{:.2f} %", True),
    ("joint_step_pct", "Joint-limit, % of steps", "{:.2f} %", True),
    ("coll_step_pct", "Collision, % of steps", "{:.2f} %", True),
    ("min_w_mean", "Manipulability, mean episode min", "{:.4f}", False),
    ("cost_mean", "Episodic safety cost", "{:.2f}", True),
]


def load(path: str):
    """Read the append-only CSV, keeping only the LAST row per (label, eval_seed)."""
    with open(path) as fh:
        rows = list(csv.DictReader(fh))
    keep: dict[tuple[str, str], dict] = {}
    for r in rows:
        keep[(r["label"], r["eval_seed"])] = r  # last wins
    dropped = len(rows) - len(keep)
    return list(keep.values()), len(rows), dropped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=CSV_IN)
    ap.add_argument("--write", action="store_true", help="Write the markdown results file too.")
    args = ap.parse_args()

    rows, n_raw, n_dropped = load(args.csv)
    labels = sorted({r["label"] for r in rows})
    seeds = sorted({r["eval_seed"] for r in rows})

    out: list[str] = []

    def emit(s: str = "") -> None:
        print(s)
        out.append(s)

    emit("# Layer 1 — evaluation results (frozen policies)")
    emit()
    emit(f"Source: `{os.path.relpath(args.csv, _ROOT)}` — {n_raw} rows read, {n_dropped} stale "
         f"duplicate(s) dropped, {len(rows)} used.")
    emit(f"Checkpoints: {len(labels)}   Eval seeds: {', '.join(seeds)}   "
         f"Episodes per (checkpoint, seed): {rows[0]['episodes']}   num_envs: 128")
    emit()
    emit("**Protocol.** Deterministic frozen policies, observation corruption off. Lift success "
         "means the cube reaches at least 50% of THAT episode's commanded goal height. Goal-reach "
         "is bounded at 1 cm. Safety violations are counted DURING EVALUATION, per step, on the "
         "frozen policy — not read off training TensorBoard scalars as the Day-22 table did.")
    emit()

    # ---- per checkpoint, averaged over eval seeds --------------------------------------
    per: dict[str, dict[str, float]] = {}
    per_sd: dict[str, dict[str, float]] = {}
    for lab in labels:
        sub = [r for r in rows if r["label"] == lab]
        per[lab] = {}
        per_sd[lab] = {}
        for f, *_ in FIELDS:
            v = [float(r[f]) for r in sub]
            per[lab][f] = st.fmean(v)
            per_sd[lab][f] = st.stdev(v) if len(v) > 1 else 0.0
        per[lab]["_n"] = len(sub)
        per[lab]["goal_z_mean"] = st.fmean(float(r["goal_z_mean"]) for r in sub)
        per[lab]["ep_len_mean"] = st.fmean(float(r["ep_len_mean"]) for r in sub)

    # frame sanity check — the lift bar is worthless if this is wrong
    gz = [per[l]["goal_z_mean"] for l in labels]
    ok = all(0.30 < g < 0.45 for g in gz)
    emit(f"**Frame sanity check:** mean commanded goal height = {st.fmean(gz):.4f} m "
         f"(expected ~0.375 from the pos_z range 0.25-0.50). "
         f"{'PASS — the lift bar is computed in the right frame.' if ok else '**FAIL — lift numbers are invalid.**'}")
    emit()

    emit("## Per checkpoint (mean over eval seeds 101/102/103, 1000 episodes each)")
    emit()
    emit("| Checkpoint | Lift % | Goal @1cm | @2cm | @5cm | Dist (m) | Sing % | Joint % | min w | Cost |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    order = [l for l in ("ppo_s1", "ppo_s2", "ppo_s3", "cppo_s1", "cppo_s2", "cppo_s3") if l in per]
    order += [l for l in labels if l not in order]
    for lab in order:
        p = per[lab]
        emit(f"| `{lab}` | {p['lift_rel_pct']:.1f} | {p['goal_1cm_pct']:.1f} | {p['goal_2cm_pct']:.1f} | "
             f"{p['goal_5cm_pct']:.1f} | {p['goal_dist_mean']:.4f} | {p['sing_step_pct']:.1f} | "
             f"{p['joint_step_pct']:.1f} | {p['min_w_mean']:.4f} | {p['cost_mean']:.1f} |")
    emit()

    # ---- eval-seed noise ---------------------------------------------------------------
    emit("## How noisy is the exam? (sd over the 3 eval seeds, per checkpoint)")
    emit()
    emit("| Checkpoint | Goal @1cm sd | Sing % sd | Cost sd |")
    emit("|---|---|---|---|")
    for lab in order:
        emit(f"| `{lab}` | {per_sd[lab]['goal_1cm_pct']:.2f} | {per_sd[lab]['sing_step_pct']:.2f} | "
             f"{per_sd[lab]['cost_mean']:.2f} |")
    emit()
    max_eval_sd = max(per_sd[l]["goal_1cm_pct"] for l in labels)
    emit(f"Largest eval-seed sd on goal-reach: **{max_eval_sd:.2f} percentage points**. Compare that "
         "with the training-seed sd in the next table. The exam is essentially noise-free; all the "
         "spread that matters comes from the training seed.")
    emit()

    # ---- algorithm level ---------------------------------------------------------------
    algs = sorted({lab.rsplit("_s", 1)[0] for lab in labels})
    emit("## Headline — mean ± sd over the 3 TRAINING seeds")
    emit()
    emit("| Metric | " + " | ".join(a.upper() for a in algs) + " |")
    emit("|---" * (len(algs) + 1) + "|")
    for f, name, fmt, lower_better in FIELDS:
        cells = []
        for a in algs:
            v = [per[f"{a}_s{i}"][f] for i in (1, 2, 3) if f"{a}_s{i}" in per]
            m, s = st.fmean(v), (st.stdev(v) if len(v) > 1 else 0.0)
            cells.append(f"{fmt.format(m)} ± {fmt.format(s).replace(' %', '')}")
        emit(f"| {name} | " + " | ".join(cells) + " |")
    emit()
    emit("Per-seed values:")
    emit()
    for f, name, fmt, _ in FIELDS:
        parts = []
        for a in algs:
            v = [per[f"{a}_s{i}"][f] for i in (1, 2, 3) if f"{a}_s{i}" in per]
            parts.append(f"{a} " + " / ".join(fmt.format(x).replace(" %", "") for x in v))
        emit(f"- **{name}** — " + "  |  ".join(parts))
    emit()

    emit(f"`cost_limit` = {COST_LIMIT:g} (undiscounted episodic budget). `MANIP_FLOOR` = {MANIP_FLOOR:g}.")
    emit()

    # ---- episode-level detail ----------------------------------------------------------
    # The summary CSV averages; these are the questions only the per-episode file can answer.
    ep_dir = os.path.join(_ROOT, "ur5_grasp", "tools", "eval_episodes")
    if os.path.isdir(ep_dir):
        emit("## Episode-level detail (pooled over all eval seeds)")
        emit()
        emit("| Checkpoint | Episodes | Numerically singular (w < 1e-4) | Over cost budget | Median cost | "
             "Lifted at some point | Still lifted at the end | Early terminations |")
        emit("|---|---|---|---|---|---|---|---|")
        for lab in order:
            pool: list[dict] = []
            for s in seeds:
                f = os.path.join(ep_dir, f"{lab}_seed{s}.csv")
                if os.path.isfile(f):
                    with open(f) as fh:
                        pool += list(csv.DictReader(fh))
            if not pool:
                continue
            n = len(pool)
            sing0 = sum(1 for x in pool if float(x["min_w"]) < 1e-4) / n * 100
            costs = [float(x["cost_sum"]) for x in pool]
            over = sum(1 for c in costs if c > COST_LIMIT) / n * 100
            ever = sum(1 for x in pool if float(x["lift_rel_ever"]) > 0.5) / n * 100
            end = sum(1 for x in pool if float(x["lift_rel"]) > 0.5) / n * 100
            early = sum(1 for x in pool if float(x["ep_len"]) < 250) / n * 100
            emit(f"| `{lab}` | {n} | {sing0:.1f} % | {over:.1f} % | {st.median(costs):.2f} | "
                 f"{ever:.1f} % | {end:.1f} % | {early:.2f} % |")
        emit()
        emit("**How to read this.** *Numerically singular* means the arm's manipulability fell to "
             "~0 at some point in the episode — an actual singularity crossing, not merely dipping "
             "under the 0.045 floor. *Over cost budget* is the fraction of episodes whose "
             f"undiscounted safety cost exceeded `cost_limit` = {COST_LIMIT:g}; this is the "
             "constraint cPPO was trained to respect and PPO was never told about. The gap between "
             "*lifted at some point* and *still lifted at the end* isolates a policy that raises the "
             "cube and then fails to hold it at the commanded height.")

    if args.write:
        with open(MD_OUT, "w") as fh:
            fh.write("\n".join(out) + "\n")
        print(f"\n[written to {MD_OUT}]")


if __name__ == "__main__":
    main()
