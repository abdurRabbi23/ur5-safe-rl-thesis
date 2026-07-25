# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Layer 2 · Phase 2 — classical IBVS baseline (single centroid, monocular RGB).

Servo the arm so the cube's colour-centroid moves to the image centre, using an image
Jacobian the controller MEASURES for itself (two small probe moves) rather than assuming a
camera convention. Flow:

  1. settle at the ready pose; the eye-in-hand camera looks along the wrist +z axis at the
     table and sees the cube (mount recovered with mount_finder.py: beside the gripper,
     aimed at the grasp region),
  2. DETECT the cube = the most-saturated blob (the DexCube has bright multi-colour faces),
  3. PROBE: nudge the end-effector along camera-x, then camera-y; measure how the centroid
     pixel (u,v) moves  ->  a 2x2 image Jacobian  J = d[u,v]/d[cam_x,cam_y],
  4. SERVO: each step, desired camera-plane move = -lambda * J^-1 * (s - s*), map it to
     joint targets through the arm Jacobian, step, log the pixel error.

Success = the logged `err_px` shrinks toward ~0 (cube centred). This is the classical
baseline the RL-tuned image Jacobian (Phase 3) will be compared against.

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

# ---- eye-in-hand mount (recovered with mount_finder.py, Day 14) -------------
# Sits beside the gripper and looks along wrist +z at the grasp region. The old mount
# (0.30 m out, aimed -z) pointed straight back at the gripper and never saw the cube.
MOUNT_POS = (0.06, 0.0, 0.0)                           # wrist frame: 6 cm to the +x side
MOUNT_ROT = (0.9894, 0.0, -0.1452, 0.0)               # (w,x,y,z) aim +z toward the grasp region
ARM_JOINTS = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
              "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]
# Optional fixed arm config (6 joint angles, rad). None = ready pose, which already frames
# the cube from this mount. Only override if you want a different vantage.
HOVER_Q = None
SAFE_U = (40, 280)                                    # keep the start centroid this far inside the 320x240 frame
SAFE_V = (30, 210)                                    #   -> probe/servo moves can't push the cube out of view

WRIST_CAM_CFG = CameraCfg(
    prim_path="{ENV_REGEX_NS}/Robot/wrist_3_link/wrist_cam",
    update_period=0.0, height=240, width=320, data_types=["rgb"],
    spawn=sim_utils.PinholeCameraCfg(focal_length=18.0, focus_distance=400.0,
                                     horizontal_aperture=20.955, clipping_range=(0.01, 5.0)),
    offset=CameraCfg.OffsetCfg(pos=MOUNT_POS, rot=MOUNT_ROT, convention="ros"),
)


def detect_cube(rgb, s_min=0.35, v_min=50):
    """Cube = the LARGEST saturated blob (the DexCube's bright faces). Taking the biggest
    connected region rather than the global centroid makes it robust to a second coloured
    object in view. Returns (u, v, npx)."""
    f = rgb.astype(np.float32)
    mx = f.max(axis=2); mn = f.min(axis=2)
    sat = np.where(mx > 1, (mx - mn) / np.clip(mx, 1, None), 0.0)   # HSV saturation
    mask = (sat > s_min) & (mx > v_min)
    if int(mask.sum()) < 30:
        return None, None, 0
    try:                                                           # largest connected component
        from scipy import ndimage
        lab, nl = ndimage.label(mask)
        sizes = ndimage.sum(mask, lab, index=np.arange(1, nl + 1))
        keep = lab == (int(np.argmax(sizes)) + 1)
    except Exception:                                              # fallback: window around the brightest blob
        ys, xs = np.nonzero(mask)
        k = int(np.argmax(sat[ys, xs])); sy, sx = ys[k], xs[k]
        rows = np.abs(np.arange(mask.shape[0])[:, None] - sy) < 55
        cols = np.abs(np.arange(mask.shape[1])[None, :] - sx) < 55
        keep = mask & rows & cols
    n = int(keep.sum())
    if n < 30:
        return None, None, 0
    ys, xs = np.nonzero(keep)
    return float(xs.mean()), float(ys.mean()), n


def _save_png(path, img):
    try:
        from PIL import Image
        Image.fromarray(img).save(path)
    except Exception:
        import imageio.v2 as imageio
        imageio.imwrite(path, img)


def _mark(img, u, v, c=(0, 255, 0), s=8):
    if u is None:
        return img
    h, w, _ = img.shape
    ui, vi = int(round(u)), int(round(v))
    if 0 <= ui < w and 0 <= vi < h:
        col = np.array(c, dtype=np.uint8)
        img[max(0, vi - s):min(h, vi + s), ui] = col
        img[vi, max(0, ui - s):min(w, ui + s)] = col
    return img


def _fmt(d):
    return f"({d[0]:.0f},{d[1]:.0f},n={d[2]})" if d[0] is not None else "None"


def main():
    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device,
                            num_envs=args_cli.num_envs, use_fabric=not args_cli.disable_fabric)
    env_cfg.scene.wrist_cam = WRIST_CAM_CFG
    env_cfg.scene.ibvs_dome = AssetBaseCfg(prim_path="/World/ibvsDome",
                                           spawn=sim_utils.DomeLightCfg(intensity=3000.0))
    # Hide the pose-command + ee_frame debug gizmos so they can't pollute the view.
    try:
        env_cfg.commands.object_pose.debug_vis = False
    except AttributeError:
        pass
    try:
        env_cfg.scene.ee_frame.debug_vis = False
    except AttributeError:
        pass
    # Freeze the cube's reset randomisation so the baseline start is repeatable (default y range
    # is +/-0.25 m, which sometimes lands the cube on a frame edge).
    try:
        env_cfg.events.reset_object_position.params["pose_range"] = {"x": (0.0, 0.0), "y": (0.0, 0.0), "z": (0.0, 0.0)}
    except (AttributeError, KeyError, TypeError):
        pass
    # Spawn the cube where THIS camera/pose frames it centrally (world (0.5,0) lands in the
    # far corner). Tuned from debug_start.png; nudge if the start centroid is near an edge.
    try:
        env_cfg.scene.object.init_state.pos = (0.56, 0.16, 0.055)
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
    wrist_bi = robot.data.body_names.index("wrist_3_link")
    default_q = robot.data.default_joint_pos[:, arm_ids].clone()
    scale = 0.5                                   # matches JointPositionActionCfg scale
    R_wc_mount = math_utils.matrix_from_quat(torch.tensor([MOUNT_ROT], device=device))[0]
    cx, cy = 160.0, 120.0
    s_target = np.array([cx, cy])
    act = torch.zeros(env.action_space.shape, device=device)

    def rgb_now():
        return cam.data.output["rgb"][0, ..., :3].detach().cpu().numpy().astype(np.uint8)

    def arm_jac():
        """Full 6x6 spatial Jacobian (EE [linear; angular] world vel per arm joint vel)."""
        jac = robot.root_physx_view.get_jacobians()
        jbody = wrist_bi if jac.shape[1] == robot.num_bodies else wrist_bi - 1
        return jac[0, jbody, :, :][:, arm_ids]      # (6,6)

    def R_world_cam():
        wq = robot.data.body_quat_w[0, wrist_bi]
        R_ww = math_utils.matrix_from_quat(wq.unsqueeze(0))[0]
        return R_ww @ R_wc_mount                    # cam->world

    def step_cam_move(cam_xyz, hold=4, cap=0.08):
        """Command an EE move of `cam_xyz` (camera frame, metres) and step `hold` times.
        `cap` bounds the joint step so an ill-conditioned direction can't swing the arm."""
        V = R_world_cam() @ torch.tensor(cam_xyz, dtype=torch.float32, device=device)   # world linear vel
        V = V.clone(); V[2] = 0.0                               # LOCK camera height: no diving toward the table
        twist = torch.cat([V, torch.zeros(3, device=device)])   # zero angular: keep the wrist orientation fixed
        Jf = arm_jac()                                          # (6,6) [linear; angular]
        # Weight the ANGULAR rows heavily so orientation is held STRICTLY. A plain linear+angular
        # least-squares is unit-mismatched (m vs rad), so it sacrifices "zero rotation" to fit the
        # tiny linear command -> the camera pitches and dives. Weighting fixes that.
        Wa = 25.0
        Jw = Jf.clone(); Jw[3:6, :] = Wa * Jw[3:6, :]
        tw = twist.clone(); tw[3:6] = Wa * tw[3:6]
        lam = 0.02
        qdot = Jw.transpose(0, 1) @ torch.linalg.solve(
            Jw @ Jw.transpose(0, 1) + (lam * lam) * torch.eye(6, device=device), tw)
        m = torch.linalg.norm(qdot)
        if m > cap:
            qdot = qdot * (cap / m)
        q = robot.data.joint_pos[0, arm_ids]
        q_des = q + qdot
        act[0, :6] = (q_des - default_q[0]) / scale
        for _ in range(hold):
            env.step(act)

    # ---- optional fixed arm config; default = ready pose (already frames the cube) ----
    if HOVER_Q is not None:
        q_hover = torch.tensor([HOVER_Q], dtype=torch.float32, device=device)
        robot.write_joint_state_to_sim(q_hover, torch.zeros((1, len(arm_ids)), device=device), joint_ids=arm_ids)
        act[0, :6] = (q_hover[0] - default_q[0]) / scale

    # ---- settle, then detect the (now deterministic) cube on the table ----
    for _ in range(40):
        env.step(act)
    u, v, n = detect_cube(rgb_now())
    _save_png(os.path.join(out_dir, "debug_start.png"),
              _mark(np.ascontiguousarray(rgb_now()).copy(), u, v))
    if u is None:
        print("[abort] no cube detected at the start pose — see debug_start.png "
              "(camera may need re-aiming, or lower detect_cube s_min).")
        env.close(); return
    err0 = float(np.hypot(u - cx, v - cy))
    print(f"[start] cube centroid=({u:.1f},{v:.1f}) npx={n} err_px={err0:.1f}  (saved debug_start.png)")
    _sv = np.linalg.svd(arm_jac().detach().cpu().numpy(), compute_uv=False)
    print(f"[dbg] arm-Jacobian cond={_sv[0] / _sv[-1]:.1f} (min sing.val={_sv[-1]:.4f}; "
          f">~50 => near-singular, translation will be structurally hard here)")

    # ---- camera world position from the RELIABLE wrist state (cam.data.pos_w lags) ----
    MOUNT_POS_T = torch.tensor(MOUNT_POS, dtype=torch.float32, device=device)
    zeros_v = torch.zeros((1, len(arm_ids)), device=device)

    def cam_pos_w():
        wp = robot.data.body_pos_w[0, wrist_bi]
        Rww = math_utils.matrix_from_quat(robot.data.body_quat_w[0, wrist_bi].unsqueeze(0))[0]
        return wp + Rww @ MOUNT_POS_T

    def goto(q, settle):
        robot.write_joint_state_to_sim(q.unsqueeze(0), zeros_v, joint_ids=arm_ids)
        act[0, :6] = (q - default_q[0]) / scale
        for _ in range(settle):
            env.step(act)

    def probe_J(q_about):
        """Finite-difference image Jacobian ds = J @ dc about joint config q_about. Probes two
        camera axes, measuring the ACTUAL camera-plane displacement each time (so it tolerates
        the arm not moving purely along the command), then restores q_about. None if degenerate."""
        DS, DC = [], []
        for axis in (0, 1):
            pr, got = 0.012, False
            for _try in range(3):
                goto(q_about, 10)
                s0 = detect_cube(rgb_now()); c0 = cam_pos_w().clone(); R0 = R_world_cam()
                if s0[0] is None:
                    break
                mv = [0.0, 0.0, 0.0]; mv[axis] = pr
                step_cam_move(mv, hold=12, cap=0.05)
                s1 = detect_cube(rgb_now()); c1 = cam_pos_w().clone()
                if s1[0] is not None:
                    dc = (R0.transpose(0, 1) @ (c1 - c0))[:2].cpu().numpy()
                    DS.append(np.array(s1[:2]) - np.array(s0[:2])); DC.append(dc)
                    got = True; break
                pr *= 0.5
            if not got:
                goto(q_about, 6); return None
        goto(q_about, 6)
        DCm = np.column_stack(DC); DSm = np.column_stack(DS)
        if abs(np.linalg.det(DCm)) < 1e-6:
            return None
        return DSm @ np.linalg.inv(DCm)

    q_start = robot.data.joint_pos[0, arm_ids].clone()
    J = probe_J(q_start)
    if J is None:
        print("[abort] no usable image Jacobian at the start pose (cube left view, or the arm "
              "can't translate the camera in 2D here). Try a different HOVER_Q.")
        env.close(); return
    print(f"[probe] image Jacobian J=\n{np.array2string(J, precision=1)}")
    Jinv = np.linalg.inv(J)

    # ---- SERVO: small proportional steps; re-measure J periodically (it drifts as the camera
    #      approaches); stop if the cube nearly fills the frame (approach guard) or it centres.
    goto(q_start, 4)
    n_start = max(detect_cube(rgb_now())[2], 1)
    log = []
    for k in range(args_cli.steps):
        u, v, n = detect_cube(rgb_now())
        if u is None:
            print(f"[{k:03d}] cube lost from view — stopping."); break
        e = np.array([u, v]) - s_target
        err = float(np.hypot(*e))
        log.append(err)
        if k % 10 == 0:
            optz = float(R_world_cam()[2, 2])                  # optical-axis world-z: constant => orientation held
            print(f"[{k:03d}] centroid=({u:.1f},{v:.1f})  err_px={err:.1f}  npx={n}  optz={optz:.3f}")
        if err < 6.0:
            print(f"[{k:03d}] converged: err_px={err:.1f}"); break
        if n > 10 * n_start:
            print(f"[{k:03d}] approach guard: cube nearly fills frame (npx={n}) — stopping."); break
        if k > 0 and k % 20 == 0:                              # occasional re-linearise (arm is well-conditioned)
            Jn = probe_J(robot.data.joint_pos[0, arm_ids].clone())
            if Jn is not None:
                J, Jinv = Jn, np.linalg.inv(Jn)
        # Proportional servo with TINY, bounded steps: the arm is well-conditioned (cond ~9), so
        # small moves track cleanly and the step shrinks with the error -> no overshoot ringing.
        d_cam = -0.15 * (Jinv @ e)                             # proportional: auto-slows near the target
        d_cam = np.clip(d_cam, -0.002, 0.002)                 # tiny steps -> no overshoot / no arc-dive
        step_cam_move([float(d_cam[0]), float(d_cam[1]), 0.0], hold=5, cap=0.004)

    _save_png(os.path.join(out_dir, "debug_end.png"),
              _mark(np.ascontiguousarray(rgb_now()).copy(), *detect_cube(rgb_now())[:2]))
    if log:
        print(f"\n[result] err_px: start={log[0]:.1f} -> min={min(log):.1f} -> end={log[-1]:.1f}  "
              f"({'CONVERGED' if min(log) < 8 else 'reduced but not centred — lower --gain'})")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
