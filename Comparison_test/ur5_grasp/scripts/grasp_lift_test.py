# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Confound-free contact-grasp test for the -Contact variant (no weld).

Every mid-air grasp test so far was confounded: a free cube falls before the slow
fingers close, and a teleport-'frozen' cube (reset AFTER the physics step) lets the
fingers ratchet through it. This test pins the cube correctly:

  * while the fingers close, rewrite the cube's pose to the pad midpoint BEFORE each
    physics step. The collider is then present when the fingers push, so if the pads
    make real contact the finger drive STALLS at the cube's width (no free-fall, no
    ratchet). If instead finger_joint runs to 0, the pads genuinely pass through.
  * then STOP pinning and watch: if the grip holds the cube by friction it stays up;
    if it slips it falls -> tune pad friction / clamp effort.

Also prints the exact LOCAL wrist_3->pad-midpoint offset = the correct value for
`_TCP_OFFSET` in ur5e_contact_env_cfg.py (Bug 2).

Run on the lab PC (isaaclab env):

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/grasp_lift_test.py \
        --task Isaac-Lift-Cube-UR5e-Contact-Play-v0 --num_envs 1
"""

import argparse
import os
import sys

from isaaclab.app import AppLauncher

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

parser = argparse.ArgumentParser(description="Contact-grasp pinned-close hold test.")
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--task", type=str, default="Isaac-Lift-Cube-UR5e-Contact-Play-v0")
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch

import gymnasium as gym

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg

import ur5_grasp.tasks  # noqa: F401  # registers the tasks

try:
    from isaaclab.utils.math import quat_rotate_inverse
except Exception:  # noqa: BLE001
    quat_rotate_inverse = None

PLACE_AT = 30       # open + settle, then place the cube at the pad midpoint
STOP_PIN = 90       # fingers fully closed by now -> stop pinning, test the hold
HOLD_UNTIL = 230


def main() -> None:
    env_cfg = parse_env_cfg(
        args_cli.task, device=args_cli.device, num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env = gym.make(args_cli.task, cfg=env_cfg)
    env.reset()

    scene = env.unwrapped
    obj = scene.scene["object"]
    robot = scene.scene["robot"]
    device = scene.device
    N = scene.num_envs

    bnames = list(robot.body_names)
    pad_ids = [i for i, n in enumerate(bnames) if "inner_finger" in n and "knuckle" not in n]
    wrist_ids = [i for i, n in enumerate(bnames) if n == "wrist_3_link"]
    jnames = list(robot.joint_names)
    fj_id = jnames.index("finger_joint")

    act = torch.zeros(env.action_space.shape, device=device)
    pinned_pose = None
    place_pt = None
    placed = False

    step = 0
    while simulation_app.is_running() and step <= HOLD_UNTIL:
        with torch.inference_mode():
            # -Contact convention: +1 = OPEN (finger->0.8), -1 = CLOSE (finger->0.0)
            act[:] = 0.0
            act[:, -1] = +1.0 if step < PLACE_AT else -1.0

            # pin the cube in place BEFORE stepping, so it's a present obstacle
            if placed and pinned_pose is not None and step < STOP_PIN:
                obj.write_root_pose_to_sim(pinned_pose)
                obj.write_root_velocity_to_sim(torch.zeros((N, 6), device=device))
            elif placed and step == STOP_PIN:
                print(f"\n[step {step}] pin released — grip must now hold the cube alone\n")

            env.step(act)
            step += 1

            if not placed and step == PLACE_AT:
                pad_mid = robot.data.body_pos_w[0, pad_ids].mean(dim=0)
                place_pt = pad_mid.clone()
                pinned_pose = torch.zeros((N, 7), device=device)
                pinned_pose[:, 0:3] = pad_mid
                pinned_pose[:, 3] = 1.0
                obj.write_root_pose_to_sim(pinned_pose)
                obj.write_root_velocity_to_sim(torch.zeros((N, 6), device=device))
                placed = True
                if wrist_ids and quat_rotate_inverse is not None:
                    w_pos = robot.data.body_pos_w[0, wrist_ids[0]]
                    w_quat = robot.data.body_quat_w[0, wrist_ids[0]]
                    local = quat_rotate_inverse(w_quat.unsqueeze(0), (pad_mid - w_pos).unsqueeze(0))[0]
                    print(f"[local offset] correct wrist_3->pad OffsetCfg pos = "
                          f"[{local[0]:+.4f}, {local[1]:+.4f}, {local[2]:+.4f}] m "
                          f"(cfg currently uses [-0.013, 0, 0])")
                print(f"\n[placed cube at pad midpoint z={place_pt[2]:.3f}] closing (pinned)...\n")

            if placed and step % 10 == 0:
                cz = obj.data.root_pos_w[0, 2].item()
                pz = place_pt[2].item()
                phase = "pinned" if step < STOP_PIN else "HOLD"
                held = "HELD" if (cz > pz - 0.05) else "DROPPED"
                fj = robot.data.joint_pos[0, fj_id].item()
                if len(pad_ids) >= 2:
                    pads = robot.data.body_pos_w[0, pad_ids]
                    gap = torch.norm(pads[0] - pads[1]).item()
                else:
                    gap = float("nan")
                print(f"  step {step:4d} [{phase:6}] cube z={cz:+.3f} (pad {pz:+.3f}) {held}"
                      f" | finger_joint={fj:+.3f} | pad gap={gap*1000:5.1f} mm")

    cz = obj.data.root_pos_w[0, 2].item()
    pz = place_pt[2].item() if place_pt is not None else 0.0
    fj = robot.data.joint_pos[0, fj_id].item()
    print("\n================= CONTACT GRASP RESULT =================")
    print(f" finger_joint at end = {fj:+.3f}  (stalled >0 = pads clamped the cube;"
          f" ~0 = pads closed through it)")
    if cz > pz - 0.05:
        print(f" cube held at z={cz:+.3f} (pad {pz:+.3f}) after release -> GRIP HOLDS ✅")
    else:
        print(f" cube fell to z={cz:+.3f} (pad {pz:+.3f}) after release -> slips / no clamp ❌")
    print("=======================================================\n")

    env.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
