# Copyright (c) 2022-2025, The Isaac Lab Project Developers.
# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Evaluate the success rate of a trained UR5e grasp checkpoint (RSL-RL).

There is no success scalar logged during training, so this replays a checkpoint over
many episodes (headless) and reports two rates, using the env's OWN lift/goal math:

  * lift success   -- object raised above `--min_height` (env default 0.04 m).
  * goal-reach      -- lifted AND object within `--success_tol` m of the commanded goal.

Run BOTH agents and compare (run from ~/Abdur_Rabbi_THESIS/IsaacLab):

    # cPPO checkpoint
    ./isaaclab.sh -p ../ur5_grasp/scripts/eval_success.py \
        --task Isaac-Lift-Cube-UR5e-Play-v0 --agent rsl_rl_cppo_cfg_entry_point \
        --headless --num_envs 64 --episodes 300

    # PPO baseline checkpoint
    ./isaaclab.sh -p ../ur5_grasp/scripts/eval_success.py \
        --task Isaac-Lift-Cube-UR5e-Play-v0 \
        --headless --num_envs 64 --episodes 300
"""

"""Launch Isaac Sim Simulator first."""

import argparse
import os
import sys

from isaaclab.app import AppLauncher

# --- TOUHID: make external package + Isaac Lab's cli_args importable -------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
# Comparison-test copy sits one directory DEEPER than the main folder's ur5_grasp/,
# so "two levels up from this script" (_REPO_ROOT) no longer lands next to IsaacLab/ --
# it lands in "Comparison_test/" instead (IsaacLab/ is one level further up, at the
# project root). Rather than hardcode a directory count that breaks again if this
# package ever moves, search upward for whichever ancestor actually contains
# IsaacLab/isaaclab.sh (same "search by identity, not by guessed depth" fix as
# make_ur5e_simple_gripper_usd.py used for the wrist_3_link mount prim).
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

parser = argparse.ArgumentParser(description="Evaluate success rate of an RSL-RL checkpoint.")
parser.add_argument("--num_envs", type=int, default=64, help="Number of parallel environments.")
parser.add_argument("--task", type=str, default=None, help="Name of the task.")
parser.add_argument(
    "--agent", type=str, default="rsl_rl_cfg_entry_point", help="Name of the RL agent configuration entry point."
)
parser.add_argument("--seed", type=int, default=None, help="Seed used for the environment.")
parser.add_argument("--episodes", type=int, default=300, help="Number of completed episodes to score over.")
parser.add_argument("--min_height", type=float, default=0.04, help="Lift-success height threshold (m).")
parser.add_argument("--success_tol", type=float, default=0.05, help="Goal-reach distance tolerance (m).")
# TOUHID (Day 22): this script had 9 print() calls and wrote NO file, so its result could not
# survive `simulation_app.close()` — the same trap that has now cost this project five separate
# results. It APPENDS to one report so a whole sweep of checkpoints accumulates in a single
# readable file, plus a CSV row per run for the results table.
parser.add_argument(
    "--report",
    type=str,
    default=None,
    help="Report file to APPEND to. Default: ur5_grasp/tools/eval_success_report.txt",
)
parser.add_argument(
    "--label", type=str, default=None, help="Short name for this run in the report (e.g. ppo_s1)."
)
cli_args.add_rsl_rl_args(parser)
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()

sys.argv = [sys.argv[0]] + hydra_args

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import gymnasium as gym
import torch

from rsl_rl.runners import DistillationRunner, OnPolicyRunner

from ur5_grasp.safe_rl.lagrangian_runner import LagrangianRunner  # TOUHID: cPPO runner

from isaaclab.envs import (
    DirectMARLEnv,
    DirectMARLEnvCfg,
    DirectRLEnvCfg,
    ManagerBasedRLEnvCfg,
    multi_agent_to_single_agent,
)
from isaaclab.utils.assets import retrieve_file_path
from isaaclab.utils.math import combine_frame_transforms

from isaaclab_rl.rsl_rl import RslRlBaseRunnerCfg, RslRlVecEnvWrapper

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import get_checkpoint_path
from isaaclab_tasks.utils.hydra import hydra_task_config

import ur5_grasp.tasks  # noqa: F401  # TOUHID: registers Isaac-Lift-Cube-UR5e-v0

# ---------------------------------------------------------------------------------------
# TOUHID (Day 22): flushed report machinery. print() alone is not enough — see --report.
# Anchored to THIS FILE so the report lands in ur5_grasp/tools/ no matter the cwd.
# ---------------------------------------------------------------------------------------
_TOOLS_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
_REPORT_PATH = args_cli.report or os.path.join(_TOOLS_DIR, "eval_success_report.txt")
_CSV_PATH = os.path.join(_TOOLS_DIR, "eval_success_results.csv")
_FH = None


def log(msg: str = "") -> None:
    """print + write + flush. Every line of output goes through here."""
    print(msg)
    if _FH is not None:
        _FH.write(msg + "\n")
        _FH.flush()


@hydra_task_config(args_cli.task, args_cli.agent)
def main(env_cfg: ManagerBasedRLEnvCfg | DirectRLEnvCfg | DirectMARLEnvCfg, agent_cfg: RslRlBaseRunnerCfg):
    """Evaluate success rate for an RSL-RL agent."""
    task_name = args_cli.task.split(":")[-1]

    agent_cfg = cli_args.update_rsl_rl_cfg(agent_cfg, args_cli)
    env_cfg.scene.num_envs = args_cli.num_envs if args_cli.num_envs is not None else env_cfg.scene.num_envs
    env_cfg.seed = agent_cfg.seed
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device

    log_root_path = os.path.abspath(os.path.join("logs", "rsl_rl", agent_cfg.experiment_name))
    log("")
    log("=" * 60)
    log(f"EVAL  label={args_cli.label or '(none)'}   task={task_name}")
    log("=" * 60)
    log(f"[progress] experiment dir : {log_root_path}")
    if args_cli.checkpoint:
        resume_path = retrieve_file_path(args_cli.checkpoint)
    else:
        resume_path = get_checkpoint_path(log_root_path, agent_cfg.load_run, agent_cfg.load_checkpoint)
    log(f"[progress] checkpoint     : {resume_path}")
    log(f"[progress] num_envs={env_cfg.scene.num_envs}  seed={agent_cfg.seed}  agent={args_cli.agent}")
    log("[progress] building scene (gym.make) ...")

    env = gym.make(args_cli.task, cfg=env_cfg, render_mode=None)
    if isinstance(env.unwrapped, DirectMARLEnv):
        env = multi_agent_to_single_agent(env)
    env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)

    if agent_cfg.class_name == "OnPolicyRunner":
        runner = OnPolicyRunner(env, agent_cfg.to_dict(), log_dir=None, device=agent_cfg.device)
    elif agent_cfg.class_name == "LagrangianRunner":  # TOUHID: cPPO (PPO-Lagrangian)
        runner = LagrangianRunner(env, agent_cfg.to_dict(), log_dir=None, device=agent_cfg.device)
    elif agent_cfg.class_name == "DistillationRunner":
        runner = DistillationRunner(env, agent_cfg.to_dict(), log_dir=None, device=agent_cfg.device)
    else:
        raise ValueError(f"Unsupported runner class: {agent_cfg.class_name}")
    runner.load(resume_path)
    policy = runner.get_inference_policy(device=env.unwrapped.device)

    # --- scene handles for the env's own lift/goal math ---
    base = env.unwrapped
    obj = base.scene["object"]
    robot = base.scene["robot"]

    lift_hits, goal_hits, n_done = 0, 0, 0
    obs = env.get_observations()
    log("[progress] policy loaded, scene up. Scoring "
        f"{args_cli.episodes} episodes (lift>{args_cli.min_height} m, goal<{args_cli.success_tol} m) ...")

    while n_done < args_cli.episodes:
        with torch.inference_mode():
            actions = policy(obs)
        # measure the (pre-step) near-terminal state, using the env's own definitions
        des_pos_w, _ = combine_frame_transforms(
            robot.data.root_pos_w, robot.data.root_quat_w,
            base.command_manager.get_command("object_pose")[:, :3],
        )
        lifted = obj.data.root_pos_w[:, 2] > args_cli.min_height
        dist = torch.norm(des_pos_w - obj.data.root_pos_w, dim=1)
        goal_ok = lifted & (dist < args_cli.success_tol)

        obs, _, dones, _ = env.step(actions)

        done_ids = torch.nonzero(dones).flatten().tolist()
        for i in done_ids:
            lift_hits += int(lifted[i].item())
            goal_hits += int(goal_ok[i].item())
            n_done += 1

    lift_rate = 100.0 * lift_hits / max(n_done, 1)
    goal_rate = 100.0 * goal_hits / max(n_done, 1)
    log("")
    log("-" * 52)
    log(f"  Label            : {args_cli.label or '(none)'}")
    log(f"  Agent            : {agent_cfg.experiment_name}")
    log(f"  Checkpoint       : {resume_path}")
    log(f"  Episodes scored  : {n_done}")
    log(f"  Lift success     : {lift_rate:.1f}%   ({lift_hits}/{n_done})")
    log(f"  Goal-reach succ. : {goal_rate:.1f}%   ({goal_hits}/{n_done})")
    log("-" * 52)

    # Machine-readable row so the results table can be built without re-parsing prose.
    write_header = not os.path.exists(_CSV_PATH)
    with open(_CSV_PATH, "a") as fh:
        if write_header:
            fh.write("label,experiment,task,seed,episodes,lift_pct,goal_pct,checkpoint\n")
        fh.write(
            f"{args_cli.label or ''},{agent_cfg.experiment_name},{task_name},"
            f"{agent_cfg.seed},{n_done},{lift_rate:.2f},{goal_rate:.2f},{resume_path}\n"
        )
    log(f"  [csv row appended to {_CSV_PATH}]")

    env.close()


if __name__ == "__main__":
    os.makedirs(_TOOLS_DIR, exist_ok=True)
    # APPEND, not truncate: a sweep over six checkpoints accumulates into one readable file.
    _FH = open(_REPORT_PATH, "a")
    try:
        main()
    except Exception:  # noqa: BLE001 — the traceback must land IN the report, not on a lost stream
        import traceback

        log("")
        log("UNHANDLED EXCEPTION:")
        log(traceback.format_exc())
        raise
    finally:
        log(f"[report appended to {_REPORT_PATH}]")
        _FH.close()
        simulation_app.close()
