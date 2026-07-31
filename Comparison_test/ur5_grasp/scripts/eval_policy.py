# Copyright (c) 2022-2025, The Isaac Lab Project Developers.
# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Evaluate a FROZEN policy: task success AND safety-constraint violations.

Supersedes `eval_success.py` (Day 22). That script had three problems, all of which
this one fixes. Read this list before changing anything here.

  1. IT MEASURED NO SAFETY. The singularity / joint-limit violation numbers in
     results/LAYER1_RESULTS_3seed.md were tail-means of the TRAINING TensorBoard
     scalars — i.e. measured on a *stochastic, still-learning* policy averaged over the
     final 10% of iterations, with exploration noise ON. They are not a property of the
     final policy. This script counts violations during evaluation, on the deterministic
     frozen policy, which is what the thesis actually claims.

  2. GOAL-REACH WAS A SINGLE HARD THRESHOLD (5 cm) on a quantity with almost no
     within-policy spread, so it saturated at exactly 0.00% or exactly 100.00% and could
     not distinguish "missed by 1 cm" from "missed by 50 cm". This script reports the
     full object-goal DISTANCE distribution (mean / median / p90 / max) alongside success
     at 2 / 5 / 10 cm.

  3. IT ONLY READ rsl_rl CHECKPOINTS. skrl runs (the PPO bridge, and SAC) could not be
     scored at all. This script loads both.

PROTOCOL (set by Touhid, 2026-07-31 / Day 23 — these are the reported numbers):
  num_envs = 128, episodes = 1000, eval seeds 101 / 102 / 103 (disjoint from training 1/2/3),
  goal-reach bound = 1 cm,
  lift success = cube reaches at least 50% of the COMMANDED GOAL HEIGHT for that episode.

The lift rule is the important change. `--min_height 0.04` (Isaac Lab's own `object_is_lifted`
threshold) sits ~2 cm above the cube's resting height, so almost any policy clears it and the
Day-22 table read 100% for everything. The goal z is resampled per episode over 0.25-0.50 m, so
`--lift_frac 0.5` demands roughly 12.5-25 cm of real lift, scaled to what that episode actually
asked for. Both are reported; the FRACTIONAL one is the headline, the absolute one is kept only
so the new table can be lined up against the old one.

Metrics recorded per episode (one CSV row each, so the distribution is reconstructable):
  * goal_dist_final   -- ||object - commanded goal||, world frame, at the last step
  * goal_z            -- commanded goal height (world z) for that episode
  * lift_rel          -- object z >= --lift_frac * goal_z at the last step   <- HEADLINE
  * lift_abs          -- object z >  --min_height at the last step (legacy, for continuity)
  * lift_max_z        -- highest object z reached during the episode
  * sing_frac         -- fraction of steps with manipulability w < MANIP_FLOOR
  * joint_frac        -- fraction of steps with any arm joint inside JOINT_LIMIT_MARGIN
  * coll_frac         -- fraction of steps with a monitored link below COLLISION_Z_FLOOR
  * sing_any / joint_any / coll_any -- did the episode violate at all (0/1)
  * min_w             -- lowest manipulability seen in the episode
  * cost_sum          -- undiscounted episodic safety cost, comparable to cost_limit=25
  * ep_len            -- steps, so early object_dropping terminations are visible

Run one (checkpoint, eval-seed) pair per process. `run_eval_policy.sh` does the sweep.

    cd ~/Abdur_Rabbi_THESIS/Comparison_test
    ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/eval_policy.py \
        --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 128 --episodes 1000 \
        --seed 101 --backend rsl_rl --agent rsl_rl_cppo_cfg_entry_point \
        --checkpoint logs/rsl_rl/ur5e_lift_cppo/<run>/model_1499.pt --label cppo_s1

STANDING RULE (five victims so far): this script writes a FLUSHED report file. Never
pipe it through `tee` — piping is what causes the block buffering that
`simulation_app.close()` then discards.
"""

"""Launch Isaac Sim Simulator first."""

import argparse
import os
import sys

from isaaclab.app import AppLauncher

# --- TOUHID: make external package + Isaac Lab's cli_args importable -------------
# Search upward for whichever ancestor actually contains IsaacLab/isaaclab.sh, rather
# than hardcoding a directory count (same fix as eval_success.py / train_skrl.py).
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))  # Comparison_test/


def _find_isaaclab_root(start_dir: str) -> str:
    d = start_dir
    for _ in range(8):
        candidate = os.path.join(d, "IsaacLab", "isaaclab.sh")
        if os.path.isfile(candidate):
            return os.path.join(d, "IsaacLab")
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    raise RuntimeError(
        f"Could not find an IsaacLab/ install by walking up from {start_dir}. "
        "Expected IsaacLab/isaaclab.sh in some ancestor directory."
    )


_CLI_ARGS_DIR = os.path.join(_find_isaaclab_root(_HERE), "scripts", "reinforcement_learning", "rsl_rl")
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
if _CLI_ARGS_DIR not in sys.path:
    sys.path.append(_CLI_ARGS_DIR)
# --------------------------------------------------------------------------------

import cli_args  # isort: skip

parser = argparse.ArgumentParser(description="Evaluate task success AND safety violations for a frozen policy.")
parser.add_argument("--num_envs", type=int, default=128, help="Parallel envs used to collect episodes.")
parser.add_argument("--task", type=str, default="Isaac-Lift-Cube-UR5e-v0", help="Name of the task.")
parser.add_argument("--episodes", type=int, default=1000, help="Completed episodes to score (per eval seed).")
parser.add_argument(
    "--seed",
    type=int,
    default=101,
    help="EVAL seed: fixes the cube spawns. Deliberately disjoint from the training seeds "
    "(1/2/3) so a seed number can never be mistaken for a policy pairing. Keep it >= 100.",
)
parser.add_argument(
    "--backend",
    type=str,
    default="rsl_rl",
    choices=["rsl_rl", "skrl"],
    help="Which library wrote the checkpoint. rsl_rl -> model_*.pt, skrl -> agent_*.pt.",
)
parser.add_argument(
    "--agent",
    type=str,
    default="rsl_rl_cfg_entry_point",
    help="Agent config entry point. rsl_rl_cfg_entry_point | rsl_rl_cppo_cfg_entry_point | skrl_cfg_entry_point | ...",
)
# NOTE: --checkpoint is NOT declared here. `cli_args.add_rsl_rl_args(parser)` at the bottom of
# this block already declares it, and declaring it twice raises argparse.ArgumentError at
# IMPORT time — before the report file below is even opened, so the run dies silently with no
# report and no traceback anywhere. That is exactly what happened on the first sweep (Day 23,
# 18/18 "failed" with zero output). Before adding ANY flag here, check it against:
#   cli_args.add_rsl_rl_args -> --experiment_name --run_name --resume --load_run --checkpoint
#                               --logger --log_project_name
#   AppLauncher.add_app_launcher_args -> --device --headless --enable_cameras --livestream
#                               --experience --kit_args --rendering_mode --verbose --info
#                               --cpu --xr --anim_recording_*
parser.add_argument("--label", type=str, default=None, help="Short name for this run in the report (e.g. cppo_s1).")
# --- task-success thresholds ---
parser.add_argument(
    "--lift_frac",
    type=float,
    default=0.5,
    help="HEADLINE lift rule: cube must reach this fraction of the episode's COMMANDED goal height.",
)
parser.add_argument(
    "--min_height",
    type=float,
    default=0.04,
    help="Legacy absolute lift threshold (m, world z), Isaac Lab's own. Reported alongside, not the headline.",
)
parser.add_argument(
    "--goal_tol",
    type=float,
    default=0.01,
    help="HEADLINE goal-reach bound (m). Default 1 cm.",
)
parser.add_argument(
    "--goal_tols_extra",
    type=str,
    default="0.02,0.05",
    help="Extra goal-reach tolerances (m) reported as context, so a near-miss is distinguishable "
    "from a total failure. The headline stays --goal_tol.",
)
# --- reporting ---
parser.add_argument("--report", type=str, default=None, help="Report file to APPEND to.")
parser.add_argument("--csv", type=str, default=None, help="Summary CSV (one row per run) to APPEND to.")
parser.add_argument(
    "--episode_csv",
    type=str,
    default=None,
    help="Per-episode CSV. Default: ur5_grasp/tools/eval_episodes/<label>_seed<seed>.csv. "
    "This is what makes the DISTRIBUTION reconstructable — do not skip it.",
)
cli_args.add_rsl_rl_args(parser)
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()

# --checkpoint comes from cli_args, which makes it optional. This script cannot do anything
# without one, so enforce it here rather than failing 40 s later inside Isaac.
if not args_cli.checkpoint:
    parser.error("--checkpoint is required (it is declared by cli_args.add_rsl_rl_args, not here).")

sys.argv = [sys.argv[0]] + hydra_args

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import statistics

import gymnasium as gym
import torch

from isaaclab.envs import DirectMARLEnv, DirectMARLEnvCfg, DirectRLEnvCfg, ManagerBasedRLEnvCfg, multi_agent_to_single_agent
from isaaclab.utils.math import combine_frame_transforms

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils.hydra import hydra_task_config

import ur5_grasp.tasks  # noqa: F401  # TOUHID: registers Isaac-Lift-Cube-UR5e-v0
from ur5_grasp.safe_rl.costs import SafetyCostComputer

# ---------------------------------------------------------------------------------------
# Flushed report machinery. Anchored to THIS FILE so output lands in ur5_grasp/tools/
# regardless of cwd. print() alone does not survive simulation_app.close().
# ---------------------------------------------------------------------------------------
_TOOLS_DIR = os.path.normpath(os.path.join(_HERE, "..", "tools"))
_REPORT_PATH = args_cli.report or os.path.join(_TOOLS_DIR, "eval_policy_report.txt")
_CSV_PATH = args_cli.csv or os.path.join(_TOOLS_DIR, "eval_policy_results.csv")
_EP_CSV_DIR = os.path.join(_TOOLS_DIR, "eval_episodes")
_FH = None


def log(msg: str = "") -> None:
    """print + write + flush. Every line of output goes through here."""
    print(msg)
    if _FH is not None:
        _FH.write(msg + "\n")
        _FH.flush()


def pct(x: float) -> str:
    return f"{100.0 * x:6.2f}%"


def quantile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return float("nan")
    idx = min(len(sorted_vals) - 1, max(0, int(round(q * (len(sorted_vals) - 1)))))
    return sorted_vals[idx]


@hydra_task_config(args_cli.task, args_cli.agent)
def main(env_cfg: ManagerBasedRLEnvCfg | DirectRLEnvCfg | DirectMARLEnvCfg, agent_cfg):
    """Score one frozen checkpoint on one eval seed."""
    task_name = args_cli.task.split(":")[-1]
    # headline tolerance first; extras follow as context and are de-duplicated
    goal_tols = [args_cli.goal_tol] + [
        float(t) for t in args_cli.goal_tols_extra.split(",") if t.strip() and float(t) != args_cli.goal_tol
    ]

    # ---- env config -------------------------------------------------------------------
    # The EVAL seed is deliberately NOT the training seed: every policy must be scored on
    # identical cube spawns, otherwise seed-to-seed spread mixes policy quality with luck
    # of the draw. The training seed is recovered from the checkpoint path in the CSV.
    env_cfg.scene.num_envs = args_cli.num_envs
    env_cfg.seed = args_cli.seed
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device
    # Observation noise is a TRAINING-time augmentation. Leaving it on would mean the
    # reported number is "success under sensor noise", which is a different claim.
    if hasattr(env_cfg.observations, "policy"):
        env_cfg.observations.policy.enable_corruption = False

    log("")
    log("=" * 78)
    log(f"EVAL  label={args_cli.label or '(none)'}  backend={args_cli.backend}  eval_seed={args_cli.seed}")
    log("=" * 78)
    log(f"[progress] task       : {task_name}")
    log(f"[progress] checkpoint : {args_cli.checkpoint}")
    log(f"[progress] num_envs={env_cfg.scene.num_envs}  episodes={args_cli.episodes}  agent={args_cli.agent}")
    log(
        f"[progress] success rules: lift >= {args_cli.lift_frac:.2f} x commanded goal height  |  "
        f"goal-reach < {args_cli.goal_tol*100:.1f} cm  (extras: "
        + ", ".join(f"{t*100:.1f} cm" for t in goal_tols[1:])
        + ")"
    )
    log("[progress] building scene (gym.make) ...")

    env = gym.make(args_cli.task, cfg=env_cfg, render_mode=None)
    if isinstance(env.unwrapped, DirectMARLEnv):
        env = multi_agent_to_single_agent(env)

    # ---- policy: rsl_rl or skrl -------------------------------------------------------
    if args_cli.backend == "rsl_rl":
        from rsl_rl.runners import OnPolicyRunner

        from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper

        from ur5_grasp.safe_rl.lagrangian_runner import LagrangianRunner

        agent_cfg = cli_args.update_rsl_rl_cfg(agent_cfg, args_cli)
        env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
        if agent_cfg.class_name == "OnPolicyRunner":
            runner = OnPolicyRunner(env, agent_cfg.to_dict(), log_dir=None, device=agent_cfg.device)
        elif agent_cfg.class_name == "LagrangianRunner":
            runner = LagrangianRunner(env, agent_cfg.to_dict(), log_dir=None, device=agent_cfg.device)
        else:
            raise ValueError(f"Unsupported runner class: {agent_cfg.class_name}")
        runner.load(os.path.abspath(args_cli.checkpoint))
        _inference = runner.get_inference_policy(device=env.unwrapped.device)

        def act(obs):
            return _inference(obs)

        def step(actions):
            obs_, _, dones_, _ = env.step(actions)
            return obs_, dones_

        def initial_obs():
            return env.get_observations()

    else:  # skrl
        from skrl.utils.runner.torch import Runner

        from isaaclab_rl.skrl import SkrlVecEnvWrapper

        # agent_cfg is the parsed yaml dict for skrl.
        agent_cfg["trainer"]["close_environment_at_exit"] = False
        agent_cfg["agent"]["experiment"]["write_interval"] = 0  # no TensorBoard from an eval
        agent_cfg["agent"]["experiment"]["checkpoint_interval"] = 0  # no checkpoints from an eval

        # --- OFF-POLICY EVAL GUARDS (added Day 23, before SAC's first eval) -------------
        # 1. random_timesteps WOULD SILENTLY EVALUATE RANDOM ACTIONS.
        #    skrl's off-policy agents open act() with
        #        if timestep < self._random_timesteps: return self.policy.random_act(...)
        #    This script calls act(obs, timestep=0, timesteps=0), and skrl_sac_cfg.yaml sets
        #    random_timesteps = 1000 for exploration during TRAINING. 0 < 1000, so every
        #    evaluation action would be drawn uniformly from the action space — and it would
        #    not look like a crash, it would look like SAC scoring ~0% and "confirming" that
        #    off-policy fails on this task. random_act also returns an empty outputs dict, so
        #    the "mean_actions" lookup below silently falls back to the random sample.
        #    Zero it here rather than in the yaml: the yaml value is correct for training.
        # 2. The replay buffer is dead weight in an eval (1.02M transitions for SAC) and is
        #    never sampled, since update() is only called from post_interaction().
        if "random_timesteps" in agent_cfg["agent"]:
            agent_cfg["agent"]["random_timesteps"] = 0
        if "learning_starts" in agent_cfg["agent"]:
            agent_cfg["agent"]["learning_starts"] = 10**9  # never update during an eval
        if "memory" in agent_cfg and agent_cfg["memory"].get("memory_size", -1) > 1:
            agent_cfg["memory"]["memory_size"] = 16
        env = SkrlVecEnvWrapper(env, ml_framework="torch")
        runner = Runner(env, agent_cfg)
        runner.agent.load(os.path.abspath(args_cli.checkpoint))
        runner.agent.set_running_mode("eval")  # deterministic: mean action, no exploration

        def act(obs):
            outputs = runner.agent.act(obs, timestep=0, timesteps=0)
            # skrl returns (sampled, log_prob, outputs_dict); "mean_actions" is the
            # deterministic action. Same selection as IsaacLab's own skrl play.py.
            return outputs[-1].get("mean_actions", outputs[0])

        def step(actions):
            obs_, _, terminated_, truncated_, _ = env.step(actions)
            return obs_, (terminated_ | truncated_).flatten()

        def initial_obs():
            obs_, _ = env.reset()
            return obs_

    base = env.unwrapped
    device = base.device
    obj = base.scene["object"]
    robot = base.scene["robot"]

    # ---- safety instrumentation -------------------------------------------------------
    # Built here rather than reused from base._cost_computer because compute() returns
    # batch MEANS only; episode-level counting needs the per-env quantities, which the
    # public helpers below expose. Thresholds are read off the env class so this can never
    # silently disagree with what training constrained.
    cost_computer = SafetyCostComputer(
        robot=robot,
        arm_joint_names=base.ARM_JOINTS,
        ee_body_name=base.EE_BODY,
        monitored_body_names=base.MONITORED_BODIES,
        z_floor=base.COLLISION_Z_FLOOR,
        joint_margin=base.JOINT_LIMIT_MARGIN,
        manip_floor=base.MANIP_FLOOR,
        w_collision=base.W_COLLISION,
        w_joint=base.W_JOINT,
        w_manip=base.W_MANIP,
    )
    log(
        f"[progress] thresholds: MANIP_FLOOR={base.MANIP_FLOOR}  "
        f"JOINT_LIMIT_MARGIN={base.JOINT_LIMIT_MARGIN}  COLLISION_Z_FLOOR={base.COLLISION_Z_FLOOR}"
    )

    n = env_cfg.scene.num_envs
    z = lambda: torch.zeros(n, device=device)  # noqa: E731
    ep_len, sing_ct, joint_ct, coll_ct, cost_sum = z(), z(), z(), z(), z()
    min_w = torch.full((n,), float("inf"), device=device)
    max_z = torch.full((n,), -float("inf"), device=device)

    rows: list[tuple] = []  # one per completed episode

    obs = initial_obs()
    log(f"[progress] policy loaded, scene up. Scoring {args_cli.episodes} episodes ...")
    next_report = max(1, args_cli.episodes // 10)

    while len(rows) < args_cli.episodes:
        with torch.inference_mode():
            actions = act(obs)

            # --- measure the PRE-step state -------------------------------------------
            # ManagerBasedRLEnv resets done envs INSIDE step(), so the post-step state of a
            # terminating env is already the fresh reset. The last observable state of an
            # episode is therefore the pre-step one. For a 250-step episode this is an
            # off-by-one of 20 ms; it is documented, not hidden.
            w = cost_computer.manipulability()
            jd = cost_computer.joint_limit_min_distance()
            zmin = cost_computer.min_link_height()

            # EVERY accumulator below must be updated IN PLACE (`+=`, or `out=`). Never
            # rebind one, i.e. never write `min_w = torch.minimum(min_w, w)`. Rebinding
            # inside `torch.inference_mode()` replaces the normal tensor with an INFERENCE
            # tensor, and the episode-reset lines further down then die with
            #   "Inplace update to inference tensor outside InferenceMode is not allowed"
            # — thousands of steps later, after the first episodes have already completed.
            # (Day 23: this is exactly how the first successful launch crashed.) Writing
            # INTO a normal tensor from inside inference mode is fine, which is why the
            # `+=` lines were always safe; it is the rebinding that is not.
            sing_ct += (w < base.MANIP_FLOOR).float()
            joint_ct += (jd < base.JOINT_LIMIT_MARGIN).float()
            coll_ct += (zmin < base.COLLISION_Z_FLOOR).float()
            min_w.copy_(torch.minimum(min_w, w))
            ep_len += 1.0

            obj_pos_w = obj.data.root_pos_w
            max_z.copy_(torch.maximum(max_z, obj_pos_w[:, 2]))
            des_pos_w, _ = combine_frame_transforms(
                robot.data.root_pos_w,
                robot.data.root_quat_w,
                base.command_manager.get_command("object_pose")[:, :3],
            )
            goal_dist = torch.norm(des_pos_w - obj_pos_w, dim=1)
            obj_z = obj_pos_w[:, 2].clone()
            # Commanded goal HEIGHT for this episode (world z). The pose command is
            # resampled once per episode (resampling_time_range = (5.0, 5.0) = the whole
            # episode), so this is constant within an episode and the value captured on the
            # final step is the value that was in force throughout.
            goal_z = des_pos_w[:, 2].clone()

            obs, dones = step(actions)

            # extras["cost"] is the per-env aggregate cost the Lagrangian actually
            # constrains; summing it undiscounted over an episode is exactly the quantity
            # cost_limit=25 bounds. Published by UR5eCubeLiftEnv._apply_cost after step().
            c = base.extras.get("cost")
            if c is not None:
                cost_sum += c.detach().float()

        done_ids = torch.nonzero(dones).flatten()
        if done_ids.numel() > 0:
            L = ep_len[done_ids].clamp(min=1.0)
            gz = goal_z[done_ids]
            lift_bar = args_cli.lift_frac * gz  # per-episode lift bar, scaled to the command
            batch = torch.stack(
                [
                    goal_dist[done_ids],
                    obj_z[done_ids],
                    max_z[done_ids],
                    gz,
                    (obj_z[done_ids] >= lift_bar).float(),        # lift_rel  (HEADLINE)
                    (max_z[done_ids] >= lift_bar).float(),        # lift_rel_ever
                    (obj_z[done_ids] > args_cli.min_height).float(),  # lift_abs (legacy)
                    sing_ct[done_ids] / L,
                    joint_ct[done_ids] / L,
                    coll_ct[done_ids] / L,
                    min_w[done_ids],
                    cost_sum[done_ids],
                    ep_len[done_ids],
                ],
                dim=1,
            ).cpu().tolist()
            rows.extend(batch)

            ep_len[done_ids] = 0.0
            sing_ct[done_ids] = 0.0
            joint_ct[done_ids] = 0.0
            coll_ct[done_ids] = 0.0
            cost_sum[done_ids] = 0.0
            min_w[done_ids] = float("inf")
            max_z[done_ids] = -float("inf")

            if len(rows) >= next_report:
                log(f"[progress] {len(rows)} / {args_cli.episodes} episodes")
                next_report += max(1, args_cli.episodes // 10)

    rows = rows[: args_cli.episodes]  # trim the overshoot from the last simultaneous batch
    m = len(rows)

    # ---- per-episode CSV: the distribution, not just its summary ----------------------
    os.makedirs(_EP_CSV_DIR, exist_ok=True)
    ep_csv = args_cli.episode_csv or os.path.join(
        _EP_CSV_DIR, f"{args_cli.label or 'run'}_seed{args_cli.seed}.csv"
    )
    with open(ep_csv, "w") as fh:
        fh.write(
            "goal_dist_final,obj_z_final,lift_max_z,goal_z,lift_rel,lift_rel_ever,lift_abs,"
            "sing_frac,joint_frac,coll_frac,min_w,cost_sum,ep_len\n"
        )
        for r in rows:
            fh.write(",".join(f"{v:.6f}" for v in r) + "\n")

    # ---- summarise --------------------------------------------------------------------
    # Column order must match the header above.
    (D, ZF, ZMAX, GZ, LREL, LRELE, LABS, SING, JNT, COLL, MINW, COST, LEN) = range(13)
    col = lambda k: [r[k] for r in rows]  # noqa: E731
    dists = sorted(col(D))
    lift_rel = statistics.fmean(col(LREL))
    lift_rel_ever = statistics.fmean(col(LRELE))
    lift_abs = statistics.fmean(col(LABS))
    # Goal-reach is gated on the HEADLINE lift rule, but be honest about what that buys:
    # at these tolerances the gate is REDUNDANT. If the cube is within 1 cm of a goal at
    # height h, its own height is >= h - 0.01, which always clears 0.5*h for h >= 0.02.
    # The gate is kept because it costs nothing and stops a future looser tolerance from
    # silently admitting a cube dragged along the table. The lift number's real job is as
    # a STANDALONE metric: how often the policy gets the cube meaningfully up even when it
    # misses the goal. Do not present the gate as if it were doing the discriminating.
    goal_rates = {t: sum(1 for r in rows if r[D] < t and r[LREL] > 0.5) / m for t in goal_tols}
    sing_frac = statistics.fmean(col(SING))
    joint_frac = statistics.fmean(col(JNT))
    coll_frac = statistics.fmean(col(COLL))
    sing_any = sum(1 for v in col(SING) if v > 0.0) / m
    joint_any = sum(1 for v in col(JNT) if v > 0.0) / m
    coll_any = sum(1 for v in col(COLL) if v > 0.0) / m
    min_w_mean = statistics.fmean(col(MINW))
    min_w_worst = min(col(MINW))
    cost_mean = statistics.fmean(col(COST))
    cost_p90 = quantile(sorted(col(COST)), 0.90)
    len_mean = statistics.fmean(col(LEN))
    goal_z_mean = statistics.fmean(col(GZ))

    log("")
    log("-" * 78)
    log(f"  Label / eval seed  : {args_cli.label or '(none)'}  /  {args_cli.seed}")
    log(f"  Checkpoint         : {args_cli.checkpoint}")
    log(f"  Episodes scored    : {m}   (mean length {len_mean:.1f} steps)")
    log("  --- TASK ---------------------------------------------------------------")
    log(f"  LIFT   >= {args_cli.lift_frac:.2f} x goal height : {pct(lift_rel)}   <- headline")
    log(f"         ... reached at any point   : {pct(lift_rel_ever)}")
    log(f"         ... legacy z > {args_cli.min_height:.3f} m      : {pct(lift_abs)}   (Day-22 definition)")
    log(f"         mean commanded goal height : {goal_z_mean:.3f} m  (bar = {args_cli.lift_frac*goal_z_mean:.3f} m)")
    for i, t in enumerate(goal_tols):
        tag = "   <- headline" if i == 0 else ""
        log(f"  GOAL-REACH < {t*100:5.1f} cm (and lifted) : {pct(goal_rates[t])}{tag}")
    log(
        f"  Goal distance (m)          : mean {statistics.fmean(dists):.4f}  "
        f"median {quantile(dists, 0.5):.4f}  p90 {quantile(dists, 0.9):.4f}  max {dists[-1]:.4f}"
    )
    log("  --- SAFETY (frozen policy, measured HERE, not from training logs) ------")
    log(f"  Singularity  : {pct(sing_frac)} of steps  |  {pct(sing_any)} of episodes touched it")
    log(f"  Joint limit  : {pct(joint_frac)} of steps  |  {pct(joint_any)} of episodes touched it")
    log(f"  Collision    : {pct(coll_frac)} of steps  |  {pct(coll_any)} of episodes touched it")
    log(f"  Manipulability w : mean-of-episode-min {min_w_mean:.4f}   worst {min_w_worst:.4f}   floor {base.MANIP_FLOOR}")
    log(f"  Episodic cost    : mean {cost_mean:.2f}   p90 {cost_p90:.2f}   (cost_limit = 25)")
    log("-" * 78)
    log(f"  [per-episode csv: {ep_csv}]")

    # ---- machine-readable summary row -------------------------------------------------
    header = (
        "label,eval_seed,backend,task,episodes,ep_len_mean,lift_frac,goal_z_mean,"
        "lift_rel_pct,lift_rel_ever_pct,lift_abs_pct,"
        + ",".join(f"goal_{round(t*100)}cm_pct" for t in goal_tols)
        + ",goal_dist_mean,goal_dist_median,goal_dist_p90,goal_dist_max,"
        "sing_step_pct,joint_step_pct,coll_step_pct,"
        "sing_ep_pct,joint_ep_pct,coll_ep_pct,"
        "min_w_mean,min_w_worst,cost_mean,cost_p90,checkpoint\n"
    )
    write_header = not os.path.exists(_CSV_PATH)
    with open(_CSV_PATH, "a") as fh:
        if write_header:
            fh.write(header)
        fh.write(
            f"{args_cli.label or ''},{args_cli.seed},{args_cli.backend},{task_name},{m},{len_mean:.2f},"
            f"{args_cli.lift_frac:.2f},{goal_z_mean:.4f},"
            f"{100*lift_rel:.2f},{100*lift_rel_ever:.2f},{100*lift_abs:.2f},"
            + ",".join(f"{100*goal_rates[t]:.2f}" for t in goal_tols)
            + f",{statistics.fmean(dists):.4f},{quantile(dists,0.5):.4f},{quantile(dists,0.9):.4f},{dists[-1]:.4f},"
            f"{100*sing_frac:.2f},{100*joint_frac:.2f},{100*coll_frac:.2f},"
            f"{100*sing_any:.2f},{100*joint_any:.2f},{100*coll_any:.2f},"
            f"{min_w_mean:.4f},{min_w_worst:.4f},{cost_mean:.2f},{cost_p90:.2f},"
            f"{os.path.abspath(args_cli.checkpoint)}\n"
        )
    log(f"  [summary row appended to {_CSV_PATH}]")

    env.close()


if __name__ == "__main__":
    os.makedirs(_TOOLS_DIR, exist_ok=True)
    _FH = open(_REPORT_PATH, "a")  # APPEND: a whole sweep accumulates into one file
    try:
        main()
    except Exception:  # noqa: BLE001 — the traceback must land IN the report
        import traceback

        log("")
        log("UNHANDLED EXCEPTION:")
        log(traceback.format_exc())
        raise
    finally:
        log(f"[report appended to {_REPORT_PATH}]")
        _FH.close()
        simulation_app.close()
