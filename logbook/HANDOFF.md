# HANDOFF — paste this into a new session

Written 2026-07-29 (Day 19). Overwrite this file whenever the next action changes.

```
Read logbook/00_INDEX.md and logbook/03c_multialgo_benchmark.md, then continue Layer 1.

State: Step 0 CLOSED (Day 18) — EE offset [0,0,0.16] verified correct, do NOT change it;
the "1.3 cm" figure was an artefact; gripper USD is NOT being rebuilt (visual only).

Day 19: env is SETTLED and is ONE change away from the proven 2026-07-19 env.
1. APPLIED: GRIPPER_OPEN=0.8 / GRIPPER_CLOSE=0.0 (was backwards). play.py gate PASSED —
   weld latches. The stale checkpoint places sloppily because joint_pos_rel on
   finger_joint flipped sign; OOD for a checkpoint being discarded. Not a bug.
2. REVERTED: arm velocity_limit_sim is back at 3.14. Tried 1.0 rad/s; a full 1500-iter
   PPO run gave viol_singularity = 0.0000% converged (vs 15.24%) and manipulability_min
   0.0547, above the 0.045 floor. A slow arm satisfies the constraint by construction =>
   lambda never activates => cPPO's gradient equals PPO's => no safety axis, no result.
   *** DO NOT LOWER velocity_limit_sim. ***
3. REVERTED: episode_length_s is back at 5.0 s. cost_limit is an EPISODIC budget over a
   per-step cost, so episode length and cost_limit must move together or not at all.
4. cost_limit=25 and MANIP_FLOOR=0.045 keep their Day-9 calibrations. Cost function
   frozen: 3 terms, one binding, no FOV term.
5. KEEP logs/rsl_rl/ur5e_lift/2026-07-28_23-24-42_ppo_s1_vel1_ep7 — it is the velocity
   sensitivity analysis for Discussion, not a failed run.

Next action:
1. Commit the shelved contact-env files SEPARATELY (working tree is dirty) so the tag
   points at a clean, reproducible tree.
2. Freeze + git-tag the env. Nothing in ur5e_robotiq.py, ur5e_lift_env*.py or costs.py
   changes after this. No re-probe needed — this is the proven env.
3. Launch PPO x3 seeds (rsl_rl). Gate = PPO + cPPO seeds done.

Working tree is dirty with shelved contact-env files — commit those separately BEFORE
the freeze commit so the tag points at a clean, reproducible tree.

Cut order is in 03c. TD3 is first cut, HARD CUT Aug 6 EOD. Writing due Aug 11.
Do not let the parked qualitative pose figure (Aug 7-11 block) pull work forward.
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

## Useful commands

```bash
cd ~/Abdur_Rabbi_THESIS/IsaacLab

# mount diagnostic (--hold keeps the GUI open)
./isaaclab.sh -p ../ur5_grasp/tools/check_gripper_mount.py --headless
./isaaclab.sh -p ../ur5_grasp/tools/check_gripper_mount.py --hold

# play PPO (default agent)
./isaaclab.sh -p ../ur5_grasp/scripts/play.py \
    --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 1 --seed 42

# play cPPO (also switches the runner to LagrangianRunner)
./isaaclab.sh -p ../ur5_grasp/scripts/play.py \
    --task Isaac-Lift-Cube-UR5e-Play-v0 \
    --agent rsl_rl_cppo_cfg_entry_point --num_envs 1 --seed 42
```

Pre-freeze checkpoints (superseded once the 3-seed runs land):

- PPO — `IsaacLab/logs/rsl_rl/ur5e_lift/2026-07-19_16-29-57/model_1499.pt`
- cPPO — `IsaacLab/logs/rsl_rl/ur5e_lift_cppo/2026-07-19_12-05-49/model_1499.pt`
