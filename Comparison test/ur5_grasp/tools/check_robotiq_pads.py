# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""MEASURE where the Robotiq 2f-85's finger pads actually are, TWO independent ways.

######################################################################################
# STOP — DO NOT TRUST THIS SCRIPT'S VERDICT LINE.  (Day 22, after it ran once.)
#
# It printed "STOP. Method A itself returns an implausible pad midpoint, so the USD's
# own authored geometry is wrong." IT IS NOT ENTITLED TO THAT CONCLUSION. Three flaws,
# found by reading its own report:
#
#   1. Read 2 prints the pad GAP but not the pad POSITIONS. So it cannot distinguish
#      "pads correctly placed ~0.2 m out from the wrist" from "pads correctly separated
#      but the whole assembly collapsed onto the wrist origin" — the exact two cases it
#      exists to separate.
#   2. The read-1 table lists only the nine GRIPPER bodies. If the ARM bodies also read
#      [0,0,0] relative to wrist_3_link there, the articulation had simply not resolved
#      at that read and read 1 is a bad read, not a gripper defect. Never printed.
#   3. METHOD A READ THE WRONG PRIMS. This script's own collider audit shows the
#      geometry lives at .../left_inner_finger/visuals/Defeatured_..._finger4step_01/...
#      — the LINK prims are identity xforms, which is normal for a PhysX-authored robot
#      (kinematics in the joints' localPos0/localPos1, geometry in child mesh prims).
#      Method A computed the body prim's local-to-world, got identity, and called the
#      asset broken.
#
# WHAT THE RUN ACTUALLY ESTABLISHED, and it is worth keeping:
#   * The pads have 10 enabled convexHull colliders. Reason #2 for abandoning the 2f-85
#     is FALSE, confirming the Day-18 retraction. This is solid.
#   * At finger_joint = 0.8 the pads separated by 84.9 mm against an 85 mm spec stroke.
#     THE LINKAGE WORKS, and PhysX resolved distinct pad transforms 60 steps after the
#     read that called them degenerate.
#
# OPEN HYPOTHESIS, never tested: nothing is wrong with the 2f-85 at all, and both zeros
# are ordinary instrument bugs — the same class as the Day-18 traversal that started
# this whole thread. The 2f-85 was closed on SCHEDULE grounds (Day 22), not because the
# asset was shown to be broken. If it is ever reopened, fix all three flaws above BEFORE
# reading a single number out of this file.
#
# Kept rather than deleted: the collider audit is the evidence, and the bad verdict is
# material for the thesis' methods paragraph on diagnostic discipline.
######################################################################################

--------------------------------------------------------------------------------------
WHY THIS EXISTS
--------------------------------------------------------------------------------------
The 2f-85 was abandoned on Day 20 for two stated reasons. Re-reading the primary record
on Day 22, only one of them survives, and it is not clean either.

REASON 2 ("the pads have no collider") IS RETRACTED, and the retraction predates the
accusation. `run_log.md`, Day 18:

    CLEARED — fingers DO have enabled convexHull colliders (10, incl. both inner_finger
    pads); checked with tools/check_gripper_colliders.py (needs TraverseInstanceProxies
    — Isaac assets are instanceable). "No collider" was a false alarm from the first,
    buggy traversal.

The Day-20 abandonment entry reinstates the false alarm as settled fact, and Day 21 and
the 2f-85 handoff both inherit it from there. The script on disk is already the FIXED
version (it uses `Usd.TraverseInstanceProxies()`), so the retraction is what the current
code produces. This script re-runs that check into a FILE, so the claim is settled by
evidence rather than by which log entry you happen to read.

REASON 1 (degenerate gripper body positions) SURVIVES, but contains its own contradiction
and was never actually diagnosed. Day 18 found that all nine gripper bodies report
*exactly* [0, 0, 0] in `wrist_3_link`'s frame — while the SAME session measured an 84.4 mm
pad-to-pad gap between two of those same bodies. Both cannot be true of one array. Day 18
called them "unreliable, not statically collapsed" and moved on, which was correct at the
time: nothing in the frozen Layer-1 env reads bodies 7-15 (MONITORED_BODIES = 3/4/6,
EE_BODY = 6, Jacobian = arm joints, weld -> synthetic ee_frame).

But the Day-21 gripper method DOES read them. "Derive the TCP from the tip geometry"
(idea 3) and "make the builder measure itself after spawn" (idea 4) both need trustworthy
pad positions. So the single surviving objection to the 2f-85 sits exactly on the critical
path of the work being proposed, and it is unexplained rather than diagnosed.

That is what this script settles, before any geometry is written.

--------------------------------------------------------------------------------------
THE TWO METHODS
--------------------------------------------------------------------------------------
Same discipline as `tools/check_wrist_frame.py`: two independent measurements, cross-checked
against each other, and a REFUSAL to write a result if they disagree. Day 21 lost most of a
session to three diagnostics that were themselves wrong, so the instrument gets tested here
too — that is the entire reason there are two methods and not one.

  METHOD A — pure USD, no PhysX anywhere.
    Open the built USD, traverse WITH instance proxies, and compute each pad prim's
    local-to-world transform straight off the stage, then express it in `wrist_3_link`'s
    frame. This reads the asset's AUTHORED geometry. It cannot be affected by the
    articulation surgery in `make_ur5e_robotiq_usd.py`, because no articulation is ever
    created — nothing is simulated.
    Note the traversal: `stage.Traverse()` silently SKIPS instanced content, and Isaac's
    robot assets are instanceable. That exact omission is what produced the "no colliders"
    false alarm on Day 18. `Usd.TraverseInstanceProxies()` descends into it.

  METHOD B — PhysX, after spawn.
    Spawn the built USD as an `Articulation` (the same path the env takes) and read
    `body_pos_w`. This is the array Day 18 called degenerate. Gravity is off so the arm
    holds the written joint state exactly.

METHOD A IS THE GROUND TRUTH HERE, not the tie-breaker. If the two disagree, the authored
USD is what the asset actually says and `body_pos_w` is what PhysX reports about it — and
the whole Day-18 finding was that the latter is untrustworthy for this asset.

--------------------------------------------------------------------------------------
WHAT THE ANSWER DECIDES  (stop rule, fixed BEFORE the run)
--------------------------------------------------------------------------------------
  A and B AGREE, midpoint physically plausible (0.15-0.30 m from wrist_3):
      Day 18's [0,0,0] was itself an instrument artefact. The last objection to the 2f-85
      falls. Proceed to `robots/robotiq_geometry.py`. Small job.

  A SANE, B DEGENERATE:
      The asset is fine, PhysX's body reporting for it is not. Build the geometry from A,
      and make any post-spawn self-check USD-based instead of body_pos_w-based. Contained,
      roughly one extra day.

  A ALSO DEGENERATE:
      The USD assembly really is broken and there is nothing to measure. STOP. Drop the
      2f-85 permanently and write it up as the negative result. No third attempt.

--------------------------------------------------------------------------------------
RUN IT  (lab PC, isaaclab env; headless is fine — this prints numbers, not pictures)
--------------------------------------------------------------------------------------
    cd ~/Abdur_Rabbi_THESIS/"Comparison test"

    # 0. rebuild the 2f-85 USD inside THIS folder first, so provenance is local.
    #    (the make_usd_report.txt currently on disk is a Jul-13 copy showing main-folder
    #     paths, so the asset here has no local build record.)
    ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/make_ur5e_robotiq_usd.py --headless

    # 1. then this.
    ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/check_robotiq_pads.py --headless

Do NOT pipe either through `tee`. `simulation_app.close()` tears the process down without
flushing block-buffered stdout — that is how Day 21 produced a 162 KB log containing not
one line from the script. Both write flushed report files instead; read those.

Output: `tools/check_robotiq_pads_report.txt`   (always)
        `ur5_grasp/assets/robotiq_pads.json`    (only if the measurement is conclusive)
"""

from __future__ import annotations

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(
    description="Measure Robotiq 2f-85 pad geometry two independent ways (USD vs PhysX)."
)
parser.add_argument(
    "--open_angle", type=float, default=0.8,
    help="finger_joint value treated as OPEN for the pad-gap cross-check. Day 18 measured "
         "finger_joint=0.796 -> 84.4 mm gap against an 85 mm spec stroke, so 0.8 should "
         "reproduce ~84 mm if body_pos_w is trustworthy.",
)
parser.add_argument(
    "--settle", type=int, default=60,
    help="physics steps to settle after writing a joint state, before reading. 60, not 5: "
         "the simple gripper's first geometry check read the fingers MID-STROKE at 5 steps "
         "and reported a 26.43 mm 'PhysX mismatch' that was entirely drive travel.",
)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- after the app is up -------------------------------------------------------------
import datetime
import os

import torch

from pxr import Gf, Usd, UsdGeom, UsdPhysics

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import Articulation, ArticulationCfg
from isaaclab.utils.math import quat_apply_inverse

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.normpath(os.path.join(HERE, "..", "assets"))
USD_PATH = os.path.join(ASSETS_DIR, "ur5e_robotiq_2f85.usd")
OUT_JSON = os.path.join(ASSETS_DIR, "robotiq_pads.json")
REPORT_PATH = os.path.join(HERE, "check_robotiq_pads_report.txt")

MOUNT_BODY = "wrist_3_link"
PAD_BODIES = ("left_inner_finger", "right_inner_finger")

# Every body the 2f-85 variant contributes. Day 18's finding was that ALL of these report
# the same position; listing them explicitly lets the degeneracy test be exact rather than
# a tolerance judgement.
GRIPPER_BODIES = (
    "base_link_0",  # the gripper's own base_link, auto-renamed (the arm already has one)
    "left_outer_knuckle", "right_outer_knuckle",
    "left_outer_finger", "right_outer_finger",
    "left_inner_finger", "right_inner_finger",
    "left_inner_knuckle", "right_inner_knuckle",
)

# Physically plausible band for |pad midpoint| from wrist_3_link's origin, same window
# check_gripper_mount.py uses: flange d6 (0.0996) + 2f-85 body to pads (~0.13) ~= 0.23 m.
#
# Worth noting while reading the result: the frozen weld env uses OffsetCfg(pos=[0,0,0.16]),
# which Day 18 defended as "d6 (0.0996) + 2F-85 body (~0.13)". That arithmetic gives 0.23,
# not 0.16, and 0.16 only just enters this window. The number has never been measured. It
# is one of the two things this script is for.
EXPECTED_MIN = 0.15
EXPECTED_MAX = 0.30
FROZEN_ENV_OFFSET = 0.16

# Agreement tolerance between the two methods, on the pad midpoint.
#
# 5 mm is loose on purpose. Method A reads the stage's AUTHORED rest state and Method B
# reads a settled sim at joint_pos = 0, and those need not be bit-identical. The question
# this script asks is not "do these agree to a micron" — it is "is one of them degenerate",
# and the difference between a sane 0.2 m and a degenerate 0.0 m is not a tolerance call.
AGREE_TOL_M = 5e-3

# Two positions closer than this are treated as the SAME point — the Day-18 signature.
DEGENERATE_TOL_M = 1e-4

_FH = open(REPORT_PATH, "w")


def log(msg: str = "") -> None:
    print(msg, flush=True)
    _FH.write(msg + "\n")
    _FH.flush()


def fmt(vec, nd: int = 5) -> str:
    return "[" + ", ".join(f"{float(v):+.{nd}f}" for v in vec) + "]"


# ======================================================================================
# METHOD A — pure USD stage transforms. No physics, no articulation, no PhysX.
# ======================================================================================
def find_prims_by_name(stage: Usd.Stage, name: str) -> list:
    """All prims on the stage whose name matches exactly, INCLUDING inside instances.

    `stage.Traverse()` skips instanced content and Isaac's robot assets are instanceable —
    that omission is precisely what produced the Day-18 'no colliders' false alarm.
    """
    out = []
    for prim in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies()):
        if prim.GetName() == name:
            out.append(prim)
    return out


def local_to_world(xcache: UsdGeom.XformCache, prim: Usd.Prim) -> Gf.Matrix4d:
    """Local-to-world of a prim, tolerant of instance proxies."""
    try:
        return xcache.GetLocalToWorldTransform(prim)
    except Exception:  # noqa: BLE001  — older USD builds are fussier about proxies
        return UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())


def method_a(stage: Usd.Stage) -> dict | None:
    """Pad positions in wrist_3_link's frame, read straight off the authored USD."""
    log("--- METHOD A: pure USD stage transforms (no PhysX) ---")
    log("    Reads the asset's AUTHORED geometry at its default state. Cannot be affected by")
    log("    the articulation surgery, because no articulation is ever created here.")
    log("")

    wanted = (MOUNT_BODY,) + PAD_BODIES
    prims = {}
    for name in wanted:
        hits = find_prims_by_name(stage, name)
        if not hits:
            log(f"    !! no prim named '{name}' found anywhere on the stage (incl. instances).")
            return None
        if len(hits) > 1:
            log(f"    note: {len(hits)} prims named '{name}': {[str(p.GetPath()) for p in hits]}")
            log("          using the first. If these are genuinely different bodies, say so —")
            log("          it would mean the name-based lookups everywhere else are ambiguous.")
        prims[name] = hits[0]
        log(f"    found {name:<20} at {hits[0].GetPath()}")
    log("")

    xcache = UsdGeom.XformCache(Usd.TimeCode.Default())
    m_w3 = local_to_world(xcache, prims[MOUNT_BODY])
    m_w3_inv = m_w3.GetInverse()

    # USD uses the row-vector convention (p_world = p_local * M), so composing a transform
    # INTO wrist_3's frame is M_pad * inverse(M_w3), in that order.
    #
    # Order verified against Isaac Lab's own code rather than derived and hoped for:
    # `isaaclab_tasks/manager_based/manipulation/dexsuite/mdp/utils.py:137` does exactly
    # `xform_cache.GetLocalToWorldTransform(prim) * world_root.GetInverse()` and then
    # applies it as `pts_h @ mat_t` — row-vector, same order as here.
    # (Line 64 of that same file uses the OPPOSITE order under an identical "prim -> root"
    # comment, but it only feeds a hash, so the order is never exercised there. Do not read
    # that line as a counter-example.)
    out = {}
    for name in PAD_BODIES:
        m_rel = local_to_world(xcache, prims[name]) * m_w3_inv
        t = m_rel.ExtractTranslation()
        out[name] = torch.tensor([t[0], t[1], t[2]], dtype=torch.float64)
        log(f"    {name:<20} in {MOUNT_BODY}'s frame : {fmt(out[name])}")

    mid = (out[PAD_BODIES[0]] + out[PAD_BODIES[1]]) / 2.0
    gap = float(torch.linalg.norm(out[PAD_BODIES[0]] - out[PAD_BODIES[1]]))
    dist = float(torch.linalg.norm(mid))
    log("")
    log(f"    pad midpoint          : {fmt(mid)}")
    log(f"    |pad midpoint|        : {dist:.5f} m")
    log(f"    pad-to-pad gap        : {gap * 1000:.1f} mm")
    log("")

    return {"pads": out, "mid": mid, "gap": gap, "dist": dist}


# ======================================================================================
# METHOD B — PhysX body_pos_w after spawn. The array Day 18 called degenerate.
# ======================================================================================
def read_bodies(robot: Articulation, names: list) -> dict:
    """Every gripper body's origin, expressed in wrist_3_link's own frame."""
    i_w3 = names.index(MOUNT_BODY)
    w3_pos = robot.data.body_pos_w[0, i_w3]
    w3_quat = robot.data.body_quat_w[0, i_w3]
    out = {}
    for name in names:
        p = robot.data.body_pos_w[0, names.index(name)]
        out[name] = quat_apply_inverse(w3_quat, p - w3_pos).double().cpu()
    return out


def method_b(sim, robot: Articulation) -> dict | None:
    log("--- METHOD B: PhysX body_pos_w after spawn ---")
    log("    This is the array Day 18 reported as exactly [0,0,0] for all nine gripper bodies")
    log("    — while the same session measured an 84.4 mm pad gap between two of them. Both")
    log("    cannot be true. This settles which.")
    log("")

    names = list(robot.body_names)
    joint_names = list(robot.joint_names)
    log(f"    body names : {names}")
    log(f"    joint names: {joint_names}")
    log("")

    missing = [n for n in (MOUNT_BODY,) + PAD_BODIES if n not in names]
    if missing:
        log(f"    !! bodies missing from body_names: {missing}. Cannot measure. Aborting method B.")
        return None

    def settle_at(finger_angle: float) -> dict:
        q = torch.zeros_like(robot.data.joint_pos)
        if "finger_joint" in joint_names:
            q[:, joint_names.index("finger_joint")] = finger_angle
        robot.write_joint_state_to_sim(q, torch.zeros_like(q))
        robot.set_joint_position_target(q)
        robot.write_data_to_sim()
        for _ in range(args_cli.settle):
            sim.step(render=False)
            robot.update(sim.get_physics_dt())
        return read_bodies(robot, names)

    # ---- read 1: everything parked at zero (comparable with method A's rest state) ----
    at_zero = settle_at(0.0)
    log(f"    [read 1] all joints parked at 0, settled {args_cli.settle} steps")
    log(f"    {'body':<22} {'x':>10} {'y':>10} {'z':>10} {'dist':>10}")
    for name in GRIPPER_BODIES:
        if name not in at_zero:
            continue
        v = at_zero[name]
        log(f"    {name:<22} {v[0]:+10.5f} {v[1]:+10.5f} {v[2]:+10.5f} "
            f"{float(torch.linalg.norm(v)):10.5f}")
    log("")

    # ---- the degeneracy test, stated exactly ----------------------------------------
    present = [n for n in GRIPPER_BODIES if n in at_zero]
    ref = at_zero[present[0]]
    spreads = [float(torch.linalg.norm(at_zero[n] - ref)) for n in present]
    max_spread = max(spreads) if spreads else 0.0
    degenerate = max_spread < DEGENERATE_TOL_M
    log(f"    degeneracy test: max separation between any two of the {len(present)} gripper")
    log(f"    bodies = {max_spread * 1000:.4f} mm")
    if degenerate:
        log("    -> DEGENERATE. Every gripper body reports the SAME point. PhysX is not")
        log("       resolving distinct transforms for them. This reproduces Day 18 exactly.")
    else:
        log("    -> NOT degenerate. The bodies occupy distinct positions, so the Day-18")
        log("       finding does NOT reproduce. Read the per-body table above before")
        log("       concluding anything — 'not identical' is not the same as 'correct'.")
    log("")

    # ---- read 2: gripper open — cross-checks Day 18's own 84.4 mm figure -------------
    at_open = settle_at(args_cli.open_angle)
    p0, p1 = (at_open[n] for n in PAD_BODIES)
    open_gap = float(torch.linalg.norm(p0 - p1))
    fj = (float(robot.data.joint_pos[0, joint_names.index("finger_joint")])
          if "finger_joint" in joint_names else float("nan"))
    log(f"    [read 2] finger_joint commanded {args_cli.open_angle}, actual {fj:+.4f}")
    log(f"    pad-to-pad gap at open : {open_gap * 1000:.1f} mm   "
        f"(Day 18 measured 84.4 mm; 2f-85 spec stroke is 85 mm)")
    if degenerate and open_gap < DEGENERATE_TOL_M:
        log("    -> gap is ZERO here. So Day 18's 84.4 mm cannot have come from this array,")
        log("       and that contradiction in the record is now explained: two different")
        log("       measurements were being attributed to one source.")
    log("")

    mid = (at_zero[PAD_BODIES[0]] + at_zero[PAD_BODIES[1]]) / 2.0
    return {
        "pads": {n: at_zero[n] for n in PAD_BODIES},
        "mid": mid,
        "gap": float(torch.linalg.norm(at_zero[PAD_BODIES[0]] - at_zero[PAD_BODIES[1]])),
        "dist": float(torch.linalg.norm(mid)),
        "open_gap": open_gap,
        "degenerate": degenerate,
        "max_spread": max_spread,
        "all_bodies": at_zero,
    }


# ======================================================================================
# The retracted collider claim — settled into a FILE this time.
# ======================================================================================
def collider_audit(stage: Usd.Stage) -> dict:
    log("--- COLLIDER AUDIT (the claim the handoff repeats and Day 18 already retracted) ---")
    n_collider = 0
    n_mesh = 0
    rows = []
    for prim in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies()):
        path = str(prim.GetPath())
        low = path.lower()
        if not any(k in low for k in ("finger", "knuckle")):
            continue
        has_col = prim.HasAPI(UsdPhysics.CollisionAPI)
        is_mesh = prim.GetTypeName() == "Mesh"
        if not (has_col or is_mesh):
            continue
        n_collider += int(has_col)
        n_mesh += int(is_mesh)
        en = prim.GetAttribute("physics:collisionEnabled")
        ap = prim.GetAttribute("physics:approximation")
        rows.append((
            "COLLIDER" if has_col else "mesh-only",
            str(prim.GetTypeName()),
            str(en.Get()) if (en and en.HasAuthoredValue()) else "(unset)",
            str(ap.Get()) if (ap and ap.HasAuthoredValue()) else "(unset)",
            path,
        ))
    for tag, typ, en, ap, path in rows:
        log(f"    [{tag:9}] {typ:6} enabled={en:<12} approx={ap:<14} {path}")
    log(f"    finger/knuckle prims with CollisionAPI : {n_collider}")
    log(f"    finger/knuckle Mesh prims total        : {n_mesh}")
    if n_collider > 0:
        log("    -> COLLIDERS EXIST. The handoff's reason #2 for abandoning the 2f-85 is")
        log("       FALSE, and Day 18 already said so. Correct the record.")
    elif n_mesh > 0:
        log("    -> Pads have visual meshes but NO collider. Reason #2 stands after all;")
        log("       the Day-18 retraction was itself wrong. Say so loudly.")
    else:
        log("    -> Nothing matched. INCONCLUSIVE — not a verdict either way. The traversal")
        log("       found no finger/knuckle prims at all, which means the gripper subtree did")
        log("       not compose. Fix that before reading anything else in this report.")
    log("")
    return {"n_collider": n_collider, "n_mesh": n_mesh}


# ======================================================================================
def main() -> None:
    log("=" * 86)
    log("MEASURE  Robotiq 2f-85 pad geometry   (USD vs PhysX, two independent methods)")
    log("=" * 86)
    log(f"USD    : {USD_PATH}")
    log(f"report : {REPORT_PATH}")
    log("")

    if not os.path.exists(USD_PATH):
        log("!! the built USD does not exist. Build it first, from inside \"Comparison test/\":")
        log("     ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/make_ur5e_robotiq_usd.py --headless")
        return

    stage = Usd.Stage.Open(USD_PATH)
    if stage is None:
        log("!! could not open the stage. Aborting.")
        return

    collider_audit(stage)
    a = method_a(stage)

    # --- method B needs a live sim ----------------------------------------------------
    # Gravity off so the arm holds exactly the joint state written to it. This is a
    # geometry read, not a physics test.
    sim = sim_utils.SimulationContext(
        sim_utils.SimulationCfg(dt=0.01, device=args_cli.device, gravity=(0.0, 0.0, 0.0))
    )
    robot = Articulation(
        ArticulationCfg(
            prim_path="/World/Robot",
            spawn=sim_utils.UsdFileCfg(usd_path=USD_PATH),
            actuators={"all": ImplicitActuatorCfg(joint_names_expr=[".*"], stiffness=None, damping=None)},
        )
    )
    sim.reset()
    b = method_b(sim, robot)

    # --- verdict ----------------------------------------------------------------------
    log("=" * 86)
    log("VERDICT")
    log("=" * 86)

    if a is None:
        log("METHOD A could not read the pads off the USD at all.")
        log("-> The asset does not contain what its own body_names claim. STOP: there is")
        log("   nothing to measure and nothing to build geometry from. Recommend dropping")
        log("   the 2f-85 permanently and writing the negative result.")
        return
    if b is None:
        log("METHOD B could not run. A is below; treat it as unconfirmed until B runs.")
        log(f"    A: |pad midpoint| = {a['dist']:.5f} m, gap = {a['gap'] * 1000:.1f} mm")
        return

    delta = float(torch.linalg.norm(a["mid"] - b["mid"]))
    plausible = EXPECTED_MIN <= a["dist"] <= EXPECTED_MAX

    log(f"    A (USD)   : |pad midpoint| = {a['dist']:.5f} m   mid = {fmt(a['mid'])}   "
        f"gap = {a['gap'] * 1000:.1f} mm")
    log(f"    B (PhysX) : |pad midpoint| = {b['dist']:.5f} m   mid = {fmt(b['mid'])}   "
        f"gap = {b['gap'] * 1000:.1f} mm")
    log(f"    A vs B difference on the midpoint : {delta * 1000:.2f} mm "
        f"(agreement tolerance {AGREE_TOL_M * 1000:.0f} mm)")
    log(f"    A midpoint physically plausible   : {'YES' if plausible else 'NO'} "
        f"(expected {EXPECTED_MIN:.2f}-{EXPECTED_MAX:.2f} m from wrist_3)")
    log(f"    frozen weld env currently uses    : {FROZEN_ENV_OFFSET:.3f} m along +Z "
        f"(error vs measured A: {(a['dist'] - FROZEN_ENV_OFFSET) * 1000:+.1f} mm)")
    log("")

    if not plausible:
        log(">>> STOP. Method A itself returns an implausible pad midpoint, so the USD's own")
        log("    authored geometry is wrong — not just PhysX's reading of it. There is no")
        log("    trustworthy source to derive a TCP from.")
        log("    RECOMMENDATION: drop the 2f-85 permanently. This is the third failure and")
        log("    the SimpleGripper is already the shipping deliverable. Write the negative")
        log("    result and launch the 15-run matrix.")
    elif b["degenerate"]:
        log(">>> A IS SANE, B IS DEGENERATE. The asset's authored geometry is correct and")
        log("    usable; PhysX's body_pos_w for the gripper is not. Day 18's finding")
        log("    reproduces, and is now localised: it is a REPORTING defect, not a geometry")
        log("    defect.")
        log("    CONSEQUENCE for the build: derive robotiq_geometry.py from method A's")
        log("    numbers, and make the post-spawn self-check (Day-21 idea 4) USD-based")
        log("    rather than body_pos_w-based — body_pos_w cannot be the instrument when it")
        log("    is the thing that is broken.")
        log("    Roughly one extra day over the clean case. Still contained. Still optional.")
    elif delta <= AGREE_TOL_M:
        log(">>> A AND B AGREE. Day 18's [0,0,0] does NOT reproduce — it was itself an")
        log("    instrument artefact, the fourth of that shape in this project. Both of the")
        log("    stated reasons for abandoning the 2f-85 are now retracted on evidence.")
        log("    Proceed to robots/robotiq_geometry.py with the numbers above.")
    else:
        log(">>> A AND B DISAGREE, and B is not degenerate either. This is a THIRD state,")
        log("    not covered by the stop rule written before the run. Do not pick a winner")
        log("    from this report alone — that is exactly the move that cost Day 21 three")
        log("    sessions. Bring the numbers back and decide with a human look in the GUI.")
    log("")

    payload = {
        "method_a_usd": {
            "pads": {k: [round(float(x), 6) for x in v.tolist()] for k, v in a["pads"].items()},
            "midpoint": [round(float(x), 6) for x in a["mid"].tolist()],
            "midpoint_distance_m": round(a["dist"], 6),
            "pad_gap_m": round(a["gap"], 6),
        },
        "method_b_physx": {
            "pads": {k: [round(float(x), 6) for x in v.tolist()] for k, v in b["pads"].items()},
            "midpoint": [round(float(x), 6) for x in b["mid"].tolist()],
            "midpoint_distance_m": round(b["dist"], 6),
            "pad_gap_m": round(b["gap"], 6),
            "pad_gap_at_open_m": round(b["open_gap"], 6),
            "all_bodies_degenerate": bool(b["degenerate"]),
            "max_body_separation_m": round(b["max_spread"], 8),
        },
        "agreement_delta_m": round(delta, 6),
        "plausible": bool(plausible),
        "frozen_env_offset_m": FROZEN_ENV_OFFSET,
        "trusted_source": "method_a_usd" if b["degenerate"] else "both",
        "source_usd": USD_PATH,
        "measured_utc": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    if plausible:
        import json

        with open(OUT_JSON, "w") as fh:
            json.dump(payload, fh, indent=2)
        log(f"wrote {OUT_JSON}")
        log("")
        log("NEXT: bring this report back. Nothing gets built against these numbers until")
        log("      they have been read — the geometry module is deliberately NOT written yet.")
    else:
        log("REFUSING to write robotiq_pads.json — the measurement is not conclusive, and a")
        log("confident wrong number on disk is worse than no number. (Same rule as")
        log("check_wrist_frame.py.)")


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
