#!/usr/bin/env python3
"""Single source of every number in Chapter 4.

Reads Comparison_test/final_results/ ONLY (the locked scope: 3 arms, 5 seeds) and
prints every table the results chapter needs, per-arm and per-seed. Nothing in the
chapter should be typed by hand; if a number is not in this output, it does not go
in the book.

Locked scope (CLAUDE.md):
    arms  : PPO_baseline (= ctrl, labelled "PPO (baseline)"), CPPO_25, CPPO15
    seeds : 1, 3, 4, 52, 54
    ppo_redundant/ holds the plain-PPO arm, used here only for the identity check.

Usage:  python3 Comparison_test/results/scripts/summarize_final.py [--json out.json]
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "final_results"
SEEDS = [1, 3, 4, 52, 54]
ARMS = ["PPO_baseline", "CPPO_25", "CPPO15"]
LABEL = {"PPO_baseline": "PPO (baseline)", "CPPO_25": "cPPO d=25", "CPPO15": "cPPO d=15"}
TAIL = 0.10          # tail mean over the final 10 % of training iterations
SING_EPS = 1e-4      # a true kinematic singularity crossing


# ----------------------------------------------------------------- readers

def read_scalar(path: Path) -> list[float]:
    with path.open() as fh:
        return [float(r["value"]) for r in csv.DictReader(fh)]


def training_metric(arm: str, seed: int, metric: str) -> list[float] | None:
    hits = sorted(glob.glob(str(ROOT / "training" / arm / f"seed_{seed}" / f"*__{metric}.csv")))
    hits = [h for h in hits if not h.endswith(f"{metric}__time.csv")]
    if not hits:
        return None
    return read_scalar(Path(hits[0]))


def tail_mean(series: list[float]) -> float:
    n = max(1, int(round(len(series) * TAIL)))
    return st.fmean(series[-n:])


def eval_episodes(arm: str, seed: int) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for f in sorted(glob.glob(str(ROOT / "evaluation" / arm / f"seed_{seed}" / "*.csv"))):
        with open(f) as fh:
            for r in csv.DictReader(fh):
                rows.append({k: float(v) for k, v in r.items()})
    return rows


def pct(x: float) -> str:
    return f"{100.0 * x:.2f}"


def quant(xs: list[float], q: float) -> float:
    ys = sorted(xs)
    if not ys:
        return float("nan")
    i = q * (len(ys) - 1)
    lo, hi = math.floor(i), math.ceil(i)
    return ys[lo] if lo == hi else ys[lo] + (ys[hi] - ys[lo]) * (i - lo)


def sd(xs: list[float]) -> float:
    ys = [x for x in xs if not math.isnan(x)]
    return st.stdev(ys) if len(ys) > 1 else 0.0


def mean(xs: list[float]) -> float:
    ys = [x for x in xs if not math.isnan(x)]
    return st.fmean(ys) if ys else float("nan")


# ----------------------------------------------------------------- sections

def section_training(out: dict) -> None:
    print("\n" + "=" * 78)
    print("TRAINING, tail mean over the final 10 % of 1500 iterations")
    print("=" * 78)
    metrics = ["Train__mean_reward", "Loss__mean_episode_cost", "safety__viol_singularity",
               "safety__viol_joint_limit", "safety__viol_collision", "safety__manipulability_min"]
    out["training"] = {}
    for m in metrics:
        print(f"\n{m}")
        print(f"  {'arm':<16}" + "".join(f"{'s'+str(s):>10}" for s in SEEDS) + f"{'mean':>11}{'sd':>10}")
        out["training"][m] = {}
        for arm in ARMS:
            vals = []
            for s in SEEDS:
                ser = training_metric(arm, s, m)
                vals.append(tail_mean(ser) if ser else float("nan"))
            out["training"][m][arm] = {"per_seed": vals, "mean": mean(vals), "sd": sd(vals)}
            print(f"  {LABEL[arm]:<16}" + "".join(f"{v:>10.4g}" for v in vals)
                  + f"{mean(vals):>11.4g}{sd(vals):>10.4g}")


def section_lambda(out: dict) -> None:
    print("\n" + "=" * 78)
    print("LAGRANGE MULTIPLIER, per seed (peak, final, iteration of peak, iters above 0.01)")
    print("=" * 78)
    out["lambda"] = {}
    for arm in ["CPPO_25", "CPPO15"]:
        print(f"\n{LABEL[arm]}")
        print(f"  {'seed':<7}{'peak':>10}{'at iter':>10}{'final':>10}{'iters>0.01':>12}")
        out["lambda"][arm] = {}
        for s in SEEDS:
            ser = training_metric(arm, s, "Loss__cost_lambda")
            if not ser:
                continue
            peak, at = max(ser), ser.index(max(ser))
            engaged = sum(1 for v in ser if v > 0.01)
            out["lambda"][arm][s] = {"peak": peak, "at": at, "final": ser[-1], "engaged": engaged}
            print(f"  {s:<7}{peak:>10.3f}{at:>10d}{ser[-1]:>10.4f}{engaged:>12d}")


def section_eval(out: dict) -> None:
    print("\n" + "=" * 78)
    print("EVALUATION, frozen deterministic policy")
    print("5 training seeds x 3 evaluation seeds x 1000 episodes = 15,000 episodes per arm")
    print("=" * 78)
    out["evaluation"] = {}
    for arm in ARMS:
        per_seed = {s: eval_episodes(arm, s) for s in SEEDS}
        pooled = [r for s in SEEDS for r in per_seed[s]]

        def per_seed_stat(fn):
            return [fn(per_seed[s]) for s in SEEDS]

        rec = {
            "n_episodes": len(pooled),
            "lift_abs": st.fmean(r["lift_abs"] for r in pooled),
            "goal_1cm": st.fmean(1.0 if r["goal_dist_final"] < 0.01 else 0.0 for r in pooled),
            "goal_2cm": st.fmean(1.0 if r["goal_dist_final"] < 0.02 else 0.0 for r in pooled),
            "goal_5cm": st.fmean(1.0 if r["goal_dist_final"] < 0.05 else 0.0 for r in pooled),
            "goal_mean": st.fmean(r["goal_dist_final"] for r in pooled),
            "goal_med": quant([r["goal_dist_final"] for r in pooled], 0.5),
            "goal_p90": quant([r["goal_dist_final"] for r in pooled], 0.9),
            "goal_max": max(r["goal_dist_final"] for r in pooled),
            "sing_cross": st.fmean(1.0 if r["min_w"] < SING_EPS else 0.0 for r in pooled),
            "sing_cross_n": sum(1 for r in pooled if r["min_w"] < SING_EPS),
            "min_w_mean": st.fmean(r["min_w"] for r in pooled),
            "min_w_worst": min(r["min_w"] for r in pooled),
            "joint_any": st.fmean(1.0 if r["joint_frac"] > 0 else 0.0 for r in pooled),
            "coll_any": st.fmean(1.0 if r["coll_frac"] > 0 else 0.0 for r in pooled),
            "cost_mean": st.fmean(r["cost_sum"] for r in pooled),
            "cost_p90": quant([r["cost_sum"] for r in pooled], 0.9),
            "cost_max": max(r["cost_sum"] for r in pooled),
        }
        # per-seed dispersion, which the superseded chapter said was unavailable
        rec["per_seed"] = {
            "cost_mean": per_seed_stat(lambda rs: st.fmean(r["cost_sum"] for r in rs)),
            "goal_1cm": per_seed_stat(
                lambda rs: st.fmean(1.0 if r["goal_dist_final"] < 0.01 else 0.0 for r in rs)),
            "lift_abs": per_seed_stat(lambda rs: st.fmean(r["lift_abs"] for r in rs)),
            "sing_cross": per_seed_stat(
                lambda rs: st.fmean(1.0 if r["min_w"] < SING_EPS else 0.0 for r in rs)),
            "joint_any": per_seed_stat(
                lambda rs: st.fmean(1.0 if r["joint_frac"] > 0 else 0.0 for r in rs)),
            "min_w_mean": per_seed_stat(lambda rs: st.fmean(r["min_w"] for r in rs)),
        }
        rec["cost_mean_sd_across_seeds"] = sd(rec["per_seed"]["cost_mean"])
        rec["goal_1cm_sd"] = sd(rec["per_seed"]["goal_1cm"])
        rec["lift_abs_sd"] = sd(rec["per_seed"]["lift_abs"])
        rec["sing_cross_sd"] = sd(rec["per_seed"]["sing_cross"])
        out["evaluation"][arm] = rec

        print(f"\n{LABEL[arm]}   ({rec['n_episodes']} episodes)")
        print(f"  lift success                 {pct(rec['lift_abs'])} %  "
              f"(sd across seeds {pct(rec['lift_abs_sd'])})")
        print(f"  goal < 1 cm                  {pct(rec['goal_1cm'])} %  "
              f"(sd across seeds {pct(rec['goal_1cm_sd'])})")
        print(f"  goal < 2 cm                  {pct(rec['goal_2cm'])} %")
        print(f"  goal < 5 cm                  {pct(rec['goal_5cm'])} %")
        print(f"  goal dist mean/med/p90 (m)   {rec['goal_mean']:.4f} / "
              f"{rec['goal_med']:.4f} / {rec['goal_p90']:.4f}   max {rec['goal_max']:.3f}")
        print(f"  true singularity crossings   {pct(rec['sing_cross'])} % "
              f"({rec['sing_cross_n']} / {rec['n_episodes']})  sd {pct(rec['sing_cross_sd'])}")
        print(f"  mean episode-min w           {rec['min_w_mean']:.5f}")
        print(f"  worst single-episode w       {rec['min_w_worst']:.6f}")
        print(f"  joint limit touched          {pct(rec['joint_any'])} % of episodes")
        print(f"  collision touched            {pct(rec['coll_any'])} % of episodes")
        print(f"  episodic cost mean/p90/max   {rec['cost_mean']:.2f} / "
              f"{rec['cost_p90']:.2f} / {rec['cost_max']:.2f}")
        print(f"  episodic cost, sd ACROSS SEEDS {rec['cost_mean_sd_across_seeds']:.2f}")
        print("  per-seed mean episodic cost  "
              + "  ".join(f"s{s}={v:.2f}" for s, v in zip(SEEDS, rec['per_seed']['cost_mean'])))
        print("  per-seed joint-limit touch   "
              + "  ".join(f"s{s}={100*v:.2f}%" for s, v in zip(SEEDS, rec['per_seed']['joint_any'])))


def section_identity(out: dict) -> None:
    """Plain ppo against ctrl on the training scalars, for Section 4.2."""
    print("\n" + "=" * 78)
    print("IDENTITY CHECK, plain ppo against ctrl (training scalars, tail mean)")
    print("=" * 78)
    base = ROOT / "ppo_redundant" / "results" / "training" / "PPO"
    out["identity"] = {}
    for m in ["Train__mean_reward", "safety__viol_singularity", "safety__manipulability_min"]:
        print(f"\n{m}")
        for s in SEEDS:
            hits = sorted(glob.glob(str(base / f"seed_{s}" / f"*__{m}.csv")))
            hits = [h for h in hits if not h.endswith(f"{m}__time.csv")]
            ctrl = training_metric("PPO_baseline", s, m)
            if not hits or not ctrl:
                print(f"  seed {s}: missing")
                continue
            p, c = tail_mean(read_scalar(Path(hits[0]))), tail_mean(ctrl)
            same = "IDENTICAL" if abs(p - c) < 1e-9 else f"DIFFER by {p - c:.3e}"
            out["identity"].setdefault(m, {})[s] = {"ppo": p, "ctrl": c, "same": same}
            print(f"  seed {s:<3} ppo={p:<14.6f} ctrl={c:<14.6f} {same}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="also write the numbers to this path")
    args = ap.parse_args()

    if not ROOT.exists():
        raise SystemExit(f"final_results not found at {ROOT}")

    print(f"source: {ROOT}")
    print(f"arms  : {', '.join(LABEL[a] for a in ARMS)}")
    print(f"seeds : {SEEDS}")

    out: dict = {"seeds": SEEDS, "arms": ARMS}
    section_training(out)
    section_lambda(out)
    section_eval(out)
    section_identity(out)

    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2))
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
