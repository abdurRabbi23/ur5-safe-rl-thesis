# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Ready-pose geometry probe for the RH-P12-RN env (no policy, zero actions).

WHY: `TCP_OFFSET` moved 0.085 -> 0.130 after the grasp-sweep calibration. That pushed the
RL reach target 4.5 cm further out along wrist +z. The grasp sweep only ever proved the
gripper can hold a cube that was TELEPORTED between its pads — it never checked that the
reach target the reward function actually chases is somewhere the arm can usefully go.

If the reach frame now sits below the table, inside the gripper mesh, or far from where
the cube spawns, the reach reward is unlearnable and PPO will never discover a grasp no
matter how long it trains. That failure looks exactly like "the robot can't grasp".

This is the cheap check to run before spending GPU hours.

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/rhp12_geometry_check.py \
        --task Isaac-Lift-Cube-UR5e-RHP12-Play-v0 --num_envs 1

Drop --headless to watch; the ee_frame marker is already enabled in the env cfg.

It probes TWICE — fingers open, then fingers closed. The RH-P12-RN fingers curl forward
as they close, so the grasp centre travels ~0.077 -> ~0.105 m along wrist +z. TCP_OFFSET
is a CLOSING TCP and is only meaningful against the closed pose; the open-pose numbers
are printed for context, not for judging it. The r2/l2 body origins used here also sit
behind the flat contact faces, so ee_frame is expected to LEAD them slightly.

The authoritative calibration remains the contact test in results/rhp12_grasp_sweep.txt.
If this probe and that sweep disagree, the sweep wins — this script cannot see contact.
What this script alone decides is BLOCKING: is the reach target above the table, and is
the cube a sane distance away.
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

parser = argparse.ArgumentParser(description="RH-P12-RN ready-pose geometry probe.")
parser.add_argument("--disable_fabric", action="store_true", default=False)
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--task", type=str, default="Isaac-Lift-Cube-UR5e-RHP12-Play-v0")
parser.add_argument("--steps", type=int, default=40, help="settle steps before probing")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import gymnasium as gym
import torch

from isaaclab.utils.math import subtract_frame_transforms

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg

import ur5_grasp.tasks  # noqa: F401
from ur5_grasp.robots.ur5e_rhp12 import GRIPPER_JOINT_NAMES, TCP_OFFSET

REPORT = os.path.normpath(os.path.join(_HERE, "..", "..", "results", "rhp12_geometry_check.txt"))


def report(env, fh, phase):
    """Measure the ready-pose geometry once, for the current finger configuration."""

    def log(msg=""):
        print(msg, flush=True)
        fh.write(msg + "\n")

    inner = env.unwrapped
    robot = inner.scene["robot"]
    obj = inner.scene["object"]
    ee = inner.scene["ee_frame"]

    names = list(robot.data.body_names)
    r2 = names.index("rh_p12_rn_r2")
    l2 = names.index("rh_p12_rn_l2")
    wi = names.index("wrist_3_link")
    bi = names.index("base_link")

    bp = robot.data.body_pos_w[0]
    bq = robot.data.body_quat_w[0]

    pad_mid = 0.5 * (bp[r2] + bp[l2])          # r2/l2 BODY ORIGINS, not the pad faces
    wrist_pos, wrist_quat = bp[wi], bq[wi]
    ee_pos = ee.data.target_pos_w[0, 0]        # what the reach reward chases
    cube = obj.data.root_pos_w[0]
    base = bp[bi]

    off_local, _ = subtract_frame_transforms(
        wrist_pos.unsqueeze(0), wrist_quat.unsqueeze(0), pad_mid.unsqueeze(0)
    )
    off_local = off_local[0]

    gj, _ = robot.find_joints(GRIPPER_JOINT_NAMES)   # by NAME: joint order is interleaved
    q = robot.data.joint_pos[0, gj]

    frame_err = torch.norm(ee_pos - pad_mid).item()
    reach_to_cube = torch.norm(ee_pos - cube).item()
    pads_to_cube = torch.norm(pad_mid - cube).item()

    p = lambda t: "[" + ", ".join(f"{v:+.3f}" for v in t.tolist()) + "]"
    log("-" * 74)
    log(f" PADS {phase}")
    log("-" * 74)
    log(f" gripper q (rh_p12_rn, rh_r2, rh_l1, rh_l2) : {p(q)}")
    log(f" arm base_link (world)             : {p(base)}")
    log(f" wrist_3_link (world)              : {p(wrist_pos)}")
    log(f" pad-ORIGIN midpoint (world)       : {p(pad_mid)}")
    log(f" RL reach target, ee_frame (world) : {p(ee_pos)}")
    log(f" cube (world)                      : {p(cube)}")
    log("")
    log(f" >> ee_frame vs pad-origin midpoint: {frame_err:.4f} m")
    log(f" >> ee_frame  -> cube distance     : {reach_to_cube:.4f} m")
    log(f" >> pad midpt -> cube distance     : {pads_to_cube:.4f} m")
    log(f" >> ee_frame height above table    : {ee_pos[2].item():+.4f} m")
    log(f" >> pad-origin offset along wrist  : {p(off_local)}")
    log("")

    return {
        "frame_err": frame_err,
        "reach_to_cube": reach_to_cube,
        "ee_z": ee_pos[2].item(),
        "off_local": off_local,
        "off_z": off_local[2].item(),
    }


def verdict(open_s, closed_s, fh):
    """Decide PASS/FAIL. Read the header carefully before acting on this."""

    def log(msg=""):
        print(msg, flush=True)
        fh.write(msg + "\n")

    travel = closed_s["off_z"] - open_s["off_z"]

    log("=" * 74)
    log(" VERDICT")
    log("=" * 74)
    log(" WHY TWO MEASUREMENTS: the RH-P12-RN fingers CURL FORWARD as they close, so")
    log(" the grasp centre is not a fixed point on the wrist axis. It travels")
    log(f" {open_s['off_z']:.4f} m (open) -> {closed_s['off_z']:.4f} m (closed), i.e. {travel:+.4f} m.")
    log(" TCP_OFFSET is therefore a CLOSING TCP and must only ever be compared against")
    log(" the CLOSED pad geometry. Comparing it against the open pose is apples to")
    log(" oranges and will look like a large error when nothing is wrong.")
    log("")
    log(" ALSO: pad_mid here is the r2/l2 BODY ORIGIN midpoint, which sits behind the")
    log(" flat contact faces. Expect ee_frame to lead it by roughly the pad half-depth.")
    log(" The authoritative calibration is the CONTACT evidence in")
    log(" results/rhp12_grasp_sweep.txt (face_gap 0.0413 m vs a 0.0412 m cube at")
    log(" TCP_OFFSET = 0.130). If this script and that sweep disagree, THE SWEEP WINS.")
    log("")

    checks = []

    ok_frame = closed_s["frame_err"] < 0.03
    checks.append(ok_frame)
    log(f" [{'PASS' if ok_frame else 'CHECK'}] ee_frame vs CLOSED pad origins"
        f" : {closed_s['frame_err']:.4f} m   (want < 0.03)")
    if not ok_frame:
        log("        -> Not automatically a bug. Re-derive TCP_OFFSET with")
        log("           scripts/rhp12_grasp_sweep.py (contact test) before changing it.")
        log("           Do NOT paste the offset vector above into the env cfg blind:")
        log("           it targets the body origins, not the contact faces, and")
        log("           0.130 is already an empirically HELD value.")

    ok_z = closed_s["ee_z"] > 0.02
    checks.append(ok_z)
    log(f" [{'PASS' if ok_z else 'FAIL'}] ee_frame height above table"
        f"      : {closed_s['ee_z']:+.4f} m   (want > 0.02)")
    if not ok_z:
        log("        -> BLOCKING. The reach target is in or under the table. The reach")
        log("           reward is unlearnable; PPO will never find a grasp. Fix the")
        log("           ready pose or TCP_OFFSET before spending GPU hours.")

    ok_reach = 0.05 < closed_s["reach_to_cube"] < 0.60
    checks.append(ok_reach)
    log(f" [{'PASS' if ok_reach else 'FAIL'}] ee_frame -> cube distance"
        f"        : {closed_s['reach_to_cube']:.4f} m   (want 0.05 - 0.60)")
    if not ok_reach:
        log("        -> BLOCKING. Either the cube spawns on top of the gripper, or it")
        log("           is near the UR5e's ~0.85 m reach limit. Move the cube spawn.")

    log("")
    blocking_ok = ok_z and ok_reach
    log(" >> " + ("CLEARED FOR TRAINING." if blocking_ok else "DO NOT TRAIN YET.")
        + ("" if ok_frame else "  (frame_err flagged - read the note above, it may be fine.)"))
    log("=" * 74)


def main():
    env_cfg = parse_env_cfg(
        args_cli.task, device=args_cli.device, num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env = gym.make(args_cli.task, cfg=env_cfg)

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    fh = open(REPORT, "w")

    fh.write("=" * 74 + "\n")
    fh.write("RH-P12-RN READY-POSE GEOMETRY\n")
    fh.write(f"TCP_OFFSET in use : {TCP_OFFSET:.3f} m\n")
    fh.write("=" * 74 + "\n")
    print(f"\nRH-P12-RN READY-POSE GEOMETRY  (TCP_OFFSET = {TCP_OFFSET:.3f} m)\n", flush=True)

    with torch.inference_mode():
        env.reset()
        act = torch.zeros(env.action_space.shape, device=env.unwrapped.device)

        # BinaryJointPositionAction masks on (action < 0) -> CLOSE. So a zero action
        # leaves the gripper OPEN. Arm entries stay 0 => default ready pose throughout.
        for _ in range(args_cli.steps):
            env.step(act)
        open_s = report(env, fh, "OPEN (gripper action >= 0)")

        act[:, -1] = -1.0
        for _ in range(args_cli.steps):
            env.step(act)
        closed_s = report(env, fh, "CLOSED (gripper action < 0)")

        verdict(open_s, closed_s, fh)

    fh.close()
    print(f"\n[saved to {REPORT}]")

    # keep the viewer alive if running with the GUI so the frame marker can be inspected
    if not args_cli.headless:
        with torch.inference_mode():
            while simulation_app.is_running():
                env.step(act)

    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
