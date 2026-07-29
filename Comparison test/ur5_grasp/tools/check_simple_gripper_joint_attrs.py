# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Raw-USD check: what did make_ur5e_simple_gripper_usd.py actually WRITE to disk?

`simple_gripper_grasp_test.py` isolated the missing 0.045 m reach to the segment
between the gripper mount (base_link_0) and the pad midpoint — i.e. somewhere in the
two finger PrismaticJoints, not the FixedJoint mount (which measured correctly at
0.03 m). This script skips the simulator entirely and just opens the saved .usd file
to print the RAW authored attribute values on both finger joint prims — no physics,
no runtime interpretation, just "what's actually in the file". This rules in/out a
scripting bug (wrong value written) vs. a PhysX runtime-interpretation issue (right
value written, not applied the way expected).

Run on the lab PC (isaaclab env), headless — needs pxr, so still launched through
Isaac Sim's Python, but does no simulation:

    cd ~/Abdur_Rabbi_THESIS/"Comparison test"
    ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/check_simple_gripper_joint_attrs.py --headless
"""

import argparse
import os

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Raw USD attribute check for the simple gripper joints.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

from pxr import Usd  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
USD_PATH = os.path.normpath(os.path.join(HERE, "..", "assets", "ur5e_simple_gripper.usd"))

JOINT_PATHS = [
    "/Robot/SimpleGripper/mount_joint",
    "/Robot/SimpleGripper/left_finger_joint",
    "/Robot/SimpleGripper/right_finger_joint",
]
BODY_PATHS = [
    "/Robot/SimpleGripper/base_link",
    "/Robot/SimpleGripper/left_finger",
    "/Robot/SimpleGripper/right_finger",
]
ATTRS = [
    "physics:localPos0", "physics:localRot0",
    "physics:localPos1", "physics:localRot1",
    "physics:axis", "physics:lowerLimit", "physics:upperLimit",
    "physics:body0", "physics:body1",
]


def main() -> None:
    print("=" * 78)
    print(f"RAW USD CHECK: {USD_PATH}")
    print("=" * 78)
    stage = Usd.Stage.Open(USD_PATH)
    if stage is None:
        print("!! could not open stage")
        return

    for jp in JOINT_PATHS:
        prim = stage.GetPrimAtPath(jp)
        print(f"\n--- {jp} ---")
        if not prim or not prim.IsValid():
            print("    !! prim not found")
            continue
        print(f"    typeName = {prim.GetTypeName()}")
        for rel_name in ("physics:body0", "physics:body1"):
            rel = prim.GetRelationship(rel_name)
            targets = rel.GetTargets() if rel else []
            print(f"    {rel_name:20} = {[str(t) for t in targets]}")
        for attr_name in ATTRS:
            if attr_name in ("physics:body0", "physics:body1"):
                continue
            attr = prim.GetAttribute(attr_name)
            if not attr or not attr.HasAuthoredValue():
                print(f"    {attr_name:20} = (unauthored / schema default)")
                continue
            print(f"    {attr_name:20} = {attr.Get()}")

    print("\n" + "=" * 78)
    print("AUTHORED PRIM TRANSFORMS (translate/scale as written by add_box)")
    print("=" * 78)
    for bp in BODY_PATHS:
        prim = stage.GetPrimAtPath(bp)
        print(f"\n--- {bp} ---")
        if not prim or not prim.IsValid():
            print("    !! prim not found")
            continue
        for op_name in ("xformOp:translate", "xformOp:scale"):
            attr = prim.GetAttribute(op_name)
            if attr and attr.HasAuthoredValue():
                print(f"    {op_name:20} = {attr.Get()}")
            else:
                print(f"    {op_name:20} = (unauthored)")

    print(f"\n[done]")


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
