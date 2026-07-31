# HANDOFF — paste this into a new session

Updated 2026-07-30 (Day 22, close). Overwrite whenever the next action changes.

```
Read logbook/00_INDEX.md, then logbook/09_comparison_test.md, then
Comparison_test/results/LAYER1_RESULTS_3seed.md, then the entries dated "2026-07-30 (Day 22...)"
in Comparison_test/run_log_new.md. Read them before touching code.

WORKING FOLDER: Comparison_test/  (renamed 2026-07-30 from "Comparison test" — the space is
gone, so shell quoting is no longer needed. run_log entries before Day 22 still show the old
spaced name; that is deliberate, they are a dated record.)
    cd ~/Abdur_Rabbi_THESIS/Comparison_test
    ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/<script>.py
Log paths are CWD-relative, so always cd into Comparison_test/ first.

SANDBOX LIMIT: you cannot run Isaac Sim (no GPU). Touhid runs everything on his lab PC.
Write code, give exact commands, and READ THE REPORT FILES the scripts write — do not ask him
to paste output, and never claim you verified something you did not. Say plainly which parts
you verified and which you could not.

STANDING RULE, now demonstrated FIVE times: a script here that does not write a FLUSHED report
file cannot be run for a result. `simulation_app.close()` discards block-buffered stdout, and
piping through `tee` is what CAUSES the buffering — so both "run it plain" and "run it through
tee" lose everything, and from outside the result is indistinguishable from a crash. Before
telling Touhid to run ANYTHING, grep it for `_FH` / `log()`. If it only print()s, add the report
pattern FIRST. Victims so far: the live demo, the grasp test, check_robotiq_pads, and
eval_success.py (caught pre-run on Day 22 — the only one caught in time).
Still unfixed (2f-85-only, closed workstream, left alone deliberately):
check_gripper_colliders.py, check_gripper_mount.py.

=============================================================================
STATE — LAYER 1 IS DONE. The must-pass deliverable is measured and written up.
=============================================================================
PPO x3 + cPPO x3 on Isaac-Lift-Cube-UR5e-v0 (frozen weld env, UR5e + Robotiq 2f-85),
1500 iters, num_envs=4096, seeds 1/2/3, ~10 min per run. Then eval_success at 512 episodes
per checkpoint with a FIXED eval seed 42 (every policy scored on identical cube spawns).

  Metric (mean +- sd, 3 seeds)   PPO                cPPO
  Lift success                   100.00% +- 0.00    100.00% +- 0.00
  Goal-reach success              52.86% +- 50.25   100.00% +- 0.00   <- THE headline metric
  Train reward                   132.00  +- 37.25   162.78  +- 4.04
  Singularity violation           83.72% +- 9.12     42.27% +- 24.74
  Joint-limit violation           30.27% +- 28.06     0.85% +- 0.82

  Per-seed goal-reach — PPO: 58.6 / 0.0 / 100.   cPPO: 100 / 100 / 100.

Full table + limitations + reproduce commands: Comparison_test/results/LAYER1_RESULTS_3seed.md

Four things about this result that must not be lost:
1. cPPO wins on EVERY axis. The registered hypothesis was "safety at no task cost"; the
   measurement is safety at a task GAIN. Do not undersell it, and do not overclaim the
   mechanism — the regulariser explanation (PPO wrecks its own learning by driving into joint
   limits and singularities) is PLAUSIBLE and UNTESTED. Say so.
2. The strongest finding is CONSISTENCY, not the means. PPO produced a totally failed policy
   (0/512 goal-reach) on 1 of 3 seeds. Reward sd 37.25 vs 4.04. That is the argument.
3. "100% lift" is nearly uninformative — the weld latches whenever the policy commands close
   within 6 cm, so lifting is close to free, and BOTH arms get 100%. GOAL-REACH is the
   discriminating metric. Day 10 reported lift success alone; do not repeat that.
4. lambda -> 0 is CORRECT, not a failure: episodic cost 9.78-24.26 against cost_limit 25. The
   constraint was met so the multiplier decayed. The 42% violation fraction coexists with a
   satisfied budget because cost is a MARGIN (1 - w/0.045) while the violation counter is
   BINARY: 25 over 250 steps permits w ~ 0.0405, i.e. sitting 10% under the floor continuously.
   The constraint did what it was told; the SPECIFICATION is the weak point. Report as a
   limitation. Do NOT quietly retune cost_limit until the number looks nicer.

SETTLED — do not reopen any of these without Touhid explicitly asking:
- Day-10's single-seed headline (cPPO 6.65% vs PPO 16.86%) is RETIRED. Three seeds give
  42.3% vs 83.7%. Env code was verified byte-identical to tag layer1-env-freeze and the runs'
  own dumped params/*.yaml confirm every locked setting, so this is seed variance, NOT a code
  change. Don't re-investigate it; write the Methods paragraph.
- The matrix runs on -v0 (weld). Reversing the Day-20/21 repoint to -SimpleGripper-v0 was a
  schedule call made with the numbers in hand.
- SimpleGripper PASSED its contact-grasp test (fingers stalled at a 62.8 mm pad gap against a
  30 mm closed target; cube held after the pin released). It is a SEPARATE demonstrated
  real-contact result on a separate env — never merge its numbers with the -v0 table. All its
  geometry lives in ONE file, ur5_grasp/robots/gripper_geometry.py. Do not re-derive it.
- The Robotiq 2f-85 CONTACT study is CLOSED PERMANENTLY, on schedule grounds — NOT because the
  asset was broken (its pads have 10 enabled convexHull colliders and its linkage works: 84.9 mm
  gap vs an 85 mm spec). If asked, read the warning block atop tools/check_robotiq_pads.py:
  that script's verdict line is wrong and is kept only as methods material.
- Env/cost frozen: MANIP_FLOOR=0.045, cost_limit=25, one binding constraint (singularity;
  collision and joint-limit costs are ~0 for cPPO). Arm speed 3.14 rad/s —
  *** DO NOT LOWER velocity_limit_sim ***, it zeroes the safety signal and collapses cPPO
  into PPO. Episode 5.0 s: cost_limit is an undiscounted EPISODIC budget, so changing episode
  length silently rescales the constraint. Change both together or neither.
- IMPORT TRAP: tasks/lift/__init__.py registers the SimpleGripper cfg alongside -v0, so
  gripper_geometry.py runs at package-import time and raises FileNotFoundError if
  assets/wrist_frame.json is missing — which breaks -v0 too. That JSON is now committed; if a
  task import ever dies on it, re-run tools/check_wrist_frame.py.
- LOG-DIR TRAP: experiment_name comes from the AGENT cfg, not the task, so two different robots
  can land in the same logs/rsl_rl/<exp>/ directory. Verify which env a run used by grepping
  <run_dir>/params/env.yaml for the robot USD filename. Never reuse a run_name across tasks.

=============================================================================
DAY 23 CLOSE (2026-07-31): EVAL SWEEP DONE. 18 runs, 18 000 episodes. READ THIS FIRST.
=============================================================================
Layer 1 is now measured properly. Numbers: results/LAYER1_RESULTS_eval.md (GENERATED — do not
hand-edit; regenerate with `python3 results/scripts/summarize_eval.py --write`).
Interpretation + limitations: results/LAYER1_FINDINGS.md (hand-written, kept separate on
purpose). The Day-22 results/LAYER1_RESULTS_3seed.md is SUPERSEDED.

  Metric (mean +- sd over 3 TRAINING seeds)   cPPO              PPO
  Goal-reach < 1 cm                           96.52% +- 3.45    34.72% +- 56.54
  Lift (>= 50% of goal height)                99.99% +- 0.02    69.89% +- 52.01
  Episodic cost (budget 25)                   17.75  +- 7.41    261.31 +- 163.49
  Joint-limit, % of steps                      0.00% +- 0.00    35.34% +- 30.62
  Singularity, % of steps                     45.07% +- 26.72   80.48% +- 14.92
  Episodes reaching w < 1e-4                  0.0/0.1/0.0%      7.9/11.6/100%
  Per-seed goal-reach @1cm  -- cPPO 97.2/99.6/92.8   PPO 4.2/0.0/100.0

FOUR THINGS THAT MUST NOT BE LOST WHEN WRITING THIS UP:
1. THE EPISODIC COST IS THE STRONGEST NUMBER, not the violation fraction. PPO spends 261 per
   episode against a budget of 25; cPPO spends 17.75. It is the exact quantity the Lagrangian
   constrains, with cost_limit fixed on Day 9 — no reporting choice flatters it.
2. REPORT SINGULARITY CROSSINGS (w < 1e-4), NOT THE STEP FRACTION. The three ways of asking
   separate by 1.8x (step fraction), 8x (episode-min w) and ~100x (crossings). The step
   fraction is a binary test on a soft margin -- the Day-22 "limitation 2" problem -- and it
   undersells the result by ~50x. Report it WITH the caveat, lead with crossings.
3. ppo_s3 MUST BE REPORTED. It matches/beats cPPO on task (100% @1cm, mean distance 0.0042 m vs
   cPPO's 0.0058 m) while being the WORST run in the matrix on singularity (92.0% of steps) and
   5x over budget. So the claim is "the constraint buys reliability and safety", NOT "PPO cannot
   do the task". Do not overclaim.
4. ppo_s2's failure mode is IDENTIFIED: it lifts and then puts the cube back DOWN. 100% of
   episodes get the cube above the bar (peak z ~0.39-0.45 m), only 9.8% are still there at the
   end (final z ~0.136 m against goals of 0.27-0.50 m). All its episodes reach an actual
   singularity. The mechanism (loses height control from singular configurations) is PLAUSIBLE
   and UNTESTED -- say so.

SETTLED: eval-seed spread is 1.05 percentage points against 56.5 across training seeds (~50x).
ppo_s2's 0% is the policy, not a bad exam. Do not re-litigate.

TRAPS FOUND HERE:
- eval_policy_results.csv is APPEND-ONLY and had two stale rows from the crashed sweep. NEVER
  average it with a plain glob -- use summarize_eval.py, which de-duplicates on
  (label, eval_seed), last wins.
- eval_policy.py's `except` block NEVER FIRES: Hydra's hydra_main catches first, so a traceback
  goes to Hydra's output, not the flushed report. A failed run leaves the report ending
  mid-sentence -- that truncation IS the signal.

NEXT: (1) ./run_skrl_seeds.sh PPO 4096 1500, then ./run_eval_policy.sh skrl
      (2) author skrl_sac_cfg.yaml -> 50-iter smoke -> SAC x3
      (3) point make_layer1_figs.py at eval_episodes/*.csv -- the DISTRIBUTIONS are now the
          interesting figure, not the training curves.

=============================================================================
DAY 23 (2026-07-31): TD3 CUT + EVALUATION REBUILT. Historical detail below.
=============================================================================
TD3 IS DROPPED, Touhid's call, six days ahead of the Aug 6 hard cut. The benchmark is
THREE algorithms: PPO / cPPO / SAC. Entry point and --algorithm choice removed. Do not
re-add without a decision-record entry in logbook/03c_multialgo_benchmark.md.

THE DAY-22 SAFETY NUMBERS ARE NOT EVALUATION NUMBERS. The 83.72%/42.27% singularity and
30.27%/0.85% joint-limit figures in results/LAYER1_RESULTS_3seed.md are tail-means over the
last 10% of TRAINING iterations -- a stochastic, still-learning policy with exploration noise
on. They describe the learning process, not the shipped policy. Every safety number must be
re-measured on the frozen policy before it goes in the thesis.

"PPO 0.00% vs cPPO 100.00%" is EXPLAINED and is not a bug: ppo_s2 really did converge badly
(reward 90.7 vs 166.4, object_goal_tracking 4.42 vs 14.78). Checkpoint paths were correct --
not the log-dir trap. But the eval turned it into a step function, because a single hard 5 cm
threshold on a quantity with near-zero within-policy spread can only answer 0 or 100.
ppo_s1's 58.59% was the knife-edge tell.

TRAP, newly found: Metrics/object_pose/position_error tracks wrist_3_link, NOT the cube
(body_name = "wrist_3_link"). Its ~0.16 m floor is the ee_frame offset, not error. Never
quote it as task error.

NEW TOOLING, written and compiling, NOT YET RUN:
  ur5_grasp/scripts/eval_policy.py   supersedes eval_success.py. Counts singularity /
                                     joint-limit / collision violations per EPISODE on the
                                     frozen deterministic policy; reports the goal-distance
                                     distribution plus success at 2/5/10 cm; sums episodic
                                     cost for direct comparison against cost_limit=25;
                                     loads BOTH rsl_rl and skrl checkpoints (this clears the
                                     Day-22 blocker); writes a per-episode CSV.
  ./run_eval_policy.sh               6 checkpoints x 3 eval seeds x 1000 episodes, 128 envs.
                                     Pass "skrl" as arg 1 to include skrl runs.

EVALUATION PROTOCOL, locked by Touhid on Day 23 — these are the reported numbers:
    num_envs 128 | episodes 1000 | eval seeds 101/102/103 | goal-reach bound 1 cm
    lift success = cube reaches >= 50% of THAT EPISODE's commanded goal height
The lift rule is the substantive change: the command's pos_z range is (0.25, 0.50) m so the bar
is ~12.5-25 cm and scales with the ask, whereas the old flat 0.04 m sits ~2 cm above the cube's
resting height, which is why every policy read 100.00% on Day 22. The legacy absolute number is
still written to the CSV for continuity but is NOT the headline.
Eval seeds are 101/102/103, DELIBERATELY disjoint from the training seeds 1/2/3. An earlier
Day-23 draft used 1/2/3 and Touhid caught it: reusing the numbers invites reading "ppo_s1 @
seed 1" as a pairing that does not exist, and puts the eval draw on the same RNG stream the
policy trained against. Every eval seed scores ALL six checkpoints. Keep any new eval seed >= 100.
FIRST SANITY CHECK on the report: `mean commanded goal height` should print ~0.375 m. If it is
far off, des_pos_w z and the cube's world z disagree on frame and every lift number is wrong.

RETRACTED, so it does not get re-litigated: I claimed the 0.04 m lift threshold was trivially
satisfied by the cube's 0.055 spawn height. WRONG. Episode_Reward/lifting_object is 0.117 at
iter 0 (~2 of 250 steps) and 14.61 at iter 1499 (~243 of 250), so the resting height IS below
the threshold. The reward function was NOT changed.

FIRST COMMANDS ON THE LAB PC:
    cd ~/Abdur_Rabbi_THESIS/Comparison_test
    ./run_eval_policy.sh                       # then read ur5_grasp/tools/eval_policy_report.txt
    ./run_skrl_seeds.sh PPO 4096 1500          # unaffected, still queued

=============================================================================
NEXT ACTION — the 3-algorithm comparison. Nothing else is open.
=============================================================================
6 of 12 runs remain: skrl-PPO bridge x3, SAC x3. SAC still needs its config written.
(This block was written for the 4-algorithm plan; read TD3 mentions below as historical.)

Facts already checked in this repo (do not re-derive, but DO re-verify anything you rely on):
- IsaacLab/scripts/reinforcement_learning/skrl/train.py exists.
- Its log path, line 160: os.path.join("logs", "skrl", agent_cfg["agent"]["experiment"]
  ["directory"]) — same cwd-relative behaviour as rsl_rl, so runs must still be launched from
  inside Comparison_test/. Run dir is <timestamp>_<algorithm>_<ml_framework>.
- Template to copy structure from (same env family):
  IsaacLab/source/isaaclab_tasks/.../manipulation/lift/config/franka/agents/skrl_ppo_cfg.yaml
- skrl is an OPTIONAL extra in isaaclab_rl/setup.py ("skrl>=1.4.3"). CONFIRM IT IS INSTALLED
  before writing configs, not after.
- There is NO SAC or TD3 yaml anywhere in this IsaacLab checkout — only skrl_ppo_cfg.yaml
  variants. Those two must be authored from skrl's own docs. THIS IS THE SCHEDULE RISK.

Order:
  1. Confirm skrl imports under isaaclab.sh. If not, install and record the version.
  2. Author configs/skrl_ppo_cfg.yaml first (the bridge) — it is the cheapest way to prove the
     skrl path works at all, and it is the framework-equivalence check.
     Register skrl_cfg_entry_point / skrl_sac_cfg_entry_point / skrl_td3_cfg_entry_point on
     BOTH -v0 and -Play-v0 in ur5_grasp/tasks/lift/__init__.py.
  3. 50-iter smoke for EVERY new algorithm before any full run. This has caught something
     every single time it has been run.
  4. skrl-PPO bridge x3 (4096 envs), then SAC x3, then TD3 x3 (128-256 envs).
  5. Extend results/scripts/make_layer1_figs.py from 2 series to 4 + seed bands. NOTE: its
     DATA path is hardcoded to a dead sandbox path — repoint it at results/tb_csv/, which
     summarize_runs.py now populates automatically.

Tools that already exist — use them, don't rewrite them:
  ./run_ppo_cppo_seeds.sh      6 rsl_rl runs; per-run exit codes + wall-clock; verifies each run
                               by its checkpoint on disk; writes logs/batch_report.txt; does NOT
                               abort the batch on one failure; exit code = number of failures.
  ./run_eval_success.sh        512 episodes x 6 checkpoints, fixed eval seed 42.
  ur5_grasp/tools/summarize_runs.py   TB event files -> flushed report + results/tb_csv/*.csv.
                               Reads only; safe to run mid-batch. Handles skrl dirs only if you
                               extend its log root — currently hardcoded to logs/rsl_rl.

DEADLINES: TD3 hard cut 2026-08-06 EOD, writing due 2026-08-11. Today is Jul 30.
Cut rule, already agreed, do not renegotiate on the day: if TD3 is not tuned and running by
Aug 6 EOD it is DROPPED and the thesis reports three algorithms with the omission stated in
Limitations. Same for SAC on Aug 4. PPO + cPPO + one off-policy baseline is a complete result;
Layer 1 is already secured, so everything from here is upside. Push back if a request risks
the deadline, and say so plainly rather than just complying.

An open, CHEAP experiment recorded but deliberately NOT run: lambda decayed to ~0, so the
constraint is slack; tightening cost_limit to ~8-10 should bind it and cut the violation
fraction, plausibly at no task cost since cPPO is already at 100% goal-reach. ~1 hour for six
runs. Deferred because SAC/TD3 are the schedule risk. Offer it only if the schedule clears.

Update Comparison_test/run_log_new.md AND run_log.md with a dated entry for whatever happens,
and keep logbook/09_comparison_test.md pointed at the current state.
```
