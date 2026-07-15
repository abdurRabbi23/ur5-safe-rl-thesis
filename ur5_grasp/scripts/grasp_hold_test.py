# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Physics-only grasp HOLDING test (no policy, no reward, no IK).

Isolates the one question the reward-hacking hides: can the 2f-85 actually clamp
a cube and hold it against gravity? Procedure:
  1. reset, let the arm settle at its ready pose (gripper open),
  2. teleport the cube to the reach-frame point (between the finger pads), zero its
     velocity,
  3. command the gripper CLOSE and hold,
  4. print the cube's height over time. If it stays near pad level -> HOLDS.
     If it falls to the table (~0.02 m) -> the grip is too weak.

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/grasp_hold_test.py \
        --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 1
"""

"""Launch Isaac Sim Simulator first."""

import argparse
import os
import sys

from isaaclab.app import AppLauncher

# --- TOUHID: make external ur5_grasp package importable --------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
# --------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Physics-only grasp holding test.")
parser.add_argument("--disable_fabric", action="store_true", default=False)
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--task", type=str, default=None)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import gymnasium as gym
import torch

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg

import ur5_grasp.tasks  # noqa: F401  # TOUHID: registers the task


def main():
    env_cfg = parse_env_cfg(
        args_cli.task, device=args_cli.device, num_envs=args_cli.num_envs, use_fabric=not args_cli.disable_fabric
    )
    env = gym.make(args_cli.task, cfg=env_cfg)
    env.reset()

    scene = env.unwrapped
    obj = scene.scene["object"]
    ee = scene.scene["ee_frame"]
    device = scene.device

    # zero action template; last slot is the gripper (negative = close)
    act = torch.zeros(env.action_space.shape, device=device)

    WARMUP = 30       # let the arm settle at ready pose (gripper open)
    PLACE_AT = 30     # teleport the cube between the pads here
    HOLD_UNTIL = 220  # keep closing until this step
    placed = False
    grasp_point = None

    step = 0
    while simulation_app.is_running() and step <= HOLD_UNTIL:
        with torch.inference_mode():
            if step < PLACE_AT:
                act[:] = 0.0                     # arm ready pose, gripper OPEN
            else:
                act[:] = 0.0
                act[:, -1] = -1.0                # arm ready pose, gripper CLOSE

            env.step(act)
            step += 1

            # place the cube between the pads once, after warmup
            if not placed and step == PLACE_AT:
                grasp_point = ee.data.target_pos_w[0, 0].clone()   # world point between fingers
                root_pose = torch.zeros((scene.num_envs, 7), device=device)
                root_pose[:, 0:3] = grasp_point
                root_pose[:, 3] = 1.0            # identity quaternion (w,x,y,z)
                obj.write_root_pose_to_sim(root_pose)
                obj.write_root_velocity_to_sim(torch.zeros((scene.num_envs, 6), device=device))
                print(f"\n[placed cube between pads at z={grasp_point[2]:.3f}] closing gripper...\n")

            # report cube height a few times while holding
            if grasp_point is not None and step % 30 == 0:
                cz = obj.data.root_pos_w[0, 2].item()
                gz = grasp_point[2].item()
                held = "HELD" if (cz > gz - 0.05) else "DROPPED"
                print(f"  step {step:4d} | cube z = {cz:+.3f}  (pad z {gz:+.3f})  -> {held}")

    # final verdict
    if grasp_point is not None:
        cz = obj.data.root_pos_w[0, 2].item()
        gz = grasp_point[2].item()
        print("\n================= GRASP HOLD RESULT =================")
        if cz > gz - 0.05:
            print(f" cube stayed at z={cz:+.3f} (pad {gz:+.3f})  ->  GRIP HOLDS ✅")
        else:
            print(f" cube fell to z={cz:+.3f} (pad {gz:+.3f})  ->  GRIP TOO WEAK ❌")
        print("====================================================\n")

    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
