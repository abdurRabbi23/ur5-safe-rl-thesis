#!/usr/bin/env python3
# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Read every training run under `logs/` and write a READABLE report + CSVs.

Why this exists
---------------
Until now the only way to see how a run went was TensorBoard in a browser, or
`results/scripts/make_layer1_figs.py` — which reads CSVs from a HARDCODED path
(`/sessions/compassionate-relaxed-sagan/mnt/.../results/tb_csv`) that belonged to a
throwaway sandbox and no longer exists on any machine. So the export step that produced
those CSVs was manual and is not reproducible. This script closes that loop: it walks the
log tree, writes one CSV per run per scalar into `results/tb_csv/`, and writes a flushed
plain-text summary that can be read straight off the folder.

Standing project rule (four demonstrated failures, run_log_new.md Days 21-22): a script
that only `print()`s cannot be run for a result — piping to capture stdout is what causes
the block-buffering that discards it. Everything here goes through `log()`, which prints
AND writes AND flushes.

No Isaac Sim, no GPU, no simulation. It only parses TensorBoard event files, so it is
safe to run while a training batch is still going (it will simply report the runs that
exist so far, including partial ones).

Usage
-----
    cd ~/Abdur_Rabbi_THESIS/Comparison_test
    ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/summarize_runs.py

    # optional: restrict to one experiment directory
    ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/summarize_runs.py --experiment ur5e_lift

Plain `python3` also works if tensorboard is importable in that interpreter; isaaclab.sh
is used above only because it is guaranteed to have it.

Outputs
-------
    ur5_grasp/tools/summarize_runs_report.txt   human-readable summary (READ THIS)
    results/tb_csv/<run_name>__<tag>.csv        step,value per scalar tag per run
"""

from __future__ import annotations

import argparse
import glob
import os
import sys

# --------------------------------------------------------------------------------------
# Paths. Deliberately anchored to THIS FILE, not to the current working directory.
#
# Everything else in this project resolves `logs/` relative to cwd (that is the documented
# gotcha in logbook/09 — it is why runs must be launched from inside "Comparison_test/").
# A reporting tool should not inherit that trap: it is read-only and there is exactly one
# correct log tree for it, the one belonging to this copy of the package.
# --------------------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))                 # .../ur5_grasp/tools
_PKG_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))      # .../Comparison_test
_LOG_ROOT = os.path.join(_PKG_ROOT, "logs", "rsl_rl")
_CSV_DIR = os.path.join(_PKG_ROOT, "results", "tb_csv")
_REPORT = os.path.join(_HERE, "summarize_runs_report.txt")

# Scalar tags worth putting in the headline table, in display order. Matching is by
# case-insensitive substring, because rsl_rl and the env's `extras["log"]` channel prefix
# tags differently ("Train/mean_reward", "Episode/viol_singularity", ...) and the exact
# prefixes have changed between rsl_rl versions. Anything not matched here still gets a
# CSV and still appears in the per-run full tag dump.
_HEADLINE_PATTERNS = [
    "mean_reward",
    "mean_episode_length",
    "success",
    "cost",
    "viol_singularity",
    "viol_collision",
    "viol_joint",
    "manipulability_min",
    "lambda",
]

_FH = None


def log(msg: str = "") -> None:
    """print + write + flush. The only output path in this file."""
    print(msg)
    if _FH is not None:
        _FH.write(msg + "\n")
        _FH.flush()


def _fmt(v) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        if abs(v) >= 1000 or (v != 0 and abs(v) < 0.001):
            return f"{v:.3e}"
        return f"{v:.4f}"
    return str(v)


def _tail_mean(values, frac: float = 0.1) -> float | None:
    """Mean of the last `frac` of a series — a less noisy 'final value' than the last
    point alone, which for a 1500-iter PPO run is a single rollout and bounces."""
    if not values:
        return None
    n = max(1, int(len(values) * frac))
    tail = values[-n:]
    return sum(tail) / len(tail)


def collect_runs(experiment: str | None) -> list[tuple[str, str]]:
    """Return [(experiment_name, run_dir), ...] sorted by experiment then run name."""
    if not os.path.isdir(_LOG_ROOT):
        return []
    pattern = os.path.join(_LOG_ROOT, experiment if experiment else "*", "*")
    out = []
    for d in sorted(glob.glob(pattern)):
        if not os.path.isdir(d):
            continue
        # a run dir is one that actually holds TensorBoard event files
        if glob.glob(os.path.join(d, "events.out.tfevents.*")):
            out.append((os.path.basename(os.path.dirname(d)), d))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--experiment",
        type=str,
        default=None,
        help="Only summarise this experiment dir (e.g. ur5e_lift). Default: all.",
    )
    parser.add_argument(
        "--no-csv", action="store_true", help="Skip writing per-tag CSVs; report only."
    )
    args = parser.parse_args()

    log("=" * 78)
    log("TRAINING RUN SUMMARY")
    log("=" * 78)
    log(f"log root : {_LOG_ROOT}")
    log(f"report   : {_REPORT}")
    log("")

    try:
        from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    except ImportError as exc:
        log(f"FATAL: cannot import TensorBoard's EventAccumulator ({exc}).")
        log("Run this through isaaclab.sh, which has tensorboard installed:")
        log('    cd ~/Abdur_Rabbi_THESIS/Comparison_test')
        log("    ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/summarize_runs.py")
        return 2

    runs = collect_runs(args.experiment)
    if not runs:
        log("NO RUNS FOUND.")
        log("")
        log("Expected: logs/rsl_rl/<experiment_name>/<timestamp>_<run_name>/events.out.tfevents.*")
        log("")
        log("If you have trained but see this message, the near-certain cause is the")
        log("cwd-relative log path documented in logbook/09: train.py resolves 'logs/'")
        log("against the CURRENT WORKING DIRECTORY, so a run launched from IsaacLab/ wrote")
        log("its logs into IsaacLab/logs/ instead. Re-launch from inside 'Comparison_test/'.")
        return 1

    if not args.no_csv:
        os.makedirs(_CSV_DIR, exist_ok=True)

    log(f"found {len(runs)} run(s)")
    log("")

    headline_rows = []

    for exp, run_dir in runs:
        run_name = os.path.basename(run_dir)
        log("-" * 78)
        log(f"RUN: {exp}/{run_name}")
        log("-" * 78)

        acc = EventAccumulator(run_dir, size_guidance={"scalars": 0})
        try:
            acc.Reload()
        except Exception as exc:  # noqa: BLE001 — a corrupt event file must not kill the batch
            log(f"  ERROR: could not read event files: {exc}")
            log("")
            continue

        tags = sorted(acc.Tags().get("scalars", []))
        if not tags:
            log("  no scalar tags — run probably died before its first logged iteration")
            log("")
            continue

        series = {}
        for tag in tags:
            events = acc.Scalars(tag)
            steps = [e.step for e in events]
            values = [e.value for e in events]
            series[tag] = (steps, values)

            if not args.no_csv:
                safe = tag.replace("/", "__").replace(" ", "_")
                csv_path = os.path.join(_CSV_DIR, f"{run_name}__{safe}.csv")
                with open(csv_path, "w") as fh:
                    fh.write("step,value\n")
                    for s, v in zip(steps, values):
                        fh.write(f"{s},{v}\n")

        max_step = max(max(s) for s, _ in series.values())
        log(f"  iterations logged : {max_step}")
        log(f"  scalar tags       : {len(tags)}")
        log("")

        # --- headline metrics for this run ------------------------------------------
        picked = {}
        for pattern in _HEADLINE_PATTERNS:
            for tag in tags:
                if pattern in tag.lower():
                    steps, values = series[tag]
                    picked[tag] = (_tail_mean(values), values[-1] if values else None)
        if picked:
            log("  key metrics (tail-mean over last 10% of iterations | final point):")
            width = max(len(t) for t in picked)
            for tag in sorted(picked):
                tm, last = picked[tag]
                log(f"    {tag:<{width}}  {_fmt(tm):>12} | {_fmt(last):>12}")
        else:
            log("  (no tags matched the headline patterns — see full tag list below)")
        log("")

        log("  all scalar tags:")
        for tag in tags:
            log(f"    {tag}")
        log("")

        headline_rows.append((exp, run_name, max_step, picked))

    # --- cross-run comparison table --------------------------------------------------
    log("=" * 78)
    log("CROSS-RUN TABLE")
    log("=" * 78)

    all_tags = sorted({t for _, _, _, p in headline_rows for t in p})
    if not all_tags:
        log("(no headline tags found in any run)")
    else:
        for tag in all_tags:
            log("")
            log(f"{tag}   (tail-mean over last 10% of iterations)")
            label_w = max(len(f"{e}/{r}") for e, r, _, _ in headline_rows)
            for exp, run_name, max_step, picked in headline_rows:
                tm = picked.get(tag, (None, None))[0]
                label = f"{exp}/{run_name}"
                log(f"    {label:<{label_w}}  iters={max_step:<6} {_fmt(tm):>12}")

    log("")
    log("=" * 78)
    log(f"CSVs written to: {_CSV_DIR}" if not args.no_csv else "CSV writing skipped")
    log("=" * 78)
    return 0


if __name__ == "__main__":
    os.makedirs(os.path.dirname(_REPORT), exist_ok=True)
    _FH = open(_REPORT, "w")
    try:
        code = main()
    except Exception:  # noqa: BLE001 — traceback must land IN the report, not on a lost stream
        import traceback

        log("")
        log("UNHANDLED EXCEPTION:")
        log(traceback.format_exc())
        code = 3
    finally:
        log("")
        log(f"[report saved to {_REPORT}]")
        _FH.close()
    sys.exit(code)
