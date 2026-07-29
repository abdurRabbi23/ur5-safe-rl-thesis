# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Day-19 mount diagnostic: where are the gripper bodies relative to wrist_3?

Step 0 of module 03c found the pad midpoint sits 13.5 mm from `wrist_3` while the
pad-to-pad gap (84.4 mm) exactly matches the real 2F-85 stroke. The gripper's
INTERNAL geometry is therefore correct; its placement relative to the wrist is not.
The asset report also shows `base_link` appearing TWICE in the rigid-body list (the
arm's and the gripper's), with both `robot_gripper_joint` and `root_joint` resolving
to that ambiguous name.

This script decides between two explanations:

  (A) instanceable-proxy artefact -- `body_pos_w` for the gripper bodies is wrong but
      the rendered/collision geometry is fine. Layer 1 is untouched; freeze and move on.
  (B) broken USD assembly -- the gripper really is mounted at the wrong transform, so
      the weld point (wrist_3 + [0,0,0.16]) is ~15 cm away from the pads and every play
      video shows a floating cube.

Read the printed table, THEN run once with the GUI and look at the robot. If the
gripper renders at the end of the wrist, it is (A).

Run on the lab PC (isaaclab env):

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    # headless -- gets you the numbers
    ./isaaclab.sh -p ../ur5_grasp/tools/check_gripper_mount.py --headless
    # GUI -- gets you the screenshot that settles (A) vs (B)
    ./isaaclab.sh -p ../ur5_grasp/tools/check_gripper_mount.py
"""

import argparse
import os
import sys

from isaaclab.app import AppLauncher

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

parser = argparse.ArgumentParser(description="Gripper mount-transform diagnostic.")
parser.add_argument("--task", type=str, default="Isaac-Lift-Cube-UR5e-Play-v0")
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--settle", type=int, default=15, help="steps to settle before reading")
parser.add_argument("--hold", action="store_true",
                    help="after printing, keep the sim running so the GUI stays open "
                         "(close the Isaac Sim window to exit). Use with the GUI.")
parser.add_argument("--weld", action="store_true",
                    help="during --hold, command CLOSE so the proximity weld latches and you "
                         "can see whether the cube sits between the pads.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch

import gymnasium as gym

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg
from isaaclab.utils.math import quat_rotate_inverse

import ur5_grasp.tasks  # noqa: F401  # registers the tasks

# expected pad-midpoint distance from wrist_3 for a real UR5e + 2F-85:
#   d6 flange offset ~0.0996 m  +  gripper base->pad ~0.13 m  ~=  0.23 m
EXPECTED_MIN = 0.15
EXPECTED_MAX = 0.30


def main() -> None:
    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device, num_envs=args_cli.num_envs)
    env = gym.make(args_cli.task, cfg=env_cfg)
    env.reset()

    scene = env.unwrapped
    robot = scene.scene["robot"]
    device = scene.device

    # settle at the ready pose with a zero action so transforms are populated
    act = torch.zeros(env.action_space.shape, device=device)
    with torch.inference_mode():
        for _ in range(args_cli.settle):
            env.step(act)

    bnames = list(robot.body_names)
    w_id = bnames.index("wrist_3_link")
    w_pos = robot.data.body_pos_w[0, w_id]
    w_quat = robot.data.body_quat_w[0, w_id]

    def to_local(p):
        return quat_rotate_inverse(w_quat.unsqueeze(0), (p - w_pos).unsqueeze(0))[0]

    print("\n" + "=" * 74)
    print(" GRIPPER MOUNT DIAGNOSTIC")
    print("=" * 74)

    # --- 1) duplicate body names -------------------------------------------------
    dupes = {n for n in bnames if bnames.count(n) > 1}
    print(f"\n[1] rigid bodies: {len(bnames)}")
    if dupes:
        print(f"    !! DUPLICATE BODY NAMES: {sorted(dupes)}")
        for d in sorted(dupes):
            idxs = [i for i, n in enumerate(bnames) if n == d]
            print(f"       '{d}' at indices {idxs} -- name lookups resolve to {idxs[0]} only")
    else:
        print("    no duplicate names")

    # --- 2) every body in wrist_3's local frame ----------------------------------
    print("\n[2] body positions in the wrist_3 LOCAL frame (m):")
    print(f"    {'idx':>3}  {'body':<26} {'x':>8} {'y':>8} {'z':>8} {'dist':>8}")
    for i, n in enumerate(bnames):
        loc = to_local(robot.data.body_pos_w[0, i])
        d = torch.norm(loc).item()
        print(f"    {i:>3}  {n:<26} {loc[0]:+8.4f} {loc[1]:+8.4f} {loc[2]:+8.4f} {d:8.4f}")

    # --- 3) pads and the reach frame ---------------------------------------------
    pad_ids = [i for i, n in enumerate(bnames) if "inner_finger" in n and "knuckle" not in n]
    print(f"\n[3] pad bodies: {[bnames[i] for i in pad_ids]}")
    if len(pad_ids) >= 2:
        pads = robot.data.body_pos_w[0, pad_ids]
        gap = torch.norm(pads[0] - pads[1]).item()
        pad_mid = pads.mean(dim=0)
        loc = to_local(pad_mid)
        dist = torch.norm(loc).item()
        print(f"    pad-to-pad gap        = {gap * 1000:6.1f} mm  (2F-85 spec ~85 mm at open)")
        print(f"    pad midpoint (local)  = [{loc[0]:+.4f}, {loc[1]:+.4f}, {loc[2]:+.4f}] m")
        print(f"    |pad midpoint|        = {dist:.4f} m")
        ok = EXPECTED_MIN <= dist <= EXPECTED_MAX
        print(f"    physical plausibility = {'PLAUSIBLE' if ok else 'IMPOSSIBLE'}"
              f"  (expected {EXPECTED_MIN:.2f}-{EXPECTED_MAX:.2f} m)")

    ee = scene.scene["ee_frame"]
    tcp = ee.data.target_pos_w[0, 0, :]
    tcp_loc = to_local(tcp)
    print(f"\n[4] weld / reach frame (what the env ACTUALLY uses):")
    print(f"    ee_frame (local)      = [{tcp_loc[0]:+.4f}, {tcp_loc[1]:+.4f}, {tcp_loc[2]:+.4f}] m")
    print(f"    |ee_frame|            = {torch.norm(tcp_loc).item():.4f} m")
    if len(pad_ids) >= 2:
        sep = torch.norm(tcp - pad_mid).item()
        print(f"\n[5] VERDICT INPUT: reach-frame-to-pad-midpoint = {sep * 1000:.1f} mm")
        if sep > 0.05:
            print("    -> the weld point is NOT between the pads.")
            print("       If the GUI shows the gripper correctly at the wrist end, this is")
            print("       case (A): body_pos_w is lying (proxy artefact). Layer 1 is SAFE.")
            print("       If the GUI shows the gripper inside the wrist, this is case (B):")
            print("       the USD assembly is broken and the figures are compromised.")
        else:
            print("    -> weld point sits between the pads. Geometry is consistent; freeze.")
    print("=" * 74 + "\n")

    # --- keep the GUI alive so the mount can actually be LOOKED at ------------------
    if args_cli.hold:
        mode = "CLOSE (weld latching)" if args_cli.weld else "OPEN"
        print(f"[hold] sim running, gripper command = {mode}.")
        print("[hold] look at: (a) is the gripper at the END of the wrist?")
        print("[hold]          (b) is the cube between the pads, or floating?")
        print("[hold] close the Isaac Sim window to exit.\n")
        hold_act = torch.zeros(env.action_space.shape, device=device)
        if args_cli.weld:
            hold_act[:, -1] = -1.0  # BinaryJointPositionAction: <0 == CLOSE == weld latches
        with torch.inference_mode():
            while simulation_app.is_running():
                env.step(hold_act)

    env.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
