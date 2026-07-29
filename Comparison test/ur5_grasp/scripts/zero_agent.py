# Copyright (c) 2022-2025, The Isaac Lab Project Developers.
# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Zero-action runner for the UR5e grasp env (geometry / physics inspection).

Same as Isaac Lab's scripts/environments/zero_agent.py, with the TOUHID import
shim so the external `ur5_grasp` package + its registered task are importable.

Holds the arm at its ready pose (zero arm action + use_default_offset=True) so you
can visually inspect grasp geometry — turn on the EE-frame marker to see exactly
where the reach target sits relative to the fingertips.

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/zero_agent.py \
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

# add argparse arguments
parser = argparse.ArgumentParser(description="Zero agent for Isaac Lab environments.")
parser.add_argument(
    "--disable_fabric", action="store_true", default=False, help="Disable fabric and use USD I/O operations."
)
parser.add_argument("--num_envs", type=int, default=None, help="Number of environments to simulate.")
parser.add_argument("--task", type=str, default=None, help="Name of the task.")
# append AppLauncher cli args
AppLauncher.add_app_launcher_args(parser)
# parse the arguments
args_cli = parser.parse_args()

# launch omniverse app
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import gymnasium as gym
import torch

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg
from isaaclab.utils.math import subtract_frame_transforms

import ur5_grasp.tasks  # noqa: F401  # TOUHID: registers Isaac-Lift-Cube-UR5e-v0


def _geometry_report(env):
    """TOUHID: one-time grasp-geometry probe. Prints where the RL reach-target
    (ee_frame) actually is vs the true grasp point (midpoint of the two inner
    fingers), and the exact local offset that would put the frame between the
    fingertips."""
    scene = env.unwrapped
    robot = scene.scene["robot"]
    obj = scene.scene["object"]
    ee = scene.scene["ee_frame"]

    names = robot.data.body_names
    li = names.index("left_inner_finger")
    ri = names.index("right_inner_finger")
    wi = names.index("wrist_3_link")

    body_pos = robot.data.body_pos_w[0]      # (num_bodies, 3)
    body_quat = robot.data.body_quat_w[0]    # (num_bodies, 4)

    tcp = 0.5 * (body_pos[li] + body_pos[ri])          # true grasp point (world)
    wrist_pos = body_pos[wi]
    wrist_quat = body_quat[wi]
    ee_pos = ee.data.target_pos_w[0, 0]                # current reach-target (world)
    cube_pos = obj.data.root_pos_w[0]

    # desired local offset = TCP expressed in the wrist_3_link frame
    off_local, _ = subtract_frame_transforms(
        wrist_pos.unsqueeze(0), wrist_quat.unsqueeze(0), tcp.unsqueeze(0)
    )
    off_local = off_local[0]
    err = torch.norm(ee_pos - tcp).item()

    p = lambda t: "[" + ", ".join(f"{v:+.3f}" for v in t.tolist()) + "]"
    print("\n================= GRASP GEOMETRY REPORT =================")
    print(f" cube position (world)            : {p(cube_pos)}")
    print(f" true grasp point / TCP (world)   : {p(tcp)}   <- between the fingers")
    print(f" current reach-target ee_frame    : {p(ee_pos)}")
    print(f" >> ee_frame is OFF by {err:.3f} m from the real grasp point")
    print(f" wrist_3_link position (world)    : {p(wrist_pos)}")
    print(f" CORRECT OffsetCfg pos to use     : {p(off_local)}")
    print("   (replace offset=OffsetCfg(pos=[0,0,0.16]) with the vector above)")
    print("========================================================\n")


def main():
    """Zero actions agent with Isaac Lab environment."""
    # parse configuration
    env_cfg = parse_env_cfg(
        args_cli.task, device=args_cli.device, num_envs=args_cli.num_envs, use_fabric=not args_cli.disable_fabric
    )
    # create environment
    env = gym.make(args_cli.task, cfg=env_cfg)

    # print info (this is vectorized environment)
    print(f"[INFO]: Gym observation space: {env.observation_space}")
    print(f"[INFO]: Gym action space: {env.action_space}")
    # reset environment
    env.reset()
    # simulate environment
    step = 0
    reported = False
    while simulation_app.is_running():
        # run everything in inference mode
        with torch.inference_mode():
            # compute zero actions
            actions = torch.zeros(env.action_space.shape, device=env.unwrapped.device)
            # apply actions
            env.step(actions)
            step += 1
            # let the arm settle at its ready pose, then print the geometry once
            if not reported and step == 40:
                _geometry_report(env)
                reported = True

    # close the simulator
    env.close()


if __name__ == "__main__":
    # run the main function
    main()
    # close sim app
    simulation_app.close()
