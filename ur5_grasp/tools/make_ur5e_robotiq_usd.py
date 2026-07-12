# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Build + validate a single-articulation UR5e + Robotiq 2f-85 USD.

Why: the stock ur5e.usd 'Robotiq_2f_85' variant declares its OWN articulation root
(/ur5e/Gripper/Robotiq_2F_85) next to the arm root (/ur5e/root_joint). Isaac Lab
requires exactly one articulation per robot, so it refuses to load it.

Fix (standard USD surgery): author a thin local USD that references ur5e.usd, selects
the gripper variant, and DISABLES the gripper's nested articulation root. PhysX then
folds the gripper bodies into the arm articulation across the existing fixed mount joint
(robot_gripper_joint), giving one articulation whose joints include finger_joint.

The script writes that USD, then spawns it to confirm a single articulation and prints
the final joint/body names Isaac Lab sees (authoritative input for the robot config).

Run on the lab PC (isaaclab env), headless:

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/tools/make_ur5e_robotiq_usd.py --headless

Output: ur5_grasp/assets/ur5e_robotiq_2f85.usd  +  tools/make_usd_report.txt
"""

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Build + validate UR5e + Robotiq 2f-85 USD.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- after app is up -------------------------------------------------------------
import os

from pxr import PhysxSchema, Usd, UsdGeom, UsdPhysics

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import Articulation, ArticulationCfg
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.normpath(os.path.join(HERE, "..", "assets"))
OUT_USD = os.path.join(ASSETS_DIR, "ur5e_robotiq_2f85.usd")
REPORT_PATH = os.path.join(HERE, "make_usd_report.txt")

SRC_USD = f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e.usd"
GRIPPER_PRIM = "/Robot/Gripper/Robotiq_2F_85"  # nested articulation root to disable

_FH = open(REPORT_PATH, "w")


def log(msg: str = "") -> None:
    print(msg, flush=True)
    _FH.write(msg + "\n")
    _FH.flush()


def build_usd() -> None:
    """Author the local wrapper USD: reference ur5e, pick variant, disable gripper root."""
    os.makedirs(ASSETS_DIR, exist_ok=True)
    if os.path.exists(OUT_USD):
        os.remove(OUT_USD)

    stage = Usd.Stage.CreateNew(OUT_USD)
    robot = UsdGeom.Xform.Define(stage, "/Robot").GetPrim()
    robot.GetReferences().AddReference(SRC_USD)
    stage.SetDefaultPrim(robot)

    # Select variants on the referenced asset (exposed on /Robot).
    vsets = robot.GetVariantSets()
    for name, sel in {"Physics": "PhysX", "Gripper": "Robotiq_2f_85", "Sensor": "None"}.items():
        if name in vsets.GetNames():
            vsets.GetVariantSet(name).SetVariantSelection(sel)
            log(f"    variant {name} -> {sel}")

    # Disable the gripper's nested articulation root so arm+gripper = one articulation.
    grip = stage.GetPrimAtPath(GRIPPER_PRIM)
    if not grip or not grip.IsValid():
        log(f"    !! gripper prim not found at {GRIPPER_PRIM} — variant may differ; aborting build")
        return
    removed = grip.RemoveAPI(UsdPhysics.ArticulationRootAPI)
    log(f"    removed UsdPhysics.ArticulationRootAPI from gripper: {removed}")
    # Belt-and-suspenders: also flag PhysX articulation disabled on that prim.
    px = PhysxSchema.PhysxArticulationAPI.Apply(grip)
    px.CreateArticulationEnabledAttr(False)
    log("    set physxArticulation:articulationEnabled = False on gripper")

    stage.GetRootLayer().Save()
    log(f"    wrote {OUT_USD}")


def validate_usd() -> None:
    """Spawn the built USD and confirm a single articulation; dump joint/body names."""
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=0.01, device=args_cli.device))
    sim_utils.GroundPlaneCfg().func("/World/ground", sim_utils.GroundPlaneCfg())
    sim_utils.DomeLightCfg(intensity=2000.0).func("/World/Light", sim_utils.DomeLightCfg(intensity=2000.0))

    robot = Articulation(
        ArticulationCfg(
            prim_path="/World/Robot",
            spawn=sim_utils.UsdFileCfg(usd_path=OUT_USD),
            actuators={"all": ImplicitActuatorCfg(joint_names_expr=[".*"], stiffness=None, damping=None)},
        )
    )
    sim.reset()

    log("    SUCCESS: loaded as a single articulation.")
    log(f"    num joints : {robot.num_joints}")
    log(f"    joint names: {list(robot.joint_names)}")
    log(f"    num bodies : {robot.num_bodies}")
    log(f"    body names : {list(robot.body_names)}")


def main() -> None:
    log("=" * 70)
    log("BUILD + VALIDATE  ur5e_robotiq_2f85.usd")
    log("=" * 70)
    log(f"source USD : {SRC_USD}")
    log(f"output USD : {OUT_USD}")
    log("")
    log("--- 1. Authoring local USD ---")
    build_usd()
    log("")
    log("--- 2. Validating single articulation ---")
    try:
        validate_usd()
    except Exception:  # noqa: BLE001
        import traceback

        log("    !! validation failed — traceback below:")
        log(traceback.format_exc())
    log("")
    log(f"[report saved to {REPORT_PATH}]")


if __name__ == "__main__":
    try:
        main()
    finally:
        _FH.close()
        simulation_app.close()
