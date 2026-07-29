# HANDOFF — paste this into a new session

Updated 2026-07-30 (Day 22). Overwrite whenever the next action changes.

```
Read logbook/00_INDEX.md, then logbook/09_comparison_test.md, then the entries dated
"2026-07-30 (Day 22...)" in Comparison_test/run_log_new.md. Read them before touching code.

WORKING FOLDER: Comparison_test/  (RENAMED 2026-07-30 from "Comparison test" — the space is
gone, so quoting is no longer required. Older run_log entries still show the old name.)
    cd ~/Abdur_Rabbi_THESIS/Comparison_test
    ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/<script>.py
Log paths are CWD-relative, so always cd into Comparison_test/ first.

SANDBOX LIMIT: you cannot run Isaac Sim (no GPU). Touhid runs everything on his lab PC.
Write code, give exact commands, and READ THE REPORT FILES the scripts write — do not ask
him to paste output, and never claim you verified something you did not.

STANDING RULE, learned four times the hard way: a script here that does not write a FLUSHED
report file cannot be run for a result. `simulation_app.close()` discards block-buffered
stdout, and piping through `tee` is what CAUSES the buffering — both ways lose everything,
and the outcome is indistinguishable from a crash. Before telling Touhid to run anything,
grep it for `_FH` / `log()`. If it only print()s, add the report pattern FIRST.

STATE: Layer 1 is a cPPO-vs-PPO safe-RL grasping result on a UR5e in Isaac Lab. The gripper
work is DONE and the 15-run benchmark matrix (PPO/SAC/TD3/cPPO, 3 seeds) is UNBLOCKED but
still unlaunched.
- *** THE MATRIX RUNS ON Isaac-Lift-Cube-UR5e-v0, THE FROZEN WELD ENV. *** Decided Day 22,
  reversing the Day-20/21 repoint to -SimpleGripper-v0. -v0 is frozen, git-tagged, and already
  produced the Day-10 headline; the 2f-85 IS present and driven in it, with only the GRASP
  abstracted as a proximity weld (declared in Methods §2). Reason is schedule, not fidelity:
  03c had these six runs finishing Day 22 and the count is zero of fifteen.
- SimpleGripper (hand-built two-finger prismatic) PASSED its contact-grasp test on Day 22 —
  fingers stalled at a 62.8 mm pad gap against a 30 mm closed target, cube held after the pin
  released. It is now a ~50-iter smoke train only, and stands in the thesis as a separately
  demonstrated real-contact grasp. Mount + TCP confirmed by eye in the GUI (Day 21); builder
  geometry check reads "error 0.00 mm -> OK". ALL its geometry lives in ONE file,
  Comparison_test/ur5_grasp/robots/gripper_geometry.py — every consumer imports from it.
  DO NOT re-derive or hand-copy it.
- IMPORT TRAP: tasks/lift/__init__.py registers the SimpleGripper cfg alongside -v0, so
  gripper_geometry.py runs at package-import time and raises FileNotFoundError if
  assets/wrist_frame.json is missing — which would break -v0 too. Commit that JSON.
- The Robotiq 2f-85 is CLOSED PERMANENTLY (Day 22), on schedule grounds — NOT because it was
  broken. Its pads do have colliders and its linkage does work (84.9 mm gap vs 85 mm spec).
  Do not reopen it. If asked, read the warning block atop tools/check_robotiq_pads.py first:
  that script's verdict line is wrong.
- Env/cost frozen: MANIP_FLOOR=0.045, cost_limit=25, one binding constraint. Arm speed
  3.14 rad/s — *** DO NOT LOWER velocity_limit_sim ***, it zeroes the safety signal and
  collapses cPPO into PPO.

NEXT ACTION — nothing else is open. From inside "Comparison_test/":
  0. git add ur5_grasp/assets/wrist_frame.json + the Day-21/22 changes; commit; re-tag.
     The fairness protocol requires the env frozen and stamped BEFORE run 1.
  1. Smoke train, 50 iters, WELD env, PPO:
       ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train.py \
           --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096 \
           --max_iterations 50 --seed 1 --run_name smoke_ppo
     DO NOT SKIP: -v0 has never been trained inside this folder, and train.py plus
     tasks/lift/__init__.py have both changed since the freeze.
  2. Same, cPPO (proves LagrangianRunner + the extras["cost"] channel):
       ... --run_name smoke_cppo --agent rsl_rl_cppo_cfg_entry_point
  3. Same, SimpleGripper: --task Isaac-Lift-Cube-UR5e-SimpleGripper-v0 --run_name smoke_sg
  4. ./run_ppo_cppo_seeds.sh    (PPO x3 + cPPO x3 on -v0; writes logs/batch_report.txt;
     does NOT abort the batch if one run dies; exit code = number of failed runs)
  5. ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/summarize_runs.py
     Writes ur5_grasp/tools/summarize_runs_report.txt + results/tb_csv/*.csv — READ THOSE.

DEADLINES: TD3 hard cut 2026-08-06 EOD, writing due 2026-08-11, 15 runs unlaunched. Treat
anything not on the list above as out of scope unless Touhid says otherwise, and push back
if a request risks the deadline.

Update Comparison_test/run_log_new.md AND run_log.md with a dated entry for whatever happens,
and keep logbook/09_comparison_test.md pointed at the current state.
```
