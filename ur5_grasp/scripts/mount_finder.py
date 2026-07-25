# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Layer 2 helper — find a CAMERA MOUNT that looks past the gripper at the cube.

The current eye-in-hand mount sits 0.30 m out along the wrist and aims BACK at the grasp
point, so it only ever sees the gripper. The camera needs to sit beside the gripper and
look OUTWARD along the approach axis (wrist -z). Two things are unknown: which side clears
the gripper, and which arm pose points the approach axis at the cube. So this sweeps BOTH:
a few candidate mounts (each its own camera) x a few arm poses, in one run.

For every (pose, mount) it saves scan_p{p}_c{c}.png to results/ibvs_phase2/ and prints
whether the cube is in view. Run once, have Claude read the frames, and we lock the winning
mount pos/rot into ibvs_servo.py's WRIST_CAM_CFG (and the pose into HOVER_Q).

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/mount_finder.py \
        --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 1 --enable_cameras --headless

(Headless is fine here — we only need the saved frames. Ctrl-C after one full cycle.)
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

parser = argparse.ArgumentParser(description="Layer 2: camera-mount + pose sweep.")
parser.add_argument("--disable_fabric", action="store_true", default=False)
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--task", type=str, default="Isaac-Lift-Cube-UR5e-Play-v0")
parser.add_argument("--dwell", type=int, default=40, help="sim steps per pose before capture.")
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

CUBE_RGB = np.array([112.0, 83.0, 190.0])
ARM_JOINTS = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
              "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]

# ---- candidate MOUNTS (wrist frame): sit beside the gripper, aim outward (approach = -z).
#      pos = where the lens sits; aim = a point it looks at. 4 lateral directions.
# Aim target in the WRIST frame: geometry.txt showed the cube sits along wrist +z
# (z = +0.18..+0.33, small y) — so look along +z toward the grasp region, NOT -z.
_AIM = (0.0, 0.0, 0.20)
MOUNTS = [
    {"name": "px6", "pos": (0.06, 0.0, 0.00), "aim": _AIM},    # +x side of the gripper
    {"name": "nx6", "pos": (-0.06, 0.0, 0.00), "aim": _AIM},   # -x side
    {"name": "py6", "pos": (0.0, 0.06, 0.00), "aim": _AIM},    # +y side
    {"name": "ny6", "pos": (0.0, -0.06, 0.00), "aim": _AIM},   # -y side
    {"name": "px9b", "pos": (0.09, 0.0, -0.03), "aim": _AIM},  # +x, a bit wider/back
    {"name": "back", "pos": (0.0, 0.0, -0.05), "aim": _AIM},   # centred behind wrist (baseline)
]

# ---- ARM POSES: a close look-down pre-grasp (downB) + the ready pose for coverage.
POSES = [
    ("downB", [0.0, -0.9, 1.3, -1.00, -1.57, 0.0]),
    ("ready", [0.0, -1.2, 1.4, -1.75, -1.57, 0.0]),
]


def _look_at_quat(pos, aim):
    """Quaternion (w,x,y,z) so a ROS camera at `pos` looks at `aim` (both wrist frame).
    ROS cam axes: x right, y down, z forward."""
    pos = np.asarray(pos, float); aim = np.asarray(aim, float)
    f = aim - pos
    f = f / (np.linalg.norm(f) + 1e-9)                    # forward (+z)
    up = np.array([0.0, 0.0, 1.0])                        # wrist +z as up reference
    if abs(float(f @ up)) > 0.95:
        up = np.array([0.0, 1.0, 0.0])
    right = np.cross(up, f); right /= (np.linalg.norm(right) + 1e-9)   # +x
    down = np.cross(f, right)                             # +y
    R = np.column_stack([right, down, f])                # cam axes in wrist frame
    t = np.trace(R)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2
        w = 0.25 * s; x = (R[2, 1] - R[1, 2]) / s; y = (R[0, 2] - R[2, 0]) / s; z = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        w = (R[2, 1] - R[1, 2]) / s; x = 0.25 * s; y = (R[0, 1] + R[1, 0]) / s; z = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        w = (R[0, 2] - R[2, 0]) / s; x = (R[0, 1] + R[1, 0]) / s; y = 0.25 * s; z = (R[1, 2] + R[2, 1]) / s
    else:
        s = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        w = (R[1, 0] - R[0, 1]) / s; x = (R[0, 2] + R[2, 0]) / s; y = (R[1, 2] + R[2, 1]) / s; z = 0.25 * s
    return (float(w), float(x), float(y), float(z))


def _cam_cfg(idx, mount):
    return CameraCfg(
        prim_path="{ENV_REGEX_NS}/Robot/wrist_3_link/scan_cam_%d" % idx,
        update_period=0.0, height=240, width=320, data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(focal_length=18.0, focus_distance=400.0,
                                         horizontal_aperture=20.955, clipping_range=(0.01, 5.0)),
        offset=CameraCfg.OffsetCfg(pos=mount["pos"], rot=_look_at_quat(mount["pos"], mount["aim"]),
                                   convention="ros"),
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
    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device,
                            num_envs=args_cli.num_envs, use_fabric=not args_cli.disable_fabric)
    for i, m in enumerate(MOUNTS):
        setattr(env_cfg.scene, f"scan_cam_{i}", _cam_cfg(i, m))
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
    cams = [scene.scene[f"scan_cam_{i}"] for i in range(len(MOUNTS))]
    obj = scene.scene["object"]
    robot = scene.scene["robot"]
    device = scene.device
    out_dir = os.path.join(_REPO_ROOT, "results", "ibvs_phase2")
    os.makedirs(out_dir, exist_ok=True)

    arm_ids = list(robot.find_joints(ARM_JOINTS)[0])
    wrist_bi = robot.data.body_names.index("wrist_3_link")
    default_q = robot.data.default_joint_pos[:, arm_ids].clone()
    scale = 0.5
    act = torch.zeros(env.action_space.shape, device=device)
    geo_path = os.path.join(out_dir, "geometry.txt")

    def rgb(cam):
        return cam.data.output["rgb"][0, ..., :3].detach().cpu().numpy().astype(np.uint8)

    def snap_hold(vals):
        q = torch.tensor([vals], dtype=torch.float32, device=device)
        robot.write_joint_state_to_sim(q, torch.zeros((1, len(arm_ids)), device=device), joint_ids=arm_ids)
        act[0, :6] = (q[0] - default_q[0]) / scale

    print(f"[scan] mounts={[m['name'] for m in MOUNTS]}  poses={[p[0] for p in POSES]}")
    for i, m in enumerate(MOUNTS):
        print(f"[scan] mount c{i} ({m['name']}): pos={m['pos']} rot={tuple(round(x,4) for x in _look_at_quat(m['pos'], m['aim']))}")
    cycle = 0
    while simulation_app.is_running():
        cycle += 1
        hits = []
        geo_lines = []
        for p, (pname, vals) in enumerate(POSES):
            snap_hold(vals)
            for _ in range(args_cli.dwell):
                if not simulation_app.is_running():
                    break
                env.step(act)
            # ground-truth geometry: where the cube sits relative to the wrist at this pose
            wpos = robot.data.body_pos_w[0, wrist_bi]
            wquat = robot.data.body_quat_w[0, wrist_bi]
            Rww = math_utils.matrix_from_quat(wquat.unsqueeze(0))[0]
            cube_w = obj.data.root_pos_w[0]
            cube_wrist = Rww.transpose(0, 1) @ (cube_w - wpos)
            gline = (f"pose {pname}: wrist_w={[round(x,3) for x in wpos.tolist()]} "
                     f"cube_w={[round(x,3) for x in cube_w.tolist()]} "
                     f"cube_in_wrist={[round(x,3) for x in cube_wrist.tolist()]} "
                     f"dist={float(torch.linalg.norm(cube_w - wpos)):.3f}")
            print("[geom] " + gline)
            geo_lines.append(gline)
            for c, cam in enumerate(cams):
                frame = np.ascontiguousarray(rgb(cam))
                u, v, n = detect_centroid(frame)
                save_png(os.path.join(out_dir, f"scan_p{p}_c{c}.png"), mark(frame.copy(), u, v))
                black = int(frame.max()) < 8
                tag = (f"YES ({u:.0f},{v:.0f}) npx={n}" if u is not None
                       else ("black" if black else "no"))
                if u is not None:
                    hits.append((pname, MOUNTS[c]["name"], u, v, n))
                print(f"[p{p}:{pname} c{c}:{MOUNTS[c]['name']}] cube={tag}")
        with open(geo_path, "w") as fh:
            fh.write("\n".join(geo_lines) + "\n")
        print(f"[cycle {cycle}] HITS (cube in view): "
              f"{[(h[0], h[1]) for h in hits] if hits else 'NONE'} — wrote geometry.txt + scan_pX_cY.png")

    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
