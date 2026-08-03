#!/usr/bin/env python3
"""
Data aggregation for Chapter 4 (Results), scoped to the LOCKED final dataset only.

Source of truth (do not read anything else -- see Comparison_test/final_results/README.md
and CLAUDE.md "Results scope"):
    Comparison_test/final_results/training/<algo_folder>/seed_<N>/*.csv     (38 metrics/run)
    Comparison_test/final_results/evaluation/<algo_folder>/seed_<N>/*.csv  (3 eval-seed files/run)

Scope: 5 seeds (1, 3, 4, 52, 54) x 3 arms. On-disk folder names are PPO_baseline (= ctrl, "PPO
(baseline)" in prose), CPPO_25 (= cppo, budget 25), CPPO15 (= cppo15, budget 15). The plain `ppo`
arm and seeds {2,5,50,51,53} are excluded by construction -- this script never globs them.

Training: stacks the 5 seeds' step-value series per metric -> per-iteration mean/std across
seeds, plus a tail-mean (last 10% = last 150 of 1500 iterations) per seed for scalar tables.

Evaluation: pools 5 training seeds x 3 eval seeds x 1000 episodes = 15,000 episodes per arm.
Column definitions are taken verbatim from ur5_grasp/scripts/eval_policy.py's own header.

Output: Comparison_test/results/final_results_summary.json (consumed by make_final_results_figs.py
and by the Chapter 4 prose re-derivation -- nothing downstream should read the CSVs directly).

Usage (pure python, no Isaac Sim needed):
    python3 build_final_results_data.py
"""
import csv, glob, os, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.dirname(HERE)
COMPTEST = os.path.dirname(RESULTS)
REPO = os.path.dirname(COMPTEST)

TRAIN = os.path.join(COMPTEST, "final_results", "training")
EVAL = os.path.join(COMPTEST, "final_results", "evaluation")

ARM_FOLDER = {"ctrl": "PPO_baseline", "cppo": "CPPO_25", "cppo15": "CPPO15"}
ARM_PREFIX = {"ctrl": "ctrl", "cppo": "cppo", "cppo15": "cppo15"}
SEEDS = [1, 3, 4, 52, 54]
EVAL_SEEDS = [101, 102, 103]

TRAIN_METRICS = {
    "mean_reward": "Train__mean_reward",
    "mean_episode_cost": "Loss__mean_episode_cost",
    "reaching_object": "Episode_Reward__reaching_object",
    "lifting_object": "Episode_Reward__lifting_object",
    "object_goal_tracking": "Episode_Reward__object_goal_tracking",
    "object_goal_tracking_fine": "Episode_Reward__object_goal_tracking_fine_grained",
    "cost_singularity": "safety__cost_singularity",
    "cost_joint_limit": "safety__cost_joint_limit",
    "cost_collision": "safety__cost_collision",
    "cost_total": "safety__cost_total",
    "viol_singularity": "safety__viol_singularity",
    "viol_joint_limit": "safety__viol_joint_limit",
    "viol_collision": "safety__viol_collision",
    "manip_mean": "safety__manipulability_mean",
    "manip_min": "safety__manipulability_min",
    "cost_lambda": "Loss__cost_lambda",
    "cost_budget_used": "Loss__cost_budget_used",
    "mean_episode_length": "Train__mean_episode_length",
}

EVAL_POOL_COLS = ["goal_dist_final", "lift_rel", "lift_rel_ever", "lift_abs",
                   "sing_frac", "joint_frac", "coll_frac", "min_w", "cost_sum", "ep_len"]


def read_train_csv(path):
    steps, vals = [], []
    with open(path) as f:
        for row in csv.DictReader(f):
            steps.append(int(float(row["step"])))
            vals.append(float(row["value"]))
    return np.array(steps), np.array(vals)


def find_train_file(arm_folder, seed, tag):
    pat = os.path.join(TRAIN, arm_folder, f"seed_{seed}", f"*__{tag}.csv")
    hits = glob.glob(pat)
    if len(hits) != 1:
        raise SystemExit(f"expected 1 training file for {pat}, got {len(hits)}")
    return hits[0]


def build_training():
    out = {}
    for arm, folder in ARM_FOLDER.items():
        out[arm] = {}
        for metric, tag in TRAIN_METRICS.items():
            series, steps_ref = [], None
            for seed in SEEDS:
                steps, vals = read_train_csv(find_train_file(folder, seed, tag))
                if steps_ref is None:
                    steps_ref = steps
                elif len(steps) != len(steps_ref):
                    raise SystemExit(f"length mismatch {arm} {metric} seed {seed}")
                series.append(vals)
            arr = np.vstack(series)
            n_tail = max(1, int(arr.shape[1] * 0.10))
            tail_per_seed = arr[:, -n_tail:].mean(axis=1)
            out[arm][metric] = {
                "steps": steps_ref.tolist(),
                "mean": arr.mean(axis=0).tolist(),
                "std": arr.std(axis=0).tolist(),
                "per_seed_tail": {str(s): float(v) for s, v in zip(SEEDS, tail_per_seed)},
                "tail_mean": float(tail_per_seed.mean()),
                "tail_std": float(tail_per_seed.std()),
            }
        # Full per-seed series for mean_episode_cost only. fig_seed_variance draws every seed
        # individually, which is where the seed-spread evidence lives now that the +/- std bands
        # have been removed from the curve figures. Kept to one metric to bound the file size.
        series = []
        for seed in SEEDS:
            _, vals = read_train_csv(find_train_file(folder, seed, TRAIN_METRICS["mean_episode_cost"]))
            series.append(vals)
        out[arm]["_seed_series"] = {str(s): v.tolist() for s, v in zip(SEEDS, series)}

        # Full per-seed lambda series. Section 4.7 quotes individual peak values and the
        # lambda_traj figure draws every seed, so the mean is not sufficient here.
        lam = []
        for seed in SEEDS:
            _, vals = read_train_csv(find_train_file(folder, seed, TRAIN_METRICS["cost_lambda"]))
            lam.append(vals)
        out[arm]["_lambda_series"] = {str(s): v.tolist() for s, v in zip(SEEDS, lam)}
    return out


def load_eval_seed_episodes(folder, prefix, seed):
    cols = None
    for es in EVAL_SEEDS:
        path = os.path.join(EVAL, folder, f"seed_{seed}", f"{prefix}_s{seed}_seed{es}.csv")
        if not os.path.exists(path):
            raise SystemExit(f"missing eval file {path}")
        with open(path) as f:
            rows = list(csv.DictReader(f))
        if cols is None:
            cols = {k: [] for k in rows[0].keys()}
        for row in rows:
            for k, v in row.items():
                cols[k].append(float(v))
    return {k: np.array(v) for k, v in cols.items()}, len(cols["ep_len"])


def build_evaluation():
    out = {}
    for arm, folder in ARM_FOLDER.items():
        pooled = {k: [] for k in EVAL_POOL_COLS}
        per_seed_cost_mean = {}
        n_total = 0
        for seed in SEEDS:
            data, n = load_eval_seed_episodes(folder, ARM_PREFIX[arm], seed)
            n_total += n
            per_seed_cost_mean[str(seed)] = float(data["cost_sum"].mean())
            for k in pooled:
                pooled[k].append(data[k])
        for k in pooled:
            pooled[k] = np.concatenate(pooled[k])

        gd, cost, minw = pooled["goal_dist_final"], pooled["cost_sum"], pooled["min_w"]
        out[arm] = {
            "n_episodes": n_total,
            "lift_rel_pct": float(pooled["lift_rel"].mean() * 100),
            "lift_rel_ever_pct": float(pooled["lift_rel_ever"].mean() * 100),
            "goal_reach_1cm_pct": float((gd < 0.01).mean() * 100),
            "goal_reach_2cm_pct": float((gd < 0.02).mean() * 100),
            "goal_reach_5cm_pct": float((gd < 0.05).mean() * 100),
            "goal_dist_mean": float(gd.mean()),
            "goal_dist_median": float(np.median(gd)),
            "goal_dist_p90": float(np.percentile(gd, 90)),
            "goal_dist_max": float(gd.max()),
            "sing_frac_mean_of_steps_pct": float(pooled["sing_frac"].mean() * 100),
            "joint_frac_mean_of_steps_pct": float(pooled["joint_frac"].mean() * 100),
            "coll_frac_mean_of_steps_pct": float(pooled["coll_frac"].mean() * 100),
            "sing_touched_pct": float((pooled["sing_frac"] > 0).mean() * 100),
            "joint_touched_pct": float((pooled["joint_frac"] > 0).mean() * 100),
            "coll_touched_pct": float((pooled["coll_frac"] > 0).mean() * 100),
            "true_singularity_pct": float((minw < 1e-4).mean() * 100),
            "true_singularity_n": int((minw < 1e-4).sum()),
            "mean_episode_min_manip": float(minw.mean()),
            "worst_episode_min_manip": float(minw.min()),
            "cost_mean": float(cost.mean()),
            "cost_median": float(np.median(cost)),
            "cost_p90": float(np.percentile(cost, 90)),
            "cost_max": float(cost.max()),
            "cost_std_across_episodes": float(cost.std()),
            "per_seed_cost_mean": per_seed_cost_mean,
        }
    return out


def main():
    summary = {
        "scope": {"seeds": SEEDS, "arms": list(ARM_FOLDER.keys()),
                   "arm_folder": ARM_FOLDER, "eval_seeds": EVAL_SEEDS,
                   "note": "ctrl is labeled 'PPO (baseline)' in thesis prose/figures"},
        "training": build_training(),
        "evaluation": build_evaluation(),
    }
    out_path = os.path.join(RESULTS, "final_results_summary.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print("wrote", out_path)

    for arm in ARM_FOLDER:
        t = summary["training"][arm]
        e = summary["evaluation"][arm]
        print(f"{arm:8s} train: reward={t['mean_reward']['tail_mean']:7.2f}  "
              f"cost={t['mean_episode_cost']['tail_mean']:7.2f}  "
              f"lambda={t['cost_lambda']['tail_mean']:.4f}   |   "
              f"eval: n={e['n_episodes']}  lift={e['lift_rel_pct']:.2f}%  "
              f"reach1cm={e['goal_reach_1cm_pct']:.2f}%  cost={e['cost_mean']:.2f}  "
              f"true_sing={e['true_singularity_pct']:.3f}%  joint_touched={e['joint_touched_pct']:.2f}%")


if __name__ == "__main__":
    main()
