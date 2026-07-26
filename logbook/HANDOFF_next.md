HANDOFF — UR5e Safe-RL Thesis · RH-P12-RN contact-grasp TRAINING (Day 16, 2026-07-26)

READ FIRST: logbook/00_INDEX.md, then logbook/05_layer3_sim2real.md (full gripper build +
calibration record). Code: ur5_grasp/robots/ur5e_rhp12.py and
ur5_grasp/tasks/lift/ur5e_rhp12_env_cfg.py. Then continue below.

NOTE: this file previously held the Layer 2 (IBVS) handoff. That work is finished and its
final state now lives in logbook/04_layer2_ibvs.md — nothing is lost by this overwrite.


## GOAL OF THIS SESSION
Train PPO on the RH-P12-RN contact-grasp env and compare it against the Layer 1 weld
baseline. Success criterion: a trained policy that grasps and lifts the cube using real
finger contact, plus a number for how much slower/harder it is than the weld env.

WHY IT MATTERS: Layer 1 grasps via a proximity weld. That is currently an unexamined
shortcut an examiner can attack. This run converts it into a MEASURED, JUSTIFIED
abstraction. Either result is publishable; only not checking is indefensible.


## STATE — what is already done and verified
- RH-P12-RN imported, mounted to the UR5e flange, loads as ONE articulation
  (10 joints / 12 bodies). Build report: ur5_grasp/tools/make_rhp12_report.txt.
- It GRIPS with contact forces alone, no weld. Calibration closed:
  TCP_OFFSET = 0.130 gives pad face gap 0.0413 m against a 0.0412 m cube (delta 0.1 mm),
  reproducible to 0.2 mm across runs, q_final stalls at 0.876.
  Evidence: results/rhp12_grasp_sweep.txt.
- Task ids registered: Isaac-Lift-Cube-UR5e-RHP12-v0 and -RHP12-Play-v0.
- ACTION SPACE IS UNCHANGED from Layer 1 (6 arm joints + 1 binary gripper scalar), so
  policies, network shapes and the cPPO agent all remain directly comparable.
- Layer 1 files are FROZEN and were never modified. Everything here is additive.


## ✅ GEOMETRY CHECK — DONE, PASSED (2026-07-26)
Ran and cleared. `results/rhp12_geometry_check.txt`, closed-pad numbers:
ee_frame vs pad origins 0.0251 m (gate < 0.03), height above table +0.2123 m (gate > 0.02),
ee_frame -> cube 0.2731 m (gate 0.05-0.60). The reach target is NOT in the table — the
earlier worry that it sat only ~0.065-0.078 m up was wrong; it is at +0.212 m.

`TCP_OFFSET = 0.130` STANDS. Do not "correct" it toward the open-pose value (~0.077).
The fingers curl forward as they close (grasp centre travels 0.0765 -> 0.1049 m), so 0.130
is a CLOSING TCP, and the contact sweep — not any body-origin proxy — is the authority.
The check script was fixed on Day 16 to probe open AND closed and to gate on the closed
pose only; detail in logbook/05_layer3_sim2real.md.

Re-run it only if TCP_OFFSET, the ready pose, or the cube spawn changes:

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/rhp12_geometry_check.py \
        --task Isaac-Lift-Cube-UR5e-RHP12-Play-v0 --num_envs 1


## TRAINING
Smoke test first if anything above changed:

    ./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
        --task Isaac-Lift-Cube-UR5e-RHP12-v0 --headless --num_envs 256 --max_iterations 20

Then the full run (tmux, this is hours):

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
        --task Isaac-Lift-Cube-UR5e-RHP12-v0 --headless --num_envs 4096 \
        2>&1 | tee ~/Abdur_Rabbi_THESIS/logbook/05_rhp12_ppo.log

Visual check afterwards:

    ./isaaclab.sh -p ../ur5_grasp/scripts/play.py \
        --task Isaac-Lift-Cube-UR5e-RHP12-Play-v0 --num_envs 16


## HOW TO READ THE RUN — do not panic early
- DO NOT judge before ~500 iterations. Layer 1 needed 1500. At iteration 20 the policy is
  random; watching it fumble in the GUI is expected behaviour, not a symptom. (This already
  caused one false alarm on Day 16.)
- Watch `Episode_Reward/lifting_object`. NOTE ITS MEANING CHANGED: on this env it is the
  dense `object_lift_progress`, not the 0/1 `object_is_lifted`, so it now pays partial
  credit for merely raising the cube and its scale is NOT comparable with the Layer 1
  figures (which climbed 0.12 -> 2.16). Read it for SHAPE, not level: it should start
  small-but-nonzero (the ramp is reachable from the first nudge) and rise. Flat at exactly
  zero past ~100 iterations means the policy is not even touching the cube — that is a
  geometry or contact problem, not an exploration one, and more iterations will not fix it.
- EXPECT IT TO BE SLOWER THAN LAYER 1. Under the weld, grasping is free the instant the
  gripper closes near the cube. Under real contact the policy must discover an alignment
  precise enough for two flat pads to meet the cube faces. That gap is the COST OF THE WELD
  and is the headline number this session exists to produce. Record it either way.
- SHAPING IS ALREADY APPLIED (Day 16, decided up front rather than after a stall):
  `lifting_object` is now the dense `object_lift_progress` from
  ur5_grasp/tasks/lift/rhp12_rewards.py. Identical to the stock term at/above 0.04 m,
  gated ramp below. Full rationale in logbook/05_layer3_sim2real.md.
  CONSEQUENCE: raw episode reward is NO LONGER comparable with Layer 1's 166.3/167.2.
  Compare on lift-success % (scripts/eval_success.py) and violation % (_apply_cost) only,
  and state the shaping as a caveat in the write-up.
- If it STILL stalls, the next honest step is a contact-sensor bonus on the r2/l2 pads
  (activate_contact_sensors is currently False), NOT loosening the physics back toward a
  weld, and NOT a "gripper closed near cube" bonus — that predicate is _apply_weld's latch
  condition and would reinstate the weld in reward-space.

COMPARISON TARGET (Layer 1, frozen, from logbook/03_cppo_benchmark.md and
results/03_cppo_vs_ppo_results.docx): 1500 iters at num_envs 4096, MANIP_FLOOR=0.045,
cost_limit=25. cPPO reward 166.3 vs PPO 167.2, both 100% lift success; singularity
violation 6.65% (cPPO) vs 16.86% (PPO).
USE THE SUCCESS AND VIOLATION FIGURES, NOT THE REWARD — the reward function differs now.

WHAT WOULD KEEP THE WELD DEFENSIBLE: the thesis claim is about SAFETY, not grasp mechanics.
The weld is a valid abstraction if swapping in real contact leaves that claim intact — PPO
still learns the task, and (if a cPPO run follows) the cPPO-vs-PPO violation gap reproduces
in DIRECTION and roughly in MAGNITUDE. If real contact instead pushes the policy into
near-singular wrist poses to close the fingers, the weld was hiding an interaction between
grasping and the safety constraint, and that must be stated openly in the limitations.
MINIMUM DEFENSIBLE VERSION if time runs short: PPO alone on the contact env, showing the
task is learnable without the weld. That proves the weld did not fabricate the task.


## AFTER PPO
1. Update logbook/05_layer3_sim2real.md + run_log.md with the curve and final numbers.
2. Only then consider a cPPO run on this env (agent cfg entry point
   `rsl_rl_cppo_cfg_entry_point` is already registered on the RHP12 task ids).
3. Feed the result into Thesis_Documentation/Methods_Chapter_Layer1.md as the weld
   validation subsection.


## GOTCHAS
- tmux is mandatory for long runs; use absolute paths for tee/log files.
- Clear `.git/index.lock` before commits: `rm -f ~/Abdur_Rabbi_THESIS/.git/index.lock`.
- Cameras are NOT needed here — do not pass `--enable_cameras` (that was Layer 2).
- Gripper joint order is INTERLEAVED: `[...arm x6, 'rh_l1', 'rh_p12_rn', 'rh_l2', 'rh_r2']`.
  Always resolve gripper joints by NAME via `find_joints`, never by positional index.
- Any script that calls `env.reset()` in a LOOP must wrap the whole loop in a single
  `torch.inference_mode()` block — the env publishes safety-cost tensors into `self.extras`,
  and resetting outside inference mode raises
  "Inplace update to inference tensor outside InferenceMode".
- NVIDIA driver drifted off the frozen 580.159.03 once via auto-update and needed a reboot;
  consider `apt-mark hold` on the driver.
- IsaacLab is pinned to the v2.3.0 TAG (`frozen/2.3.0`), not the branch.


## UNCOMMITTED on the lab PC (push when convenient)
    cd ~/Abdur_Rabbi_THESIS && rm -f .git/index.lock
    git add -A && git commit -m "RH-P12-RN gripper: real contact grasp env + calibration"
    git push
New this session: ur5_grasp/assets/rh_p12_rn/, ur5_grasp/assets/ur5e_rhp12.usd,
tools/make_ur5e_rhp12_usd.py, robots/ur5e_rhp12.py, tasks/lift/ur5e_rhp12_env.py,
tasks/lift/ur5e_rhp12_env_cfg.py, scripts/rhp12_grasp_sweep.py,
scripts/rhp12_geometry_check.py, results/rhp12_grasp_sweep.txt.
Updated: tasks/lift/__init__.py, logbook/05_layer3_sim2real.md, run_log.md,
Thesis_Documentation/07_Troubleshooting.md.
