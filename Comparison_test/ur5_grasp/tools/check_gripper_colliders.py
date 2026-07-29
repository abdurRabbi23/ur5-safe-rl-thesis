# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Report the collision state of the Robotiq 2f-85 finger prims.

Physics-only grasp tests show the pads close straight THROUGH a cube pinned between
them (finger_joint -> 0, pad gap -> 0, no stall). The cube has a working collider
(it lands on the table), so the missing contact must be on the gripper fingers.
This script opens the built USD and, for every finger/knuckle prim, prints whether a
UsdPhysics.CollisionAPI exists, whether collision is enabled, and the mesh
approximation. If the inner-finger pads have NO enabled collider, that is the cause.

Run on the lab PC (isaaclab env), headless:

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/tools/check_gripper_colliders.py --headless
"""

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Inspect Robotiq 2f-85 finger colliders.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import os

from pxr import Usd, UsdPhysics

HERE = os.path.dirname(os.path.abspath(__file__))
USD = os.path.normpath(os.path.join(HERE, "..", "assets", "ur5e_robotiq_2f85.usd"))

KEYS = ("finger", "knuckle")


def main() -> None:
    print("=" * 78)
    print(f"COLLIDER CHECK: {USD}")
    print("=" * 78)
    stage = Usd.Stage.Open(USD)
    if stage is None:
        print("!! could not open stage")
        return

    # IMPORTANT: Isaac assets are instanceable; a plain Traverse() skips the instanced
    # geometry. TraverseInstanceProxies descends into it so we see the real meshes.
    prim_iter = iter(Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies()))

    total = 0
    gripper_hits = 0
    n_collider = 0
    n_mesh = 0
    for prim in prim_iter:
        total += 1
        path = str(prim.GetPath())
        low = path.lower()
        if "gripper" in low or "robotiq" in low:
            gripper_hits += 1
        if not any(k in low for k in KEYS):
            continue
        typ = prim.GetTypeName()
        has_col = prim.HasAPI(UsdPhysics.CollisionAPI)
        is_mesh = typ == "Mesh"
        if not (has_col or is_mesh):
            continue

        en_attr = prim.GetAttribute("physics:collisionEnabled")
        enabled = en_attr.Get() if (en_attr and en_attr.HasAuthoredValue()) else "(unset)"
        ap_attr = prim.GetAttribute("physics:approximation")
        approx = ap_attr.Get() if (ap_attr and ap_attr.HasAuthoredValue()) else "(unset)"

        tag = "COLLIDER" if has_col else "mesh-only"
        if has_col:
            n_collider += 1
        if is_mesh:
            n_mesh += 1
        print(f"  [{tag:9}] {typ:6} enabled={enabled!s:12} approx={approx!s:14} {path}")

    print("-" * 78)
    print(f"total prims traversed (incl. instances): {total}")
    print(f"prims under a Gripper/Robotiq path     : {gripper_hits}")
    print(f"finger/knuckle prims with CollisionAPI : {n_collider}")
    print(f"finger/knuckle Mesh prims total        : {n_mesh}")
    if gripper_hits == 0:
        print(">>> The gripper subtree didn't compose here — result inconclusive, not a collider verdict.")
    elif n_collider == 0 and n_mesh > 0:
        print(">>> Pads have VISUAL meshes but NO collider — this is why they pass through the cube.")
    elif n_collider == 0:
        print(">>> No finger colliders found — likely why the pads pass through the cube.")
    else:
        print(">>> Colliders exist; if grasp still fails, check collisionEnabled / approximation / contact offsets.")


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
