# HANDOFF — Robotiq 2f-85: same mount + TCP treatment as the simple gripper

> ## ⛔ SUPERSEDED — DO NOT PASTE THIS INTO A NEW CHAT
> **This workstream was opened and CLOSED on 2026-07-30 (Day 22).** Kept for the record only.
>
> Two corrections to the prompt below, both established by a run on the lab PC:
> 1. **"its finger pads have no working collider at all" is FALSE.** They have 10 enabled
>    `convexHull` colliders including both `inner_finger` pads. This was a false alarm from a
>    traversal that omitted `TraverseInstanceProxies`, **retracted on Day 18** (`run_log.md`
>    lines 186–188) and wrongly reinstated as fact by the Day-20 entry, from which this handoff
>    inherited it.
> 2. **The linkage works.** At `finger_joint = 0.8` the pads separate by 84.9 mm against an
>    85 mm spec stroke, with PhysX resolving distinct pad transforms. The "degenerate body
>    positions" finding was never diagnosed and may itself be an instrument artefact.
>
> The 2f-85 was closed on **schedule** grounds — three sessions consumed, two more rounds needed
> for a validated TCP, the SimpleGripper deliverable already passing at 0.00 mm, TD3 hard cut
> Aug 6, writing due Aug 11, and Layer-3 hardware being an RH-P12-RN — **not** because the asset
> was shown to be broken.
>
> Current record: `Comparison_test/run_log_new.md` (2026-07-30, Day 22) and
> `logbook/09_comparison_test.md`. Current next action: `logbook/HANDOFF.md`.
> If this is ever reopened, read the warning block at the top of
> `Comparison_test/ur5_grasp/tools/check_robotiq_pads.py` first.

Paste the block below into a new chat (connect the `Abdur_Rabbi_THESIS` folder first).
Written 2026-07-30, end of Day 21.

---

```
Read logbook/00_INDEX.md, then logbook/09_comparison_test.md, then the four entries dated
"2026-07-30 (Day 21...)" in Comparison_test/run_log_new.md. Everything below summarises
those so you have the shape of it, but read the actual logs before touching code.

WORKING FOLDER: "Comparison_test/" — the name has a space, quote it in every shell command.
Commands run as:
    cd ~/Abdur_Rabbi_THESIS/Comparison_test
    ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/<script>.py --headless

SANDBOX LIMIT: you cannot run Isaac Sim (no GPU). Touhid runs everything on his lab PC
(i9 / 64 GB / RTX 5090). Write code and give exact commands; do not claim anything is
verified that you have not verified. You CAN read the report files the scripts write, in
the working folder — do that instead of asking him to paste output.

=== THE TASK ===
Give the Robotiq 2f-85 the same mount orientation and TCP treatment that the simple
two-finger gripper got on Day 21, and which is now confirmed correct by eye in the GUI:
the gripper aligned with the wrist, and the TCP sitting between the finger pads rather
than at some inherited offset.

=== SCOPE — READ THIS BEFORE PLANNING ANYTHING ===
This is a PARALLEL, OPTIONAL workstream. Touhid's explicit call, Day 21 close.

The simple two-finger gripper REMAINS the Layer-1 deliverable. The 15-run benchmark
matrix launches on Isaac-Lift-Cube-UR5e-SimpleGripper-v0 and does NOT wait for the
2f-85. If the 2f-85 stalls, it gets dropped again and nothing is lost.

Why the guardrail exists: the 2f-85 was abandoned on Day 20 after failing twice, for two
independent and separately confirmed reasons —
  1. it is a closed 4-bar linkage authored as its OWN articulation, and
     make_ur5e_robotiq_usd.py's surgery folding it into the arm's articulation produced
     degenerate [0,0,0] gripper body positions (Day 18, tools/check_gripper_mount.py);
  2. its finger pads have no working collider at all — mesh geometry with no
     UsdPhysics.CollisionAPI (tools/check_gripper_colliders.py), so pads closed straight
     through the cube.
Also: the real Layer-3 hardware gripper is a ROBOTIS RH-P12-RN, not a 2f-85, so 2f-85
fidelity was never buying sim-to-real value (ur5_grasp/CONTEXT.md).

Deadlines this is measured against: writing due 2026-08-11, TD3 hard cut 2026-08-06 EOD,
and the 15-run matrix is STILL UNLAUNCHED. So: if the collider or articulation problems
resist, say so early and recommend stopping rather than grinding. Do not let this become
the critical path. Ask before expanding scope.

=== THE METHOD THAT WORKED — COPY IT, DON'T REINVENT IT ===
Day 21 fixed the simple gripper with four ideas. Reuse all four.

1. MEASURE THE MOUNT AXIS, DO NOT INHERIT IT.
   The simple gripper was mounted along wrist_3_link's local +Z, a number inherited from
   the frozen weld env's OffsetCfg(pos=[0,0,0.16]) — commented "approx, tune" and never
   validated. It could not have been validated there: a weld env TELEPORTS the cube to
   whatever point the TCP names, so a TCP pointing out of the side of the wrist trains to
   100% success exactly like a correct one.
   ur5_grasp/tools/check_wrist_frame.py already exists and already did this measurement.
   It identifies the tool axis two independent ways (the axis invariant under
   wrist_3_joint rotation; the sign from the wrist_2 -> wrist_3 origin offset) and refuses
   to write a result if they disagree. It writes assets/wrist_frame.json.
   RESULT ALREADY ON DISK: tool axis is +Z of wrist_3_link, dot 1.000000 vs 0.764842 for
   X and Y, offset [0, 0, +0.0996] = a UR5e's d6. You do NOT need to re-run it. Reuse the
   JSON. (Note the outcome: the standard UR URDF convention makes -Y look likely and it is
   wrong. That is the whole argument for measuring.)

2. ONE GEOMETRY MODULE, NOT NUMBERS COPIED ACROSS FILES.
   ur5_grasp/robots/gripper_geometry.py is the single source of truth for the simple
   gripper: it reads wrist_frame.json and derives MOUNT_QUAT, MOUNT_POS, TCP_OFFSET_POS,
   TCP_OFFSET_ROT and the open/close targets. The USD builder, the training env cfg, the
   grasp test and the live demo all import from it. Before it existed, "0.075" was
   hand-copied into three files each carrying a comment begging whoever changed one to
   remember the other two — and the Day-21 geometry change is exactly what broke that.
   Do the same for the 2f-85: a sibling module (e.g. robots/robotiq_geometry.py), NOT new
   constants scattered around. Do not modify gripper_geometry.py — the simple gripper is
   the shipping deliverable and must not move.

3. DERIVE THE TCP FROM THE TIP GEOMETRY.
   Simple gripper: TCP_Z = TIP_Z - GRASP_INSET (0.025 m back from the finger tips), so the
   cube's centre sits between the pads and the tips reach past it onto flat faces. Change
   a finger length and the TCP follows. Do the same for the 2f-85 rather than picking a
   number: measure where its pads actually are, then inset from there.
   Give the ee_frame offset a ROTATION as well as a translation (OffsetCfg(pos=..., rot=...))
   so the TCP frame's own +Z is the approach direction. Anything that reasons about approach
   direction — IK, and IBVS in Layer 2 later — reads that orientation, not just the position.

4. MAKE THE BUILDER MEASURE ITSELF AFTER SPAWN.
   make_ur5e_simple_gripper_usd.py's report ends with a post-spawn check: where did the
   finger body ACTUALLY end up relative to wrist_3_link, versus where the geometry says,
   in mm, per axis. Both of the simple gripper's hard bugs were "the USD says X, PhysX
   resolved Y" and neither showed up in a joint/body name dump. For the 2f-85 the
   equivalent check is more important, not less, because its articulation is the thing
   that was broken.

=== HARD-WON WARNINGS (all cost real time on Day 21) ===
- The instrument is as likely to be wrong as the thing it measures. Day 21 lost most of a
  session to three self-inflicted diagnostic failures: a geometry check that reported a
  26.43 mm "PhysX mismatch" that was entirely finger travel (the drive target was OPEN and
  the read caught the fingers mid-stroke; the error was all in X, the fingers' free axis,
  while Z — the thing under test — was exact); a `| tee` capture that block-buffered
  Python's stdout so a 162 KB log contained not one line from the script; and a "visual
  gate" script that had been the pending next action for three sessions and had never once
  executed. TEST THE INSTRUMENT.
- Never capture an Isaac script's output through a pipe. `simulation_app.close()` tears the
  process down without flushing block-buffered stdout. Every script here writes a FLUSHED
  report file (log() = print + write + flush) — follow that pattern and read the file.
  Useful corollary: stderr stays line-buffered even when redirected, so absence of a
  traceback in a merged 2>&1 capture IS evidence the script did not raise.
- Do NOT declare a marker/config field inside an InteractiveSceneCfg configclass BODY.
  InteractiveScene._add_entities_from_cfg() walks every field and skips only names in
  InteractiveSceneCfg.__dataclass_fields__ — a leading underscore means nothing. A stray
  `_marker_cfg = FRAME_MARKER_CFG.copy()` in the class body IS a scene entity and raises
  "Unknown asset config type" before a single frame renders. Build markers at module level
  or inside __post_init__.
- FRAME_MARKER_CFG's default frame scale is (0.5, 0.5, 0.5) — half-metre axes. On a ~0.1 m
  gripper that fills the viewport. Use ~0.05. Also, FrameTransformer's debug_vis draws a
  marker at the SOURCE frame as well as every target, plus a 1 m yellow connecting_line
  cylinder; turn debug_vis off if you are drawing your own marker.
- PhysX resolves an off-axis (Y/Z) anchor offset on a PrismaticJoint differently from the
  identical offset on a FixedJoint (measured: 0.031 m where 0.075 m was authored). The
  simple gripper routes around this by keeping each finger's body ORIGIN exactly on its
  joint anchor and offsetting the collision box as a CHILD prim inside the body. If you
  author any joint for the 2f-85, keep off-axis components out of the joint anchors.
- The arm already has a body called `base_link`, so a gripper prim of the same name is
  auto-renamed to `base_link_0` in Articulation.body_names. Do not look up the gripper by
  `base_link`.
- Path depth gotcha: scripts under "Comparison_test/" are one directory deeper than the
  main folder, which broke a hardcoded "two levels up" IsaacLab lookup (Day 20). The four
  scripts in Comparison_test/ur5_grasp/scripts/ use _find_isaaclab_root() instead. Reuse it.
- rsl_rl log paths are CWD-relative, not script-relative — cd into "Comparison_test/" first.

=== TWO COPIES OF ur5_grasp/ — KEEP THEM STRAIGHT ===
- Abdur_Rabbi_THESIS/ur5_grasp/ — main folder, tagged layer1-env-freeze. Source of truth for
  the env/cost definition. Do NOT do 2f-85 work here.
- Abdur_Rabbi_THESIS/Comparison_test/ur5_grasp/ — the working copy. All of this happens here.
  New files specific to the 2f-85 live only in this copy.

=== SUGGESTED FIRST MOVES (not a plan — propose one and confirm before building) ===
1. Read tools/make_ur5e_simple_gripper_usd.py, robots/gripper_geometry.py and
   tools/check_wrist_frame.py end to end. They are heavily commented with the WHY of every
   decision, including the two failed rounds. That is the pattern to mirror.
2. Read tools/check_gripper_colliders.py and tools/check_gripper_mount.py — the two Day-18/19
   diagnostics that condemned the 2f-85. Re-run them first on the current asset. If the pads
   still have no CollisionAPI, decide EARLY whether authoring colliders onto them is a
   contained fix or the start of another rebuild. That decision is the whole risk of this
   workstream, so surface it in the first session, not the third.
3. Only then propose the mount/TCP work.

=== SUCCESS CRITERION ===
In the GUI: the 2f-85 mounted aligned with the wrist, and a single ~0.05 m RGB axis marker
sitting between the finger pads with its blue +Z arrow along the approach direction —
matching what the simple gripper now shows. Grasping with it is a SEPARATE, later question
and needs the collider problem solved first; do not conflate the two.

Update Comparison_test/run_log_new.md AND run_log.md with a dated entry for whatever happens,
and keep logbook/09_comparison_test.md pointed at the current state. Same convention as every
other session in this project.
```
