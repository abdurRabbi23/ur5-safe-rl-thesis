# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Layer 2 · Phase 1 — eye-in-hand camera smoke test (RGB only, no depth).

Adds a wrist-mounted RGB camera to the UR5e lift env and checks two things:
  1. the camera actually renders and the cube is in frame, and
  2. we can turn the cube's position into a pixel (u, v) — the feature the IBVS
     loop will servo on.

It does NOT train or control anything. It holds the arm at its ready pose, saves a
few RGB frames with a RED CROSSHAIR drawn where we *predict* the cube projects, and
prints that pixel. If the crosshair lands on the cube -> camera geometry is correct
and Phase 1 is done. If it's off -> we adjust the camera offset/orientation (marked
TOUHID below) or the projection convention.

Why RGB-only: it matches the real webcam (no depth). The cube world position used
here is privileged ground truth, used ONLY to validate the pixel geometry; the real
appearance-based detector (colour centroid) comes in Phase 2.

Run on the lab PC (cameras REQUIRE --enable_cameras):

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/ibvs_camera_test.py \
        --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 1 --headless --enable_cameras

Frames are saved to  ~/Abdur_Rabbi_THESIS/results/ibvs_phase1/.
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

parser = argparse.ArgumentParser(description="Layer 2 Phase 1: eye-in-hand camera smoke test.")
parser.add_argument("--disable_fabric", action="store_true", default=False)
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--task", type=str, default="Isaac-Lift-Cube-UR5e-Play-v0")
parser.add_argument("--frames", type=int, default=5, help="How many RGB frames to save.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

# cameras must be enabled to render; force it on so a forgotten flag can't waste a run
args_cli.enable_cameras = True

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import numpy as np
import torch

import gymnasium as gym

import isaaclab.sim as sim_utils
import isaaclab.utils.math as math_utils
from isaaclab.sensors import CameraCfg
from isaaclab_tasks.utils import parse_env_cfg

import ur5_grasp.tasks  # noqa: F401  # TOUHID: registers the task


# ============================ eye-in-hand camera ==============================
# Mounted on wrist_3_link, looking along +z — the SAME axis as the 0.16 m TCP
# offset, i.e. toward the grasp point. RGB only (no depth) to match the real
# webcam. TOUHID: tune pos / rot below if the cube isn't in the frame.
WRIST_CAM_CFG = CameraCfg(
    prim_path="{ENV_REGEX_NS}/Robot/wrist_3_link/wrist_cam",
    update_period=0.0,                 # refresh every physics step
    height=240,
    width=320,
    data_types=["rgb"],
    spawn=sim_utils.PinholeCameraCfg(
        focal_length=18.0,             # ~60 deg horizontal FOV with the aperture below
        focus_distance=400.0,
        horizontal_aperture=20.955,
        clipping_range=(0.01, 5.0),
    ),
    offset=CameraCfg.OffsetCfg(
        # Measured aim: camera +z points at the fingertip grasp point (wrist -z axis).
        # Recovered from recommend_aim() — stable across episodes.
        pos=(-3e-05, 0.00368, -0.03983),
        rot=(-0.03285, 0.70643, 0.70629, 0.03228),   # (w, x, y, z)
        convention="ros",                            # ROS cam frame: x right, y down, z forward
    ),
)


def project_to_pixel(cam, p_w):
    """World point (3,) -> pixel (u, v) via the camera's own intrinsics + ROS pose.
    Returns (u, v, z_cam). z_cam <= 0 means the point is behind the camera."""
    K = cam.data.intrinsic_matrices[0]                       # (3, 3)
    t = cam.data.pos_w[0]                                    # (3,)
    q = cam.data.quat_w_ros[0]                               # (4,) w,x,y,z ; ROS cam frame
    R_wc = math_utils.matrix_from_quat(q.unsqueeze(0))[0]    # cam -> world
    p_c = R_wc.transpose(0, 1) @ (p_w - t)                   # world -> cam
    z = p_c[2]
    u = K[0, 0] * (p_c[0] / z) + K[0, 2]
    v = K[1, 1] * (p_c[1] / z) + K[1, 2]
    return float(u), float(v), float(z)


def recommend_aim(wpos, wquat, target_w, mount=0.04):
    """Compute the CameraCfg.OffsetCfg (rot, pos) that points the eye-in-hand
    camera's +z (ROS forward) straight at `target_w`, expressed in the wrist frame.
    Returns (quat_wxyz, pos_xyz) ready to paste into WRIST_CAM_CFG."""
    Rw = math_utils.matrix_from_quat(wquat.unsqueeze(0))[0]          # wrist -> world
    f = Rw.transpose(0, 1) @ (target_w - wpos)                       # dir to target, wrist frame
    f = f / torch.linalg.norm(f)
    down_local = -(Rw.transpose(0, 1) @ torch.tensor([0.0, 0.0, 1.0], device=f.device))
    if torch.abs(torch.dot(down_local, f)) > 0.95:                  # near-parallel -> alt up
        down_local = -(Rw.transpose(0, 1) @ torch.tensor([0.0, 1.0, 0.0], device=f.device))
    x_ax = torch.linalg.cross(down_local, f); x_ax = x_ax / torch.linalg.norm(x_ax)
    y_ax = torch.linalg.cross(f, x_ax)
    Rc = torch.stack([x_ax, y_ax, f], dim=1)                        # cols = cam axes in wrist frame
    quat = math_utils.quat_from_matrix(Rc.unsqueeze(0))[0]          # (w, x, y, z)
    return quat, mount * f


def draw_crosshair(img, u, v, color=(255, 0, 0), size=8):
    """Paint a crosshair at (u, v) on an HxWx3 uint8 array, in place."""
    h, w, _ = img.shape
    ui, vi = int(round(u)), int(round(v))
    if 0 <= ui < w and 0 <= vi < h:
        c = np.array(color, dtype=np.uint8)
        img[max(0, vi - size):min(h, vi + size), ui] = c
        img[vi, max(0, ui - size):min(w, ui + size)] = c
    return img


def detect_centroid_rgb(rgb, seed_uv, tol=45):
    """Appearance-only cube detector (no privileged pose). Seeds the target colour
    from a 3x3 patch at `seed_uv`, masks pixels within `tol` (L2 in RGB) of it, and
    returns (u, v, n_px, seed_rgb). This is the Phase-2 stand-in for the real webcam
    detector; seeding from ground truth here just validates colour separability and
    reports the cube's colour so we can hard-code the range for the live loop."""
    h, w, _ = rgb.shape
    su = min(max(int(round(seed_uv[0])), 1), w - 2)
    sv = min(max(int(round(seed_uv[1])), 1), h - 2)
    seed = np.median(rgb[sv - 1:sv + 2, su - 1:su + 2].reshape(-1, 3).astype(np.float32), axis=0)
    mask = np.linalg.norm(rgb.astype(np.float32) - seed, axis=2) < tol
    n = int(mask.sum())
    if n == 0:
        return None, None, 0, seed
    ys, xs = np.nonzero(mask)
    return float(xs.mean()), float(ys.mean()), n, seed


def save_png(path, img):
    try:
        from PIL import Image
        Image.fromarray(img).save(path)
    except Exception:
        import imageio.v2 as imageio
        imageio.imwrite(path, img)


def main():
    env_cfg = parse_env_cfg(
        args_cli.task, device=args_cli.device, num_envs=args_cli.num_envs, use_fabric=not args_cli.disable_fabric
    )
    # attach the eye-in-hand camera to the scene cfg — Layer 1 env files untouched.
    # InteractiveScene iterates cfg.__dict__, so a dynamically added sensor is picked up.
    env_cfg.scene.wrist_cam = WRIST_CAM_CFG

    env = gym.make(args_cli.task, cfg=env_cfg)
    env.reset()

    scene = env.unwrapped
    cam = scene.scene["wrist_cam"]
    obj = scene.scene["object"]
    robot = scene.scene["robot"]
    device = scene.device

    out_dir = os.path.join(_REPO_ROOT, "results", "ibvs_phase1")
    os.makedirs(out_dir, exist_ok=True)

    def cam_pose_world():
        R = math_utils.matrix_from_quat(cam.data.quat_w_ros[0].unsqueeze(0))[0]
        return cam.data.pos_w[0], R[:, 2]      # camera position, forward (+z) axis in world

    TABLE_Z = 0.03
    act = torch.zeros(env.action_space.shape, device=device)   # arm ready pose, gripper open
    saved = 0
    step = 0
    SETTLE = 40
    pinned = False
    while simulation_app.is_running() and saved < args_cli.frames:
        with torch.inference_mode():
            env.step(act)
            step += 1

            # After settling, drop the cube onto the camera's optical axis where it
            # meets the table, so it sits dead-centre in view. Verifies render +
            # projection numerically, independent of the random spawn.
            if not pinned and step == SETTLE:
                cpos, fwd = cam_pose_world()
                d = (TABLE_Z - cpos[2]) / fwd[2] if fwd[2] < -0.05 else torch.as_tensor(0.2, device=device)
                target = cpos + d * fwd
                root_pose = torch.zeros((scene.num_envs, 7), device=device)
                root_pose[:, 0:3] = target
                root_pose[:, 3] = 1.0
                obj.write_root_pose_to_sim(root_pose)
                obj.write_root_velocity_to_sim(torch.zeros((scene.num_envs, 6), device=device))
                print(f"[pin] cube -> optical axis @ table: {[round(x, 3) for x in target.tolist()]}")
                pinned = True

            if not pinned or step < SETTLE + 5 or step % 10 != 0:
                continue

            rgb = cam.data.output["rgb"][0, ..., :3].detach().cpu().numpy().astype(np.uint8)
            cube_w = obj.data.root_pos_w[0]
            u, v, z = project_to_pixel(cam, cube_w)                # ground-truth pixel
            du, dv, npx, seed = detect_centroid_rgb(rgb, (u, v))   # appearance detector

            img = np.ascontiguousarray(rgb).copy()
            draw_crosshair(img, u, v, color=(255, 0, 0))           # ground truth = red
            if du is not None:
                draw_crosshair(img, du, dv, color=(0, 255, 0))     # colour centroid = green
            fname = os.path.join(out_dir, f"frame_{saved:02d}.png")
            save_png(fname, img)

            in_view = (0 <= u < rgb.shape[1]) and (0 <= v < rgb.shape[0]) and (z > 0)
            print(f"[{saved:02d}] cube_world={[round(c, 3) for c in cube_w.tolist()]}  ->  "
                  f"gt (u,v)=({u:.1f}, {v:.1f})  z_cam={z:.3f}  in_view={in_view}")
            if du is not None:
                err = ((du - u) ** 2 + (dv - v) ** 2) ** 0.5
                print(f"     colour-centroid=({du:.1f}, {dv:.1f})  npx={npx}  "
                      f"err_vs_gt={err:.1f}px  seed_rgb={[int(c) for c in seed]}")
            else:
                print(f"     colour-centroid: NONE within tol  seed_rgb={[int(c) for c in seed]}")
            if saved == 0:
                print("     intrinsics K=\n" + str(cam.data.intrinsic_matrices[0].cpu().numpy()))
                print(f"     cam_pos_w={[round(c, 3) for c in cam.data.pos_w[0].tolist()]}")
            saved += 1

    print(f"\nDONE. Wrote {saved} frames to {out_dir}")
    print("CHECK: does the red crosshair sit ON the cube? yes -> Phase 1 geometry verified.")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
