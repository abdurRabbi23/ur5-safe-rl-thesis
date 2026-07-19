# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Calibrate the manipulability floor for the singularity cost term.

Rolls out the trained PPO baseline and records the Yoshikawa manipulability
w = sqrt(det(J Jᵀ)) of the 6-DOF arm every step, then prints its distribution. Pick
`MANIP_FLOOR` (in ur5e_lift_env.py) around the 5th–10th percentile: low enough that a
well-conditioned grasp is never penalised, high enough to fire before a real singularity.

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/calibrate_manipulability.py \
        --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 64 --steps 400
"""

"""Launch Isaac Sim Simulator first."""

import argparse
import os
import sys

from isaaclab.app import AppLauncher

# --- TOUHID: make external package + Isaac Lab's cli_args importable -------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
_CLI_ARGS_DIR = os.path.join(_REPO_ROOT, "IsaacLab", "scripts", "reinforcement_learning", "rsl_rl")
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
if _CLI_ARGS_DIR not in sys.path:
    sys.path.append(_CLI_ARGS_DIR)
# --------------------------------------------------------------------------------

import cli_args  # isort: skip

parser = argparse.ArgumentParser(description="Calibrate the manipulability floor from a PPO rollout.")
parser.add_argument("--num_envs", type=int, default=64, help="Number of environments to simulate.")
parser.add_argument("--task", type=str, default="Isaac-Lift-Cube-UR5e-Play-v0", help="Name of the task.")
parser.add_argument("--steps", type=int, default=400, help="Number of rollout steps to sample.")
parser.add_argument(
    "--agent", type=str, default="rsl_rl_cfg_entry_point", help="RL agent configuration entry point."
)
parser.add_argument("--seed", type=int, default=None, help="Seed used for the environment")
cli_args.add_rsl_rl_args(parser)
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()

sys.argv = [sys.argv[0]] + hydra_args
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import gymnasium as gym
import torch

from rsl_rl.runners import OnPolicyRunner

from isaaclab.envs import ManagerBasedRLEnvCfg

from isaaclab_rl.rsl_rl import RslRlBaseRunnerCfg, RslRlVecEnvWrapper

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import get_checkpoint_path
from isaaclab_tasks.utils.hydra import hydra_task_config

import ur5_grasp.tasks  # noqa: F401  # TOUHID: registers Isaac-Lift-Cube-UR5e-v0
from ur5_grasp.safe_rl.costs import SafetyCostComputer


@hydra_task_config(args_cli.task, args_cli.agent)
def main(env_cfg: ManagerBasedRLEnvCfg, agent_cfg: RslRlBaseRunnerCfg):
    agent_cfg = cli_args.update_rsl_rl_cfg(agent_cfg, args_cli)
    env_cfg.scene.num_envs = args_cli.num_envs
    env_cfg.seed = agent_cfg.seed
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device

    # locate the PPO baseline checkpoint (experiment 'ur5e_lift')
    log_root_path = os.path.abspath(os.path.join("logs", "rsl_rl", agent_cfg.experiment_name))
    if args_cli.checkpoint:
        resume_path = args_cli.checkpoint
    else:
        resume_path = get_checkpoint_path(log_root_path, agent_cfg.load_run, agent_cfg.load_checkpoint)
    print(f"[INFO] Loading checkpoint: {resume_path}")

    env = gym.make(args_cli.task, cfg=env_cfg, render_mode=None)
    env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)

    runner = OnPolicyRunner(env, agent_cfg.to_dict(), log_dir=None, device=agent_cfg.device)
    runner.load(resume_path)
    policy = runner.get_inference_policy(device=env.unwrapped.device)

    robot = env.unwrapped.scene["robot"]
    computer = SafetyCostComputer(
        robot=robot,
        arm_joint_names=env.unwrapped.ARM_JOINTS,
        ee_body_name=env.unwrapped.EE_BODY,
        monitored_body_names=env.unwrapped.MONITORED_BODIES,
        z_floor=env.unwrapped.COLLISION_Z_FLOOR,
        joint_margin=env.unwrapped.JOINT_LIMIT_MARGIN,
        manip_floor=env.unwrapped.MANIP_FLOOR,
        w_collision=env.unwrapped.W_COLLISION,
        w_joint=env.unwrapped.W_JOINT,
        w_manip=env.unwrapped.W_MANIP,
    )

    w_s, jl_s, z_s = [], [], []
    obs = env.get_observations()
    for _ in range(args_cli.steps):
        with torch.inference_mode():
            actions = policy(obs)
            obs, _, _, _ = env.step(actions)
            w_s.append(computer.manipulability().detach().flatten().cpu())
            jl_s.append(computer.joint_limit_min_distance().detach().flatten().cpu())
            z_s.append(computer.min_link_height().detach().flatten().cpu())

    w = torch.cat(w_s)
    jl = torch.cat(jl_s)
    z = torch.cat(z_s)
    qs = torch.tensor([0.01, 0.05, 0.10, 0.25, 0.50, 0.90])

    def _report(name, x, low_is_dangerous=True):
        pct = torch.quantile(x, qs)
        print(f"\n{name}  ({x.numel()} samples)")
        print(f"  min={x.min():.5f}  mean={x.mean():.5f}  max={x.max():.5f}")
        print("  " + "  ".join(f"p{int(q*100):02d}={p:.4f}" for q, p in zip(qs.tolist(), pct.tolist())))
        return pct

    print("\n" + "=" * 68)
    print(f"SAFETY-THRESHOLD CALIBRATION — trained baseline, "
          f"{args_cli.num_envs} envs x {args_cli.steps} steps")
    print("Goal: pick thresholds the UNCONSTRAINED policy actually crosses sometimes,")
    print("      else cPPO has nothing to fix and the benchmark is trivial.")

    wp = _report("Manipulability  w = sqrt(det(J Jᵀ))  (low = near singular)", w)
    print(f"  -> MANIP_FLOOR candidate ~p10–p25: {wp[2]:.4f} – {wp[3]:.4f}")
    print("     (higher floor = baseline violates more; verify it still lets a good grasp through)")

    jp = _report("Joint-limit clearance (rad to nearer soft limit; low = near limit)", jl)
    print(f"  current JOINT_LIMIT_MARGIN=0.10 -> baseline within-margin rate: "
          f"{(jl < 0.10).float().mean().item()*100:.1f}% of steps")

    zp = _report("Min monitored-link height z (world; below floor = table hit)", z, low_is_dangerous=True)
    print(f"  current COLLISION_Z_FLOOR=0.00 -> baseline below-floor rate: "
          f"{(z < 0.0).float().mean().item()*100:.1f}% of steps")

    print("-" * 68)
    print("Set MANIP_FLOOR (and, if needed, JOINT_LIMIT_MARGIN / COLLISION_Z_FLOOR)")
    print("in ur5_grasp/tasks/lift/ur5e_lift_env.py. Aim for a few-to-30% baseline violation rate.")
    print("=" * 68 + "\n")

    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
