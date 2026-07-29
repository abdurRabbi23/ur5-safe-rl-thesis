# HANDOFF — paste this into a new session

Written 2026-07-29 (Day 19, evening). Overwrite this file whenever the next action changes.

```
Read logbook/00_INDEX.md, logbook/09_comparison_test.md, and logbook/03c_multialgo_benchmark.md
(decisions/hypothesis/protocol, still binding), then work inside the "Comparison test/" folder.

CONTEXT: the 4-algorithm benchmark (PPO/SAC/TD3/cPPO) is being redone from scratch, start to
finish, inside Abdur_Rabbi_THESIS/Comparison test/ — NOT continued in the main ur5_grasp/ /
IsaacLab/logs/ folders. That's a deliberate Day-19 decision for a clean, self-contained record.
Nothing from the main folder's earlier PPO x3 seeds is reused.

SETUP ALREADY DONE (Day 19 evening):
- "Comparison test/" created with ur5_grasp/ (working copy of the frozen env, copied from the
  main folder's tagged layer1-env-freeze / b8f0727 state), configs/, results/ (with
  make_layer1_figs.py copied in as a starting point), docs/.
- Confirmed by reading the code: rsl_rl log paths are CWD-relative, not script-location-relative.
  To get logs inside Comparison test/, you MUST cd there first and call IsaacLab by relative path
  the other way. Exact commands are in logbook/09_comparison_test.md - use them as written.
- The folder name has a space in it ("Comparison test") - always quote the path in shell
  commands.

STATE OF THE ENV (unchanged, frozen): EE offset [0,0,0.16] verified correct - don't touch it.
Gripper OPEN/CLOSE convention corrected (0.8=OPEN/0.0=CLOSE). Arm speed 3.14 rad/s, 5.0 s
episodes - *** DO NOT LOWER velocity_limit_sim ***, a 1.0 rad/s probe zeroed the safety signal
(kept as a Discussion sensitivity-analysis run in the main folder's logs, not reproduced here).
cost_limit=25 / MANIP_FLOOR=0.045 are the Day-9 calibrations, still valid.

NEXT ACTION: cd into "Comparison test/", launch PPO x3 seeds (seed 1/2/3, run_name ppo_s1/s2/s3
to match the main folder's naming convention), then cPPO x3 seeds. Commands in
logbook/09_comparison_test.md.

AFTER PPO+cPPO (pass bar restored, everything past this is upside, per 03c's cut order):
author skrl configs for SAC/TD3/bridge inside Comparison test/configs/, smoke-test each at
50 iters, then run the full matrix. TD3 is first cut, HARD CUT Aug 6 EOD. Writing due Aug 11.

OPEN, non-blocking (unrelated to this move, still true):
1. Git divergence on the main repo: local main has 2 commits origin doesn't; origin has 6
   Layer-2 commits local doesn't. Needs a pull/merge before either side pushes further.
   "Comparison test/" is a plain filesystem copy, not yet git-tracked - decide before the first
   commit whether it goes into the same repo or its own.
2. Admin gaps from the supervisor: defense date, submission deadline, page limit, font size
   (12pt vs 14pt conflict). See logbook/08_project_context.md.
3. Reference PDFs (Fawad Khan cPPO paper, Shahid, Shi, Zhang, thesis proposal, Md Masrul Khan's
   thesis book) exist only in the old Claude Project's uploads, not in this folder.
```

## Settled — do not re-litigate

| Question | Answer |
|---|---|
| EE offset `[0,0,0.16]` | correct axis (+Z is forward tool axis) and magnitude — keep |
| "~1.3 cm" pad midpoint | artefact of collapsed gripper bodies — dead |
| `_TCP_OFFSET = (-0.013,0,0)` | invalid, stays in the shelved contact branch |
| `base_link` name collision | does not exist — Isaac auto-renames to `base_link_0` |
| Gripper open/close inversion | real, measured (0.796 → 84.4 mm gap vs 85 mm spec) — apply |
| Gripper USD rebuild | NO — visual only, days of shelved-branch work, no deliverable affected |
| Cost function | frozen: 3 terms, `MANIP_FLOOR=0.045`, `cost_limit=25`, no FOV term |
| Arm speed | **3.14 rad/s — do NOT lower.** 1.0 rad/s zeroes the violations and kills the result (Day 19, full 1500-iter evidence) |
| Episode length | **5.0 s.** Coupled to `cost_limit`; move both or neither |
| Random cube + random target | already in the base env, nothing to build |
| Slow-motion for viewing | use `play.py --slow 5` — playback only, does not touch the env |
| Where the comparison-test work happens | `Comparison test/`, NOT the main `ur5_grasp/`/`IsaacLab/logs/` — decided Day 19 |
| Main folder's PPO ×3 seeds | NOT reused — the new folder retrains everything, including PPO |
| rsl_rl log path | CWD-relative — cd into `Comparison test/` before invoking `isaaclab.sh` |
| Scope pivot (PPO/SAC/TD3/cPPO) | resolved Day 18, don't reopen — see `08_project_context.md` |

## Useful commands

```bash
# main-folder playback / diagnostics (unchanged)
cd ~/Abdur_Rabbi_THESIS/IsaacLab

./isaaclab.sh -p ../ur5_grasp/tools/check_gripper_mount.py --headless
./isaaclab.sh -p ../ur5_grasp/tools/check_gripper_mount.py --hold

./isaaclab.sh -p ../ur5_grasp/scripts/play.py \
    --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 1 --seed 42

./isaaclab.sh -p ../ur5_grasp/scripts/play.py \
    --task Isaac-Lift-Cube-UR5e-Play-v0 \
    --agent rsl_rl_cppo_cfg_entry_point --num_envs 1 --seed 42
```

```bash
# comparison-test training (NEW — run from inside "Comparison test/", note the quoting)
cd "$HOME/Abdur_Rabbi_THESIS/Comparison test"

../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096 --seed 1 --run_name ppo_s1

../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096 --seed 1 --run_name cppo_s1 \
    --agent rsl_rl_cppo_cfg_entry_point
```

Pre-existing checkpoints (main folder, NOT part of the comparison-test matrix — reference only):

- PPO ×3 seeds (main folder, not reused) — `IsaacLab/logs/rsl_rl/ur5e_lift/2026-07-28_23-53-22_ppo_s1/model_1499.pt` (+ `s2`, `s3`)
- PPO (pre-freeze, Day-9 2-algorithm record) — `IsaacLab/logs/rsl_rl/ur5e_lift/2026-07-19_16-29-57/model_1499.pt`
- cPPO (pre-freeze, Day-9 2-algorithm record) — `IsaacLab/logs/rsl_rl/ur5e_lift_cppo/2026-07-19_12-05-49/model_1499.pt`
