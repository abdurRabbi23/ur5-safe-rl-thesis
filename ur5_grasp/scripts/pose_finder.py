# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Layer 2 helper — sweep arm configs to find a LOOK-DOWN pose where the wrist camera
sees the cube.

The eye-in-hand mount aims at the grasp point between the fingers, so from most poses the
camera just sees the gripper (or, if the lens buries in a mesh, a black frame). The pose we
want has the OPEN gripper hovering above the cube pointing down, so the cube sits between
the fingers and is in view.

This holds the arm at each config you pass, one after another, and saves a labelled frame
(`pose_00.png`, `pose_01.png`, ...) to results/ibvs_phase2/ plus a console line saying
whether the cube is in view. Run once, then have Claude read the frames and pick/refine.

Run WITH the GUI (drop --headless) so you can watch:

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/pose_finder.py \
        --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 1 --enable_cameras

Joint order: shoulder_pan, shoulder_lift, elbow, wrist_1, wrist_2, wrist_3.
Pass your own set with --q "c1 ; c2 ; c3" (each c = 6 comma-separated radians). The default
sweeps a spread around the ready pose. It cycles forever; Ctrl-C to quit.
"""

"""Launch Isaac Sim Simulator first."""

import argparse
import os
import sys

from isaaclab.app import AppLauncher

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Default sweep: ready pose + variations of wrist_1 (camera pitch) and shoulder_lift/elbow
# (where the wrist sits). Kept broad on purpose so one run shows which render + see the cube.
_DEFAULT = (
    "0,-1.2,1.4,-1.75,-1.57,0"      # ready pose (renders; looks sideways at the gripper)
    " ; 0,-1.2,1.4,-2.40,-1.57,0"   # wrist_1 pitched one way
    " ; 0,-1.2,1.4,-1.00,-1.57,0"   # wrist_1 pitched the other way
    " ; 0,-1.2,1.4,-0.30,-1.57,0"   # wrist_1 further
    " ; 0,-0.8,1.2,-1.60,-1.57,0"   # wrist parked higher
    " ; 0,-1.6,1.8,-1.80,-1.57,0"   # wrist parked lower/forward
    " ; 0,-1.0,1.6,-2.20,-1.57,0"   # combo
    " ; 0,-1.2,1.4,-1.75,-1.57,1.57"  # ready + wrist_3 roll 90 deg
)

parser = argparse.ArgumentParser(description="Layer 2: batch look-down pose finder.")
parser.add_argument("--disable_fabric", action="store_true", default=False)
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--task", type=str, default="Isaac-Lift-Cube-UR5e-Play-v0")
parser.add_argument("--q", type=str, default=_DEFAULT,
                    help="configs separated by ';', each 6 comma-separated joint angles (rad).")
parser.add_argument("--dwell", type=int, default=60, help="sim steps held per config before capture.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import numpy as np
import torch

import gymnasium as gym

import isaaclab.sim as sim_utils
import isaaclab.utils.math as math_utils
from isaaclab.assets import AssetBaseCfg
from isaaclab.sensors import CameraCfg
from isaaclab_tasks.utils import parse_env_cfg

import ur5_grasp.tasks  # noqa: F401

# ---- same eye-in-hand mount as ibvs_servo.py --------------------------------
MOUNT_POS = (0.0002, -0.0276, 0.2987)
MOUNT_ROT = (-0.03285, 0.70643, 0.70629, 0.03228)
CUBE_RGB = np.array([112.0, 83.0, 190.0])
ARM_JOINTS = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
              "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]

WRIST_CAM_CFG = CameraCfg(
    prim_path="{ENV_REGEX_NS}/Robot/wrist_3_link/wrist_cam",
    update_period=0.0, height=240, width=320, data_types=["rgb"],
    spawn=sim_utils.PinholeCameraCfg(focal_length=18.0, focus_distance=400.0,
                                     horizontal_aperture=20.955, clipping_range=(0.01, 5.0)),
    offset=CameraCfg.OffsetCfg(pos=MOUNT_POS, rot=MOUNT_ROT, convention="ros"),
)


def detect_centroid(rgb, tol=50):
    d = np.linalg.norm(rgb.astype(np.float32) - CUBE_RGB, axis=2)
    mask = d < tol
    n = int(mask.sum())
    if n < 20:
        return None, None, 0
    ys, xs = np.nonzero(mask)
    return float(xs.mean()), float(ys.mean()), n


def save_png(path, img):
    try:
        from PIL import Image
        Image.fromarray(img).save(path)
    except Exception:
        import imageio.v2 as imageio
        imageio.imwrite(path, img)


def mark(img, u, v, c=(0, 255, 0), s=8):
    if u is None:
        return img
    h, w, _ = img.shape
    ui, vi = int(round(u)), int(round(v))
    if 0 <= ui < w and 0 <= vi < h:
        col = np.array(c, dtype=np.uint8)
        img[max(0, vi - s):min(h, vi + s), ui] = col
        img[vi, max(0, ui - s):min(w, ui + s)] = col
    return img


def main():
    configs = []
    for chunk in args_cli.q.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        vals = [float(x) for x in chunk.split(",")]
        assert len(vals) == 6, f"each config needs 6 values, got {len(vals)}: {chunk}"
        configs.append(vals)

    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device,
                            num_envs=args_cli.num_envs, use_fabric=not args_cli.disable_fabric)
    env_cfg.scene.wrist_cam = WRIST_CAM_CFG
    env_cfg.scene.ibvs_dome = AssetBaseCfg(prim_path="/World/ibvsDome",
                                           spawn=sim_utils.DomeLightCfg(intensity=3000.0))
    try:
        env_cfg.commands.object_pose.debug_vis = False
    except AttributeError:
        pass
    try:
        env_cfg.scene.ee_frame.debug_vis = False
    except AttributeError:
        pass

    env = gym.make(args_cli.task, cfg=env_cfg)
    env.reset()
    scene = env.unwrapped
    cam = scene.scene["wrist_cam"]
    obj = scene.scene["object"]
    robot = scene.scene["robot"]
    device = scene.device
    out_dir = os.path.join(_REPO_ROOT, "results", "ibvs_phase2")
    os.makedirs(out_dir, exist_ok=True)

    arm_ids = list(robot.find_joints(ARM_JOINTS)[0])
    default_q = robot.data.default_joint_pos[:, arm_ids].clone()
    scale = 0.5
    act = torch.zeros(env.action_space.shape, device=device)

    def rgb_now():
        return cam.data.output["rgb"][0, ..., :3].detach().cpu().numpy().astype(np.uint8)

    def snap_hold(vals):
        q = torch.tensor([vals], dtype=torch.float32, device=device)
        robot.write_joint_state_to_sim(q, torch.zeros((1, len(arm_ids)), device=device), joint_ids=arm_ids)
        act[0, :6] = (q[0] - default_q[0]) / scale

    print(f"[sweep] {len(configs)} configs; saving pose_00..pose_{len(configs)-1:02d}.png to results/ibvs_phase2/")
    cycle = 0
    while simulation_app.is_running():
        cycle += 1
        good = []
        for i, vals in enumerate(configs):
            snap_hold(vals)
            for _ in range(args_cli.dwell):
                if not simulation_app.is_running():
                    break
                env.step(act)
            frame = np.ascontiguousarray(rgb_now())
            u, v, n = detect_centroid(frame)
            save_png(os.path.join(out_dir, f"pose_{i:02d}.png"), mark(frame.copy(), u, v))
            R = math_utils.matrix_from_quat(cam.data.quat_w_ros[0].unsqueeze(0))[0]
            camp = cam.data.pos_w[0]
            black = int(frame.max()) < 8
            state = (f"YES centroid=({u:.0f},{v:.0f}) npx={n}" if u is not None
                     else ("BLACK (lens buried in mesh)" if black else "no cube (renders bg/gripper)"))
            if u is not None:
                good.append(i)
            print(f"[pose {i:02d}] q={vals} -> {state} | cam_z={camp[2]:.2f} fwd_z={R[2,2]:.2f}")
        print(f"[cycle {cycle}] cube-in-view poses: {good if good else 'NONE'}. "
              f"Frames saved -> tell Claude to read pose_XX.png (or paste this table).")

    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
