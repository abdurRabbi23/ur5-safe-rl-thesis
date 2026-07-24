# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Layer 2 · Phase 2 — classical IBVS baseline (single centroid, monocular RGB).

Servo the arm so the cube's colour-centroid moves to the image centre, using an
image Jacobian that the controller MEASURES for itself (two small probe moves)
rather than assuming a camera convention. Flow:

  1. pin the cube at a visible, off-centre spot (repeatable start),
  2. PROBE: nudge the end-effector along camera-x, then camera-y; measure how the
     centroid pixel (u,v) moves  ->  a 2x2 image Jacobian  J = d[u,v]/d[cam_x,cam_y],
  3. SERVO: each step, desired camera-plane move = -lambda * J^-1 * (s - s*),
     map it to joint targets through the arm Jacobian, step, and log the pixel error.

Success = the logged `err_px` shrinks toward ~0 (cube centred). This is the
classical baseline the RL-tuned image Jacobian (Phase 3) will be compared against.

Run on the lab PC:
    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/ibvs_servo.py \
        --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 1 --headless --enable_cameras
Frames -> ~/Abdur_Rabbi_THESIS/results/ibvs_phase2/.
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

parser = argparse.ArgumentParser(description="Layer 2 Phase 2: classical IBVS centroid servo.")
parser.add_argument("--disable_fabric", action="store_true", default=False)
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--task", type=str, default="Isaac-Lift-Cube-UR5e-Play-v0")
parser.add_argument("--gain", type=float, default=0.35, help="IBVS proportional gain lambda.")
parser.add_argument("--steps", type=int, default=400, help="Servo steps.")
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

# ---- locked from Phase 1/2a -------------------------------------------------
MOUNT_POS = (0.0002, -0.0276, 0.2987)                 # wrist-frame standoff (out of gripper)
MOUNT_ROT = (-0.03285, 0.70643, 0.70629, 0.03228)     # (w,x,y,z) aim at grasp point
CUBE_RGB = np.array([112.0, 83.0, 190.0])             # DexCube violet (discovered Phase 2a)
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
    """Global colour-mask detector: cube = pixels near CUBE_RGB. Returns (u,v,npx)."""
    d = np.linalg.norm(rgb.astype(np.float32) - CUBE_RGB, axis=2)
    mask = d < tol
    n = int(mask.sum())
    if n < 20:
        return None, None, 0
    ys, xs = np.nonzero(mask)
    return float(xs.mean()), float(ys.mean()), n


def main():
    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device,
                            num_envs=args_cli.num_envs, use_fabric=not args_cli.disable_fabric)
    env_cfg.scene.wrist_cam = WRIST_CAM_CFG
    env_cfg.scene.ibvs_dome = AssetBaseCfg(prim_path="/World/ibvsDome",
                                           spawn=sim_utils.DomeLightCfg(intensity=3000.0))
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
    wrist_bi = robot.data.body_names.index("wrist_3_link")
    default_q = robot.data.default_joint_pos[:, arm_ids].clone()
    scale = 0.5                                   # matches JointPositionActionCfg scale
    R_wc_mount = math_utils.matrix_from_quat(torch.tensor([MOUNT_ROT], device=device))[0]
    cx, cy = 160.0, 120.0
    s_target = np.array([cx, cy])

    act = torch.zeros(env.action_space.shape, device=device)

    def rgb_now():
        return cam.data.output["rgb"][0, ..., :3].detach().cpu().numpy().astype(np.uint8)

    def arm_jac_pos():
        """3x6 position Jacobian (EE linear vel in world per arm joint vel)."""
        jac = robot.root_physx_view.get_jacobians()
        jbody = wrist_bi if jac.shape[1] == robot.num_bodies else wrist_bi - 1
        J = jac[0, jbody, :, :][:, arm_ids]        # (6,6)
        return J[:3, :]                            # (3,6) linear rows

    def R_world_cam():
        wq = robot.data.body_quat_w[0, wrist_bi]
        R_ww = math_utils.matrix_from_quat(wq.unsqueeze(0))[0]
        return R_ww @ R_wc_mount                   # cam->world

    def step_cam_move(cam_xyz, hold=4):
        """Command an EE move of `cam_xyz` (camera frame, metres) and step `hold` times."""
        V = R_world_cam() @ torch.tensor(cam_xyz, dtype=torch.float32, device=device)
        Jp = arm_jac_pos()
        qdot = torch.linalg.pinv(Jp) @ V           # (6,)
        m = torch.linalg.norm(qdot)                # cap joint step: don't fling near singularities
        if m > 0.08:
            qdot = qdot * (0.08 / m)
        q = robot.data.joint_pos[0, arm_ids]
        q_des = q + qdot
        act[0, :6] = (q_des - default_q[0]) / scale
        for _ in range(hold):
            env.step(act)

    # settle, then pin the cube at a visible, slightly off-centre spot
    for _ in range(40):
        env.step(act)
    cpos = cam.data.pos_w[0]
    fwd = R_world_cam()[:, 2]
    target = cpos + 0.30 * fwd + torch.tensor([0.03, 0.0, 0.0], device=device)  # farther/smaller, mild off-centre
    root = torch.zeros((scene.num_envs, 7), device=device); root[:, 0:3] = target; root[:, 3] = 1.0
    obj.write_root_pose_to_sim(root)
    obj.write_root_velocity_to_sim(torch.zeros((scene.num_envs, 6), device=device))
    for _ in range(6):
        env.step(act)

    u, v, n = detect_centroid(rgb_now())
    if u is None:
        print("[abort] cube not visible after pin — adjust mount/pin before servoing.")
        env.close(); return
    print(f"[start] centroid=({u:.1f},{v:.1f}) npx={n}")

    # ---- PROBE: measure image Jacobian J = d[u,v]/d[cam_x, cam_y] ----
    probe = 0.01  # metres (small so the cube stays in view)
    cols = []
    for axis in (0, 1):
        d0 = detect_centroid(rgb_now()); p0 = cam.data.pos_w[0].clone()
        mv = [0.0, 0.0, 0.0]; mv[axis] = probe
        step_cam_move(mv, hold=4)
        d1 = detect_centroid(rgb_now()); p1 = cam.data.pos_w[0].clone()
        step_cam_move([-mv[0], -mv[1], 0.0], hold=4)           # undo the probe
        if d0[0] is None or d1[0] is None:
            print(f"[abort] cube left view during probe on axis {axis} — mount framing too tight.")
            env.close(); return
        dp_cam = (R_world_cam().T @ (p1 - p0))[axis].item()    # actual cam-frame displacement
        if abs(dp_cam) < 1e-5:
            dp_cam = probe
        cols.append((np.array(d1[:2]) - np.array(d0[:2])) / dp_cam)
    J = np.column_stack(cols)                                  # 2x2, pixels per metre
    print(f"[probe] image Jacobian J=\n{np.array2string(J, precision=1)}")
    if abs(np.linalg.det(J)) < 1e-3:
        print("[abort] near-singular image Jacobian."); env.close(); return
    Jinv = np.linalg.inv(J)

    # ---- SERVO ----
    log = []
    for k in range(args_cli.steps):
        u, v, n = detect_centroid(rgb_now())
        if u is None:
            print(f"[{k:03d}] cube lost from view — stopping."); break
        e = np.array([u, v]) - s_target
        err = float(np.hypot(*e))
        log.append(err)
        if k % 20 == 0:
            print(f"[{k:03d}] centroid=({u:.1f},{v:.1f})  err_px={err:.1f}  npx={n}")
        if err < 4.0:
            print(f"[{k:03d}] converged: err_px={err:.1f}"); break
        d_cam = -args_cli.gain * (Jinv @ e)                    # desired cam-plane move (m)
        d_cam = np.clip(d_cam, -0.01, 0.01)                    # step cap for stability
        step_cam_move([float(d_cam[0]), float(d_cam[1]), 0.0], hold=1)

    if log:
        print(f"\n[result] err_px: start={log[0]:.1f} -> end={log[-1]:.1f}  "
              f"({'CONVERGED' if log[-1] < log[0] * 0.5 else 'no clear convergence — check J sign/gain'})")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
