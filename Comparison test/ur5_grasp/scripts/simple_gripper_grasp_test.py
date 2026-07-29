# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Confound-free contact-grasp test for the new simple two-finger gripper.

Adapted from `grasp_lift_test.py` (the Robotiq contact-grasp diagnostic) for the two
independent prismatic joints authored in `make_ur5e_simple_gripper_usd.py`. Same
methodology, because the confound it guards against is generic to any contact grasp
test, not specific to the Robotiq asset:

  * while the fingers close, rewrite the cube's pose to the TCP BEFORE each
    physics step. The collider is then present when the fingers push, so if the pads
    make real contact the finger drive STALLS at the cube's width (no free-fall, no
    ratchet). If instead both joints run all the way to their closed target, the pads
    genuinely passed through — the failure mode `check_gripper_colliders.py` found on
    the Robotiq asset.
  * then STOP pinning and watch: if the grip holds the cube by friction it stays up;
    if it slips it falls -> tune pad friction / stiffness / effort limits.

Also prints the exact LOCAL wrist_3->TCP offset measured in sim, against what
`robots/gripper_geometry.py` says it should be, so a mismatch between the authored asset
and what PhysX actually resolved shows up as a number instead of as a confusing grasp
failure. (Rounds 2 and 3 of the gripper build were both exactly that kind of mismatch.)

Day 21 change: the cube is now pinned at the TCP taken from the env's `ee_frame` sensor —
the grasp point between the finger TIPS — not at the mean of the two finger BODY origins
as before. Those used to coincide; they no longer do. Each finger's body origin now sits
at its prismatic joint anchor, level with the mounting plate, with the finger box offset
forward as a child prim (see `make_ur5e_simple_gripper_usd.py`, "Fix, round 3"). Pinning
at the body-origin midpoint would drop the cube inside the mounting plate.

Run on the lab PC (isaaclab env):

    cd ~/Abdur_Rabbi_THESIS/"Comparison test"
    ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/simple_gripper_grasp_test.py \
        --task Isaac-Lift-Cube-UR5e-SimpleGripper-Play-v0 --num_envs 1
"""

import argparse
import os
import sys

from isaaclab.app import AppLauncher

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

parser = argparse.ArgumentParser(description="Simple-gripper pinned-close hold test.")
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--task", type=str, default="Isaac-Lift-Cube-UR5e-SimpleGripper-Play-v0")
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
from ur5_grasp.robots import gripper_geometry as G  # noqa: E402

try:
    from isaaclab.utils.math import quat_rotate_inverse
except Exception:  # noqa: BLE001
    quat_rotate_inverse = None

# --------------------------------------------------------------------------------------
# Flushed report file (Day 22). This script previously only print()ed — 17 calls, no file.
#
# That is the Day-21 trap, and it bit again: `simulation_app.close()` tears the process down
# without flushing block-buffered stdout, piping to capture the output is what CAUSES the
# buffering, and nothing readable survives either way. The demo lost a whole session to this
# and every tool in tools/ already writes a flushed report. This script did not, so its
# result could not be read back at all — which is indistinguishable, from the outside, from
# the run having failed.
#
# log() = print + write + flush, the same helper the builders use. Read the FILE.
# --------------------------------------------------------------------------------------
REPORT_PATH = os.path.normpath(
    os.path.join(_HERE, "..", "tools", "simple_gripper_grasp_report.txt")
)
_FH = open(REPORT_PATH, "w")


def log(msg: str = "") -> None:
    print(msg, flush=True)
    _FH.write(msg + "\n")
    _FH.flush()


PLACE_AT = 30       # open + settle, then place the cube at the pad midpoint
STOP_PIN = 90       # fingers fully closed (or stalled on the cube) by now -> release
HOLD_UNTIL = 230


def main() -> None:
    # PROGRESS logging at every stage, so a run that dies says WHERE. The live demo died
    # in scene construction for three sessions and looked, from outside, exactly like a
    # run that had worked and been closed early. Stage lines make those distinguishable.
    log("=" * 78)
    log("SIMPLE GRIPPER — pinned-close contact grasp test")
    log("=" * 78)
    log(f"task     : {args_cli.task}   num_envs: {args_cli.num_envs}")
    log(f"report   : {REPORT_PATH}")
    log("")
    log("--- resolved geometry (robots/gripper_geometry.py) ---")
    log(G.summary())
    log("")

    log("[progress] parsing env cfg ...")
    env_cfg = parse_env_cfg(
        args_cli.task, device=args_cli.device, num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    log("[progress] gym.make ... (scene construction happens here)")
    env = gym.make(args_cli.task, cfg=env_cfg)
    log("[progress] env.reset ...")
    env.reset()
    log("[progress] scene up.")

    scene = env.unwrapped
    obj = scene.scene["object"]
    robot = scene.scene["robot"]
    device = scene.device
    N = scene.num_envs

    bnames = list(robot.body_names)
    log(f"[progress] body names : {bnames}")
    log(f"[progress] joint names: {list(robot.joint_names)}")
    pad_ids = [i for i, n in enumerate(bnames) if n in ("left_finger", "right_finger")]
    wrist_ids = [i for i, n in enumerate(bnames) if n == "wrist_3_link"]
    # Our gripper mount box was named "base_link" at authoring time, but the ARM already
    # has its own body called "base_link" -> Isaac Lab auto-disambiguates ours to
    # "base_link_0" (same auto-rename check_gripper_mount.py flagged for the old Robotiq
    # asset). Must reference it by the disambiguated name, not the one we wrote in the USD.
    mount_ids = [i for i, n in enumerate(bnames) if n == "base_link_0"]
    # The env's own end-effector frame = the grasp point the reward function uses.
    ee_frame = scene.scene["ee_frame"] if "ee_frame" in scene.scene.keys() else None
    jnames = list(robot.joint_names)
    left_id = jnames.index("left_finger_joint")
    right_id = jnames.index("right_finger_joint")

    if len(pad_ids) != 2:
        log(f"!! expected 2 pad bodies (left_finger, right_finger), found {len(pad_ids)}: "
              f"{[bnames[i] for i in pad_ids]}. Body list: {bnames}")
    if not mount_ids:
        log(f"!! could not find gripper mount body 'base_link_0'. Body list: {bnames}")

    act = torch.zeros(env.action_space.shape, device=device)
    pinned_pose = None
    place_pt = None
    placed = False

    step = 0
    while simulation_app.is_running() and step <= HOLD_UNTIL:
        with torch.inference_mode():
            # gripper_action is a single binary scalar (last action dim): +1 = OPEN,
            # -1 = CLOSE, mapped through open/close_command_expr for BOTH finger
            # joints at once (ur5e_simple_gripper_env_cfg.py). Same convention the
            # Robotiq contact test used.
            act[:] = 0.0
            act[:, -1] = +1.0 if step < PLACE_AT else -1.0

            # pin the cube in place BEFORE stepping, so it's a present obstacle
            if placed and pinned_pose is not None and step < STOP_PIN:
                obj.write_root_pose_to_sim(pinned_pose)
                obj.write_root_velocity_to_sim(torch.zeros((N, 6), device=device))
            elif placed and step == STOP_PIN:
                log(f"\n[step {step}] pin released — grip must now hold the cube alone\n")

            env.step(act)
            step += 1

            if not placed and step == PLACE_AT:
                # THE GRASP POINT, straight from the env's own ee_frame sensor — i.e. the
                # exact frame the reward function uses, so this test can never drift away
                # from what training sees. Falls back to the finger-body midpoint only if
                # the env has no ee_frame, which would itself be worth knowing about.
                if ee_frame is not None:
                    tcp = ee_frame.data.target_pos_w[0, 0]
                else:
                    log("!! no ee_frame in this env — falling back to the finger-body "
                          "midpoint, which is NOT the grasp point. Treat the result as "
                          "indicative only.")
                    tcp = robot.data.body_pos_w[0, pad_ids].mean(dim=0)
                place_pt = tcp.clone()
                pinned_pose = torch.zeros((N, 7), device=device)
                pinned_pose[:, 0:3] = tcp
                pinned_pose[:, 3] = 1.0
                obj.write_root_pose_to_sim(pinned_pose)
                obj.write_root_velocity_to_sim(torch.zeros((N, 6), device=device))
                placed = True
                if wrist_ids and quat_rotate_inverse is not None:
                    w_pos = robot.data.body_pos_w[0, wrist_ids[0]]
                    w_quat = robot.data.body_quat_w[0, wrist_ids[0]]
                    local = quat_rotate_inverse(w_quat.unsqueeze(0), (tcp - w_pos).unsqueeze(0))[0]
                    log(f"[local offset] measured wrist_3->TCP = "
                          f"[{local[0]:+.4f}, {local[1]:+.4f}, {local[2]:+.4f}] m")
                    log(f"[local offset] geometry says it should be "
                          f"{[round(v, 4) for v in G.TCP_OFFSET_POS]} m "
                          f"(TCP_Z {G.TCP_Z:.3f} along the measured tool axis "
                          f"{G.TOOL_AXIS.tolist()})")

                    # Split the offset at the mount, so a mismatch points at ONE joint:
                    # wrist_3 -> mount plate is the FixedJoint; mount -> finger origin is
                    # the two PrismaticJoints. Round 2 was diagnosed exactly this way.
                    if mount_ids:
                        m_pos = robot.data.body_pos_w[0, mount_ids[0]]
                        m_quat = robot.data.body_quat_w[0, mount_ids[0]]
                        wrist_to_mount = quat_rotate_inverse(w_quat.unsqueeze(0), (m_pos - w_pos).unsqueeze(0))[0]
                        mount_to_tcp = quat_rotate_inverse(m_quat.unsqueeze(0), (tcp - m_pos).unsqueeze(0))[0]
                        log(f"[segment] wrist_3->mount (base_link_0) = "
                              f"[{wrist_to_mount[0]:+.4f}, {wrist_to_mount[1]:+.4f}, {wrist_to_mount[2]:+.4f}] m "
                              f"(expect {[round(v, 4) for v in G.MOUNT_POS]}, the FixedJoint)")
                        log(f"[segment] mount->TCP, in the GRIPPER's own frame = "
                              f"[{mount_to_tcp[0]:+.4f}, {mount_to_tcp[1]:+.4f}, {mount_to_tcp[2]:+.4f}] m "
                              f"(expect [0, 0, {G.TCP_Z - G.MOUNT_CENTER_Z:+.4f}] — pure +Z, "
                              f"since the gripper frame's +Z IS the approach axis)")
                log(f"\n[placed cube at TCP z={place_pt[2]:.3f}] closing (pinned)...\n")

            if placed and step % 10 == 0:
                cz = obj.data.root_pos_w[0, 2].item()
                pz = place_pt[2].item()
                phase = "pinned" if step < STOP_PIN else "HOLD"
                held = "HELD" if (cz > pz - 0.05) else "DROPPED"
                lj = robot.data.joint_pos[0, left_id].item()
                rj = robot.data.joint_pos[0, right_id].item()
                if len(pad_ids) == 2:
                    pads = robot.data.body_pos_w[0, pad_ids]
                    gap = torch.norm(pads[0] - pads[1]).item()
                else:
                    gap = float("nan")
                log(f"  step {step:4d} [{phase:6}] cube z={cz:+.3f} (pad {pz:+.3f}) {held}"
                      f" | left={lj:+.4f} right={rj:+.4f} | pad gap={gap*1000:5.1f} mm")

    cz = obj.data.root_pos_w[0, 2].item()
    pz = place_pt[2].item() if place_pt is not None else 0.0
    lj = robot.data.joint_pos[0, left_id].item()
    rj = robot.data.joint_pos[0, right_id].item()
    log("\n================= SIMPLE GRIPPER CONTACT GRASP RESULT =================")
    log(f" left_finger_joint={lj:+.4f}  right_finger_joint={rj:+.4f}")
    log(" (both near 0 = pads closed all the way through, no obstruction; either")
    log("  stalled well short of 0 = pads clamped the cube -> real contact)")
    if cz > pz - 0.05:
        log(f" cube held at z={cz:+.3f} (pad {pz:+.3f}) after release -> GRIP HOLDS")
    else:
        log(f" cube fell to z={cz:+.3f} (pad {pz:+.3f}) after release -> slips / no clamp")
    log("=========================================================================\n")

    env.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        # Log the traceback INTO the report file. stderr survives redirection (it stays
        # line-buffered) but stdout does not, and there is no reason to depend on which
        # stream the reader happened to capture. A run that raises now says so in the file.
        import traceback

        log("!! test failed — traceback below:")
        log(traceback.format_exc())
    finally:
        log(f"[report saved to {REPORT_PATH}]")
        _FH.close()
        simulation_app.close()
