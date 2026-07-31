# Copyright (c) 2022-2025, The Isaac Lab Project Developers.
# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Evaluate lift / goal-reach success for a trained **skrl** checkpoint.

The skrl twin of eval_success.py. Written as a SEPARATE FILE rather than as branches
inside eval_success.py on purpose: eval_success.py produced the Layer-1 numbers that are
already written up, and it is not worth risking that validated path to save some
duplication. The two scripts share what actually matters — the scoring block below is
character-for-character the same lift/goal math, the same 512-episode protocol, and the
SAME report and CSV files — so rsl_rl and skrl rows land in one table.

  * lift success -- object raised above `--min_height` (env default 0.04 m).
  * goal-reach   -- lifted AND object within `--success_tol` m of the commanded goal.

DETERMINISTIC ACTIONS. rsl_rl's `get_inference_policy()` returns the distribution MEAN, so
this script must too, or the skrl policies would be scored while still exploring and would
look worse for a reason that has nothing to do with the algorithm. The
`outputs[-1].get("mean_actions", outputs[0])` idiom below is IsaacLab's own play.py pattern:
it takes the mean for Gaussian policies (PPO) and falls back to the deterministic action for
policies that have no mean (SAC/TD3 actors), so this script serves those unchanged.

Run from inside Comparison_test/ (log paths are cwd-relative):

    ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/eval_success_skrl.py \
        --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 64 \
        --episodes 512 --seed 42 --label skrl_ppo_s1 \
        --checkpoint logs/skrl/ur5e_lift_skrl/<run>/checkpoints/agent_36000.pt
"""

"""Launch Isaac Sim Simulator first."""

import argparse
import os
import sys

from isaaclab.app import AppLauncher

# --- TOUHID: make the external ur5_grasp package importable (see train_skrl.py) ---
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))  # Comparison_test/
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
# --------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Evaluate success rate of a skrl checkpoint.")
parser.add_argument("--num_envs", type=int, default=64, help="Number of parallel environments.")
parser.add_argument("--task", type=str, default=None, help="Name of the task.")
parser.add_argument("--agent", type=str, default=None, help="Agent cfg entry point (overrides --algorithm).")
parser.add_argument("--algorithm", type=str, default="PPO", choices=["PPO", "SAC", "TD3"])
parser.add_argument("--ml_framework", type=str, default="torch", choices=["torch", "jax", "jax-numpy"])
parser.add_argument("--seed", type=int, default=42, help="FIXED eval seed — same exam for every policy.")
parser.add_argument("--checkpoint", type=str, required=True, help="Path to a skrl agent_*.pt checkpoint.")
parser.add_argument("--episodes", type=int, default=512, help="Number of completed episodes to score over.")
parser.add_argument("--min_height", type=float, default=0.04, help="Lift-success height threshold (m).")
parser.add_argument("--success_tol", type=float, default=0.05, help="Goal-reach distance tolerance (m).")
parser.add_argument("--report", type=str, default=None, help="Report file to APPEND to.")
parser.add_argument("--label", type=str, default=None, help="Short name for this run in the report.")

AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()

sys.argv = [sys.argv[0]] + hydra_args

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import gymnasium as gym
import torch

import skrl
from packaging import version

SKRL_VERSION = "1.4.3"
if version.parse(skrl.__version__) < version.parse(SKRL_VERSION):
    skrl.logger.error(f"Unsupported skrl version: {skrl.__version__}. Need >= {SKRL_VERSION}")
    exit()

if args_cli.ml_framework.startswith("torch"):
    from skrl.utils.runner.torch import Runner
elif args_cli.ml_framework.startswith("jax"):
    from skrl.utils.runner.jax import Runner

from isaaclab.envs import DirectMARLEnv, DirectMARLEnvCfg, DirectRLEnvCfg, ManagerBasedRLEnvCfg
from isaaclab.envs import multi_agent_to_single_agent
from isaaclab.utils.assets import retrieve_file_path
from isaaclab.utils.math import combine_frame_transforms

from isaaclab_rl.skrl import SkrlVecEnvWrapper

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils.hydra import hydra_task_config

import ur5_grasp.tasks  # noqa: F401  # TOUHID: registers Isaac-Lift-Cube-UR5e-v0

# Same entry-point shortcut as train_skrl.py, so eval resolves the identical config the
# run was trained with. Reconstructing the agent from that yaml — rather than rebuilding
# the network by hand — is deliberate: the yaml is the single artefact the training run
# also consumed, so the evaluated policy cannot silently drift from the trained one.
if args_cli.agent is None:
    _algo = args_cli.algorithm.lower()
    agent_cfg_entry_point = "skrl_cfg_entry_point" if _algo == "ppo" else f"skrl_{_algo}_cfg_entry_point"
else:
    agent_cfg_entry_point = args_cli.agent

# --- flushed report machinery, identical contract to eval_success.py ---------------
_TOOLS_DIR = os.path.normpath(os.path.join(_HERE, "..", "tools"))
_REPORT_PATH = args_cli.report or os.path.join(_TOOLS_DIR, "eval_success_report.txt")
_CSV_PATH = os.path.join(_TOOLS_DIR, "eval_success_results.csv")
_FH = None


def log(msg: str = "") -> None:
    """print + write + flush. Every line of output goes through here."""
    print(msg)
    if _FH is not None:
        _FH.write(msg + "\n")
        _FH.flush()


@hydra_task_config(args_cli.task, agent_cfg_entry_point)
def main(env_cfg: ManagerBasedRLEnvCfg | DirectRLEnvCfg | DirectMARLEnvCfg, agent_cfg: dict):
    """Evaluate success rate for a skrl agent."""
    task_name = args_cli.task.split(":")[-1]

    env_cfg.scene.num_envs = args_cli.num_envs
    env_cfg.seed = args_cli.seed
    agent_cfg["seed"] = args_cli.seed
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device

    # Eval must not write TensorBoard files or checkpoints — otherwise every eval spawns a
    # junk run directory under logs/skrl/ that a later glob would mistake for a training run.
    agent_cfg["agent"]["experiment"]["write_interval"] = 0
    agent_cfg["agent"]["experiment"]["checkpoint_interval"] = 0

    resume_path = retrieve_file_path(args_cli.checkpoint)

    log("")
    log("=" * 60)
    log(f"EVAL (skrl)  label={args_cli.label or '(none)'}   task={task_name}")
    log("=" * 60)
    log(f"[progress] checkpoint     : {resume_path}")
    log(f"[progress] num_envs={env_cfg.scene.num_envs}  eval_seed={args_cli.seed}  algo={args_cli.algorithm}")
    log("[progress] building scene (gym.make) ...")

    env = gym.make(args_cli.task, cfg=env_cfg, render_mode=None)
    if isinstance(env.unwrapped, DirectMARLEnv):
        env = multi_agent_to_single_agent(env)
    env = SkrlVecEnvWrapper(env, ml_framework=args_cli.ml_framework)

    runner = Runner(env, agent_cfg)
    runner.agent.load(resume_path)

    # Put the agent in evaluation mode. IsaacLab's own skrl play.py calls
    # set_running_mode("eval"), but that method does not exist on the skrl build actually
    # installed here (AttributeError, Day 23), so try the alternatives in order. This is a
    # belt-and-braces path rather than a guess at the version, because the eval must not be
    # blocked a second time by an API name. It is also not load-bearing for determinism:
    # the actions below are the distribution MEAN regardless of mode, and these networks
    # contain no dropout or batch-norm, so mode only affects skrl's internal bookkeeping.
    if hasattr(runner.agent, "set_running_mode"):
        runner.agent.set_running_mode("eval")
    elif hasattr(runner.agent, "set_mode"):
        runner.agent.set_mode("eval")
    else:
        for _m in getattr(runner.agent, "models", {}).values():
            if _m is not None:
                _m.eval()

    # --- scene handles for the env's own lift/goal math (same as eval_success.py) ---
    base = env.unwrapped
    obj = base.scene["object"]
    robot = base.scene["robot"]

    lift_hits, goal_hits, n_done = 0, 0, 0
    obs, _ = env.reset()
    log("[progress] policy loaded, scene up. Scoring "
        f"{args_cli.episodes} episodes (lift>{args_cli.min_height} m, goal<{args_cli.success_tol} m) ...")

    while n_done < args_cli.episodes:
        with torch.inference_mode():
            outputs = runner.agent.act(obs, timestep=0, timesteps=0)
            # deterministic: distribution mean for PPO, deterministic action for SAC/TD3.
            # Guarded because the trailing element is only a dict on the agents that expose
            # extra outputs; if it is not, the sampled action is the only thing available.
            if isinstance(outputs, tuple) and isinstance(outputs[-1], dict):
                actions = outputs[-1].get("mean_actions", outputs[0])
            else:
                actions = outputs[0] if isinstance(outputs, tuple) else outputs

        # measure the (pre-step) near-terminal state, using the env's own definitions
        des_pos_w, _ = combine_frame_transforms(
            robot.data.root_pos_w, robot.data.root_quat_w,
            base.command_manager.get_command("object_pose")[:, :3],
        )
        lifted = obj.data.root_pos_w[:, 2] > args_cli.min_height
        dist = torch.norm(des_pos_w - obj.data.root_pos_w, dim=1)
        goal_ok = lifted & (dist < args_cli.success_tol)

        # skrl's wrapper returns the gymnasium 5-tuple, unlike rsl_rl's 4-tuple.
        obs, _, terminated, truncated, _ = env.step(actions)
        dones = (terminated | truncated).flatten()

        done_ids = torch.nonzero(dones).flatten().tolist()
        for i in done_ids:
            lift_hits += int(lifted[i].item())
            goal_hits += int(goal_ok[i].item())
            n_done += 1

    lift_rate = 100.0 * lift_hits / max(n_done, 1)
    goal_rate = 100.0 * goal_hits / max(n_done, 1)
    experiment = agent_cfg["agent"]["experiment"].get("directory", "skrl")
    experiment = os.path.basename(str(experiment).rstrip("/"))

    log("")
    log("-" * 52)
    log(f"  Label            : {args_cli.label or '(none)'}")
    log(f"  Agent            : {experiment} ({args_cli.algorithm}, skrl)")
    log(f"  Checkpoint       : {resume_path}")
    log(f"  Episodes scored  : {n_done}")
    log(f"  Lift success     : {lift_rate:.1f}%   ({lift_hits}/{n_done})")
    log(f"  Goal-reach succ. : {goal_rate:.1f}%   ({goal_hits}/{n_done})")
    log("-" * 52)

    write_header = not os.path.exists(_CSV_PATH)
    with open(_CSV_PATH, "a") as fh:
        if write_header:
            fh.write("label,experiment,task,seed,episodes,lift_pct,goal_pct,checkpoint\n")
        fh.write(
            f"{args_cli.label or ''},{experiment},{task_name},"
            f"{args_cli.seed},{n_done},{lift_rate:.2f},{goal_rate:.2f},{resume_path}\n"
        )
    log(f"  [csv row appended to {_CSV_PATH}]")

    env.close()


if __name__ == "__main__":
    os.makedirs(_TOOLS_DIR, exist_ok=True)
    _FH = open(_REPORT_PATH, "a")
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
