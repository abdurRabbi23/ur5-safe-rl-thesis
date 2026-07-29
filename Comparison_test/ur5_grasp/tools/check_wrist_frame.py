# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""MEASURE which local axis of `wrist_3_link` is the UR5e's tool (flange) axis.

Why this exists (Day 21). `make_ur5e_simple_gripper_usd.py` mounted the gripper along
`wrist_3_link`'s local **+Z**, and the GUI shows it sticking out sideways — 90 degrees off
the direction the flange actually faces. The +Z assumption was never measured: it was
inherited from the frozen weld env's `OffsetCfg(pos=[0, 0, 0.16])`, which is commented
"approx, tune" and could never have been caught there, because the weld env TELEPORTS the
cube to the TCP. A TCP pointing out of the side of the wrist welds a cube to a point in
mid-air and trains to 100% success exactly the same way. So the weld env is not evidence.

This script settles it by measurement instead of by recall, using two independent facts and
cross-checking them against each other:

  1. **Which axis** — the tool axis is, by definition, the axis `wrist_3_joint` rotates
     about, so it is the ONE local axis of `wrist_3_link` whose world direction does not
     change when you drive `wrist_3_joint`. Pose the arm at wrist_3 = 0, record the world
     directions of the link's local X/Y/Z; re-pose at wrist_3 = +0.7 rad, record again; the
     axis with dot product ~1.0 is the tool axis. The other two will be ~cos(0.7) = 0.76.
  2. **Which sign** — +axis or -axis. On a UR arm the last link extends along its own
     rotation axis (d6 = 99.6 mm on a UR5e), so the vector from `wrist_2_link`'s origin to
     `wrist_3_link`'s origin points OUTWARD along the tool axis. Rotate that vector into
     `wrist_3_link`'s local frame and take its sign on the axis found in step 1.

If those two disagree — i.e. the wrist_2 -> wrist_3 offset is NOT essentially parallel to
the invariant axis — the script says so loudly and refuses to write a result, rather than
writing a confident wrong number. That would mean this asset's kinematics differ from a
standard UR5e and the mount needs a human look.

Gravity is disabled for this run (`SimulationCfg(gravity=(0,0,0))`) so the arm holds
whatever joint state is written to it exactly, with no sag between the write and the read.
Nothing here is a physics test; it is a pure geometry read.

Output: `ur5_grasp/assets/wrist_frame.json`  +  `tools/check_wrist_frame_report.txt`

`robots/gripper_geometry.py` REQUIRES that JSON and refuses to import without it, so this
script must be run once before `make_ur5e_simple_gripper_usd.py` (and re-run only if the
source arm asset ever changes).

Run on the lab PC (isaaclab env), headless is fine — this prints numbers, not pictures:

    cd ~/Abdur_Rabbi_THESIS/Comparison_test
    ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/check_wrist_frame.py --headless

Then paste the report back before running the builder.
"""

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Measure the UR5e tool axis in wrist_3_link's frame.")
parser.add_argument("--probe_angle", type=float, default=0.7,
                    help="wrist_3_joint angle (rad) used for the second pose. Any value well "
                         "away from 0 and from +-pi works; 0.7 rad keeps the two non-tool axes "
                         "clearly separated (cos 0.7 = 0.76) without risking a joint limit.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- after the app is up -------------------------------------------------------------
import datetime
import json
import os

import torch

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import Articulation, ArticulationCfg
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR
from isaaclab.utils.math import quat_apply, quat_apply_inverse

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.normpath(os.path.join(HERE, "..", "assets"))
OUT_JSON = os.path.join(ASSETS_DIR, "wrist_frame.json")
REPORT_PATH = os.path.join(HERE, "check_wrist_frame_report.txt")

SRC_USD = f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e.usd"
AXIS_NAMES = ("x", "y", "z")

# A pose with the wrist clearly bent, so the three local axes of wrist_3_link point in
# three visibly different world directions and the invariant-axis test is unambiguous.
# (At the zero pose several links are axis-aligned, which makes a mis-read easier to miss.)
PROBE_POSE = {
    "shoulder_pan_joint": 0.0,
    "shoulder_lift_joint": -1.2,
    "elbow_joint": 1.4,
    "wrist_1_joint": -1.75,
    "wrist_2_joint": -1.57,
    "wrist_3_joint": 0.0,  # overwritten per-pose below
}

_FH = open(REPORT_PATH, "w")


def log(msg: str = "") -> None:
    print(msg, flush=True)
    _FH.write(msg + "\n")
    _FH.flush()


def main() -> None:
    os.makedirs(ASSETS_DIR, exist_ok=True)

    log("=" * 78)
    log("MEASURE  wrist_3_link tool axis   (UR5e, arm only)")
    log("=" * 78)
    log(f"source USD : {SRC_USD}")
    log("")

    # Gravity off: the arm then holds exactly the joint state written to it, so the two
    # poses are read with zero settling error.
    sim = sim_utils.SimulationContext(
        sim_utils.SimulationCfg(dt=0.01, device=args_cli.device, gravity=(0.0, 0.0, 0.0))
    )

    robot = Articulation(
        ArticulationCfg(
            prim_path="/World/Robot",
            spawn=sim_utils.UsdFileCfg(
                usd_path=SRC_USD,
                # Arm only — same variant selection the builder uses, so we measure the
                # exact articulation the gripper will be mounted onto.
                variants={"Physics": "PhysX", "Gripper": "None", "Sensor": "None"},
            ),
            actuators={"all": ImplicitActuatorCfg(joint_names_expr=[".*"], stiffness=800.0, damping=40.0)},
        )
    )
    sim.reset()

    names = list(robot.body_names)
    log(f"body names : {names}")
    for required in ("wrist_2_link", "wrist_3_link"):
        if required not in names:
            log(f"    !! '{required}' not in body_names — cannot measure. Aborting.")
            return
    i2 = names.index("wrist_2_link")
    i3 = names.index("wrist_3_link")

    joint_names = list(robot.joint_names)
    log(f"joint names: {joint_names}")
    log("")

    def pose_at(wrist3_angle: float):
        """Teleport the arm to PROBE_POSE with wrist_3_joint = angle, then read
        wrist_2/wrist_3 world poses. Returns (pos2, pos3, quat3)."""
        q = torch.zeros_like(robot.data.joint_pos)
        for jname, val in PROBE_POSE.items():
            if jname not in joint_names:
                raise RuntimeError(f"joint '{jname}' missing from the asset: {joint_names}")
            q[:, joint_names.index(jname)] = val
        q[:, joint_names.index("wrist_3_joint")] = wrist3_angle

        robot.write_joint_state_to_sim(q, torch.zeros_like(q))
        robot.set_joint_position_target(q)
        robot.write_data_to_sim()
        for _ in range(5):  # a few steps so the reported buffers are fully in sync
            sim.step(render=False)
            robot.update(sim.get_physics_dt())
        return (
            robot.data.body_pos_w[0, i2].clone(),
            robot.data.body_pos_w[0, i3].clone(),
            robot.data.body_quat_w[0, i3].clone(),
        )

    eye = torch.eye(3, device=robot.device)

    def axes_in_world(quat: torch.Tensor) -> torch.Tensor:
        """World-frame directions of the body's own local X, Y, Z. Rows = axes."""
        return quat_apply(quat.unsqueeze(0).expand(3, 4), eye)

    # ---- pose A: wrist_3 = 0 --------------------------------------------------------
    pos2_a, pos3_a, quat3_a = pose_at(0.0)
    axes_a = axes_in_world(quat3_a)

    # ---- pose B: wrist_3 = probe_angle ----------------------------------------------
    _, _, quat3_b = pose_at(args_cli.probe_angle)
    axes_b = axes_in_world(quat3_b)

    # ---- 1. which axis is invariant under wrist_3 rotation? -------------------------
    dots = (axes_a * axes_b).sum(dim=1)
    log(f"--- 1. invariant-axis test (wrist_3_joint: 0.0 -> {args_cli.probe_angle} rad) ---")
    for k in range(3):
        log(f"    local {AXIS_NAMES[k].upper()} : dot(before, after) = {dots[k].item():+.6f}")
    axis_idx = int(torch.argmax(dots).item())
    expected_others = float(torch.cos(torch.tensor(args_cli.probe_angle)))
    log(f"    -> invariant axis = local {AXIS_NAMES[axis_idx].upper()} "
        f"(the other two should read ~{expected_others:+.3f} = cos(probe_angle))")

    sorted_dots = torch.sort(dots, descending=True).values
    margin = (sorted_dots[0] - sorted_dots[1]).item()
    if dots[axis_idx].item() < 0.999 or margin < 0.05:
        log("")
        log("    !! INCONCLUSIVE: no axis is cleanly invariant. Either wrist_3_joint did not")
        log("       actually move between the two poses (check the joint limits / the probe")
        log("       angle), or this asset's wrist is not a simple revolute about a link axis.")
        log("       Refusing to write a result. Nothing downstream will use a guess.")
        return
    log("")

    # ---- 2. which sign points OUT of the flange? ------------------------------------
    offset_w = pos3_a - pos2_a
    dist = float(torch.linalg.norm(offset_w))
    offset_local = quat_apply_inverse(quat3_a, offset_w)
    log("--- 2. outward-sign test (vector from wrist_2_link origin to wrist_3_link origin) ---")
    log(f"    world  : {[round(v, 6) for v in offset_w.tolist()]}   (|d| = {dist:.4f} m; "
        f"a UR5e's d6 is 0.0996 m)")
    log(f"    in wrist_3_link's own frame: {[round(v, 6) for v in offset_local.tolist()]}")

    unit_local = offset_local / max(dist, 1e-9)
    alignment = float(unit_local[axis_idx])
    log(f"    component on local {AXIS_NAMES[axis_idx].upper()} = {alignment:+.6f} "
        f"(should be ~+-1.0 if the link really extends along its own rotation axis)")

    if abs(alignment) < 0.95:
        log("")
        log("    !! INCONCLUSIVE: the wrist_2 -> wrist_3 offset is NOT parallel to the")
        log("       invariant axis, so the two independent checks disagree. This asset's")
        log(f"       wrist geometry is not a standard UR5e (offset is {abs(alignment)*100:.1f}% "
            "along the tool axis).")
        log("       Refusing to write a result — decide the mount direction by eye in the GUI")
        log("       instead, then set TOOL_AXIS by hand in robots/gripper_geometry.py.")
        return

    sign = 1.0 if alignment > 0 else -1.0
    tool_axis = [0.0, 0.0, 0.0]
    tool_axis[axis_idx] = sign
    log("")

    # ---- result ---------------------------------------------------------------------
    log("=" * 78)
    log(f"RESULT: the UR5e tool axis is  {'+' if sign > 0 else '-'}{AXIS_NAMES[axis_idx].upper()}  "
        "of wrist_3_link")
    log(f"        TOOL_AXIS = {tuple(tool_axis)}")
    log("=" * 78)
    if tool_axis == [0.0, 0.0, 1.0]:
        log("NOTE: this says +Z, which is what the current asset already uses. If the gripper")
        log("      still looks sideways in the GUI, the problem is NOT the mount axis — it is")
        log("      the ROLL about it, or the finger geometry. Say so before rebuilding.")
    else:
        log("This CONTRADICTS the +Z assumption baked into the old builder and into the frozen")
        log("env's OffsetCfg(pos=[0, 0, 0.16]) — which explains the sideways gripper exactly.")
        log("The frozen weld env never caught it because a weld teleports the cube to whatever")
        log("point the TCP names, correct or not.")
    log("")

    payload = {
        "tool_axis_wrist3_link": tool_axis,
        "invariant_axis": AXIS_NAMES[axis_idx],
        "sign": sign,
        "invariant_dot_products": {AXIS_NAMES[k]: round(float(dots[k]), 6) for k in range(3)},
        "wrist2_to_wrist3_local": [round(float(v), 6) for v in offset_local.tolist()],
        "wrist2_to_wrist3_distance_m": round(dist, 6),
        "probe_angle_rad": args_cli.probe_angle,
        "source_usd": SRC_USD,
        "measured_utc": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    with open(OUT_JSON, "w") as fh:
        json.dump(payload, fh, indent=2)
    log(f"wrote {OUT_JSON}")
    log("")
    log("NEXT: rebuild the gripper asset, which now reads this file:")
    log('    ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/make_ur5e_simple_gripper_usd.py --headless')


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        import traceback

        log("!! measurement failed — traceback below:")
        log(traceback.format_exc())
    finally:
        log(f"[report saved to {REPORT_PATH}]")
        _FH.close()
        simulation_app.close()
