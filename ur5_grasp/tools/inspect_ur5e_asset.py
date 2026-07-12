# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Inspect the UR5e asset on the Nucleus server.

Purpose: before scaffolding the grasp env we must know, for THIS machine's asset
library, (1) which ur5e USD path actually resolves, (2) whether a Robotiq gripper
variant is present, and (3) the real joint + body names of the articulation.
Guessing these is the #1 cause of a broken env config, so we read them directly.

Run on the lab PC (conda env `isaaclab` active), headless:

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/tools/inspect_ur5e_asset.py --headless

It prints a report and also writes it to ur5_grasp/tools/ur5e_asset_report.txt.
Paste that file back to me (or the console output) and I'll write the configs.
"""

import argparse

from isaaclab.app import AppLauncher

# --- launch Isaac Sim (headless) -------------------------------------------------
parser = argparse.ArgumentParser(description="Inspect UR5e asset for the grasp env.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- everything below runs only after the app is up ------------------------------
import os

import omni.client
from pxr import Usd, UsdPhysics

from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR, ISAACLAB_NUCLEUS_DIR

REPORT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ur5e_asset_report.txt")
_REPORT_FH = open(REPORT_PATH, "w")  # write-through so a segfault can't swallow output


def log(msg: str = "") -> None:
    print(msg, flush=True)
    _REPORT_FH.write(msg + "\n")
    _REPORT_FH.flush()


# Candidate USD paths to test, in order of likelihood. UR10e lives at
# {ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur10e/ur10e.usd, so ur5e should mirror it.
CANDIDATES = [
    f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e.usd",
    f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/UR5e/ur5e.usd",
    f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e_instanceable.usd",
    f"{ISAACLAB_NUCLEUS_DIR}/Robots/UniversalRobots/UR5e/ur5e_instanceable.usd",
    f"{ISAACLAB_NUCLEUS_DIR}/Robots/UniversalRobots/UR5/ur5_instanceable.usd",
    f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5/ur5.usd",
]


def path_exists(url: str) -> bool:
    """Return True if the USD resolves on the (possibly remote) asset server."""
    try:
        result, _ = omni.client.stat(url)
        return result == omni.client.Result.OK
    except Exception as exc:  # noqa: BLE001
        log(f"    (stat error: {exc})")
        return False


def report_variants(usd_path: str) -> None:
    """List any variant sets (e.g. a 'Gripper' variant) on the root prim."""
    try:
        stage = Usd.Stage.Open(usd_path)
        if stage is None:
            log("    could not open stage to read variants")
            return
        root = stage.GetDefaultPrim() or stage.GetPseudoRoot()
        vsets = root.GetVariantSets()
        names = vsets.GetNames()
        if not names:
            log("    variant sets: none (gripper likely a separate USD / must be attached)")
            return
        for vs_name in names:
            vs = vsets.GetVariantSet(vs_name)
            log(f"    variant set '{vs_name}': options = {vs.GetVariantNames()}")
    except Exception as exc:  # noqa: BLE001
        log(f"    variant read error: {exc}")


def main() -> None:
    log("=" * 70)
    log("UR5e ASSET INSPECTION REPORT")
    log("=" * 70)
    log(f"ISAAC_NUCLEUS_DIR    = {ISAAC_NUCLEUS_DIR}")
    log(f"ISAACLAB_NUCLEUS_DIR = {ISAACLAB_NUCLEUS_DIR}")
    log("")

    log("--- 1. Resolving candidate USD paths ---")
    found_path = None
    for cand in CANDIDATES:
        ok = path_exists(cand)
        log(f"  [{'FOUND' if ok else '  -  '}] {cand}")
        if ok and found_path is None:
            found_path = cand
    log("")

    if found_path is None:
        log("No candidate UR5e USD resolved. Next step: browse the asset library at")
        log(f"  {ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/  and report the folder names,")
        log("or we import a UR5e URDF->USD manually. Stopping here.")
        return

    log(f"--- 2. Variant sets on {found_path} ---")
    report_variants(found_path)
    log("")

    log("--- 3. USD structure WITH gripper (Gripper=Robotiq_2f_85) ---")
    log("    (pure USD traversal — no physics sim, so the 'single articulation'")
    log("     constraint doesn't apply; this just enumerates the composed tree)")
    try:
        dump_usd_structure(found_path, variants={"Physics": "PhysX", "Gripper": "Robotiq_2f_85"})
    except Exception:  # noqa: BLE001
        import traceback

        log("    !! traversal failed — traceback below:")
        log(traceback.format_exc())
    log("")

    log("--- What I need from this report ---")
    log("  * gripper joint name(s) (revolute) + their limits -> open/close positions")
    log("  * which prim/link the gripper mounts on (arm flange: tool0 / wrist_3_link / ee_link)")
    log("  * where each articulation root sits (to plan merging arm+gripper into one)")
    log("")
    log(f"[report saved to {REPORT_PATH}]")


def dump_usd_structure(usd_path: str, variants: dict) -> None:
    """Open the USD with variant selections applied and list joints, links, roots."""
    stage = Usd.Stage.Open(usd_path)
    if stage is None:
        log("    could not open stage")
        return
    root = stage.GetDefaultPrim() or stage.GetPseudoRoot()
    # Apply variant selections (e.g. enable the gripper) so composition includes them.
    vsets = root.GetVariantSets()
    for vs_name, sel in variants.items():
        if vs_name in vsets.GetNames():
            vsets.GetVariantSet(vs_name).SetVariantSelection(sel)
    log(f"    applied variants: {variants}")

    art_roots, bodies, joints = [], [], []
    for prim in stage.Traverse():
        path = prim.GetPath().pathString
        if prim.HasAPI(UsdPhysics.ArticulationRootAPI):
            art_roots.append(path)
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            bodies.append(prim.GetName())
        if prim.IsA(UsdPhysics.Joint):
            jtype = prim.GetTypeName()
            targets = []
            rel = prim.GetRelationship("physics:body1")
            if rel:
                targets = [t.pathString for t in rel.GetTargets()]
            child = targets[0].split("/")[-1] if targets else "?"
            joints.append(f"{prim.GetName()}  ({jtype} -> {child})")

    log(f"    articulation roots ({len(art_roots)}):")
    for r in art_roots:
        log(f"        {r}")
    log(f"    rigid-body links ({len(bodies)}): {bodies}")
    log(f"    joints ({len(joints)}):")
    for j in joints:
        log(f"        {j}")


if __name__ == "__main__":
    try:
        main()
    finally:
        _REPORT_FH.close()
        simulation_app.close()
