# Matrix v2 — PARTIAL Results: 3-of-5 Arms (ppo / ctrl / cppo), 10 Seeds

Written 2026-08-01 (Day 24). Training + evaluation both complete for this batch.

**This is explicitly a 3-of-5-arm subset of the audit's registered v2 matrix
(`ALGORITHM_AUDIT.md` §4).** `cppo10` and `sac` are **not** included. Do not read this file as
Step 6 of `RUN_CHECKLIST_v2.md` being complete — it is not. "Does an actively-binding safety
budget help" is **not yet answered**; this batch only speaks to "does a budget that is
borderline-to-binding depending on seed help."

Companion PDF with identical content: `MATRIX_V2_PARTIAL_3ARM_report.pdf` (English — no
Bengali-script font was available in the build sandbox; see `run_log.md`, Day 24).

---

## 0. Provenance

| | |
|---|---|
| Commit / tag | `567e4c0`, tag `matrix-v2` |
| Task | `Isaac-Lift-Cube-UR5e-v0` (frozen weld env) |
| Training seeds | 1, 2, 3, 4, 5, 50, 51, 52, 53, 54 &nbsp;(n = 10 per arm) |
| Training | 1500 iterations, num_envs = 4096, rsl_rl 3.0.1 |
| Eval seeds | 101, 102, 103 &nbsp;(n = 3, disjoint from training) |
| Eval protocol | 1000 episodes per (checkpoint × eval-seed), num_envs = 128, deterministic policy, observation corruption off |
| `MANIP_FLOOR` | 0.06 (recalibrated this session; was 0.045) |
| `JOINT_LIMIT_MARGIN` | 0.175 rad (unchanged value; **reclassified active**, was "inactive by construction") |
| `COLLISION_Z_FLOOR` | 0.05 m (unchanged, confirmed inactive) |
| `cost_limit` | 25.0 (unchanged; see §4 for why this is a seed-dependent question, not a fixed verdict) |
| Arms in this batch | `ppo`, `ctrl`, `cppo` only |
| Arms **not** in this batch | `cppo10`, `sac` |

Checkpoint hygiene note: `logs/rsl_rl/ur5e_lift_cppo/` also contains 3 superseded pre-audit
`cppo_s1/s2/s3` runs (2026-07-30, gradient-clip-bug era) under the same labels as the new ones.
All numbers below are filtered to the 2026-08-01-dated runs only, verified by checkpoint path.
The old runs should be archived out of that folder; not done yet.

---

## 1. Reading order

Per the audit's reporting rule (`ALGORITHM_AUDIT.md` §4), the decomposition comes first, not a
headline `cppo`-vs-`ppo` number:

```
(cppo − ppo)  =  (ctrl − ppo)          +  (cppo − ctrl)
                  the implementation       the constraint
                  artifact                 ← the only part licensed as a safe-RL result
```

---

## 2. `ctrl` vs `ppo`: confirmed null — bitwise, not just statistically

Every `Train/mean_reward` and `safety/*` training scalar matches between `ppo_sN` and `ctrl_sN`
to **four decimal places, for all 10 seed pairs**, including chaotic near-zero quantities like
`manipulability_min` (`ppo_s3` and `ctrl_s3` both read `7.419e-06` tail-mean). That level of
agreement is too precise to be statistical — it was checked at the file level before being
trusted:

- Event files are genuinely distinct processes (different MD5 hashes, different sizes — 3.13 MB
  ppo vs 3.59 MB ctrl, consistent with ctrl's extra cost-critic logging — different PIDs). Rules
  out a duplicated-file logging bug.
- The two `model_1499.pt` checkpoints were opened directly and every stored tensor compared by
  content hash. **All 68 tensors in `ppo_s1`'s checkpoint (the complete trained actor and
  reward-critic networks) were found byte-for-byte inside `ctrl_s1`'s checkpoint** (which
  additionally carries `ctrl`'s own cost-critic tensors, 100 total). Parameter-name strings
  recovered from the pickle stream confirm these are the `actor.0/2/4/6` and `critic.0/2/4/6`
  weight/bias tensors.

**Interpretation.** With the Day-23 gradient-clip fix applied (actor+reward-critic clipped
separately from the cost critic) and λ pinned to 0, `ctrl`'s actor loss is algebraically
identical to `ppo`'s at every step. Given that the two runs also converge to identical weights,
the RNG stream driving action sampling and minibatch permutation was evidently **not** perturbed
by the cost critic's extra parameter draws in this codebase — the opposite of what the audit's
A4 finding assumed ("every subsequent random draw... is offset"). The effect is verified above;
the exact mechanism (e.g. separate CPU/CUDA generator streams) was not traced in source and
should be treated as an open question, not asserted.

**Reconfirmed independently at evaluation time** (§4): every eval metric matches exactly between
`ppo` and `ctrl` on the frozen, deterministic policy, across all 90 valid (checkpoint × eval-seed)
rows.

This is the strongest possible form of the audit's expected null result — not merely
indistinguishable, but exactly reproduced, independently, across every tested seed.

---

## 3. `cppo` vs `ctrl` — task performance (no meaningful cost)

Training-time (tail-mean over last 10% of iterations, n = 10 seeds):

| | reward (mean ± std) | viol_singularity (soft-margin step-fraction) |
|---|---|---|
| ppo / ctrl (identical) | 133.57 ± 1.58 | 0.318 ± 0.261 |
| cppo | 132.65 ± 1.80 | 0.261 ± 0.124 |

Decomposition: `(cppo − ppo) = (ctrl − ppo) + (cppo − ctrl) = 0.000 + (−0.920)` — the entire
reward gap (≈0.7%) is attributable to the constraint, none to the artifact, because the artifact
term is exactly zero (§2).

Evaluation-time (frozen deterministic policy, mean over 10 seeds, each seed = mean of 3 eval
seeds), goal-reach reported as a **distance distribution plus success at 1/2/5 cm**, never a
single threshold (audit finding A6 — the weld makes the cube's pose the TCP's pose, so a single
cutoff saturates and cannot discriminate two converged policies):

| metric | ppo / ctrl | cppo |
|---|---|---|
| lift success (≥ 50% of commanded goal height) | 99.86% | 99.87% |
| goal-reach < 1 cm | 94.28% | 96.49% |
| goal-reach < 2 cm | 99.08% | 99.17% |
| goal-reach < 5 cm | 99.81% | 99.85% |
| goal distance: mean / median / p90 (m) | 0.0060 / 0.0047 / 0.0080 | 0.0054 / 0.0042 / 0.0068 |

(Pooled over all 30,000 scored episodes per arm — 10 seeds × 3 eval-seeds × 1000 episodes. Both
arms have a small number of outlier catastrophic-miss episodes, max goal distance > 1 m for both;
not further investigated here, flagged for anyone extending this analysis.)

Task performance is essentially unaffected by the constraint, at either training or evaluation
time — consistent with the original Day-9 headline ("safety at no task cost"), now on a
10-seed, checkpoint-hash-verified footing instead of 1 seed.

---

## 4. Safety — leading with actual singularity crossings, not the soft-margin fraction

Per the audit's reporting rule, this section leads with **episodes that reached an actual
singularity (w < 1e-4)** and the **mean episode-minimum manipulability**, not the soft-margin
step-fraction (which exaggerates differences by testing a binary threshold on a continuous
margin).

**Pooled over 30,000 evaluation episodes per arm** (10 training seeds × 3 eval seeds × 1000
episodes each, deterministic frozen policy):

| | ppo / ctrl | cppo |
|---|---|---|
| **True singularity crossings (w < 1e-4)** | **1.343%** (403 / 30,000 episodes) | **0.250%** (75 / 30,000 episodes) |
| Mean episode-minimum manipulability | 0.05471 | 0.06169 |
| Worst single-episode manipulability | 0.000001 | 0.000001 |
| Joint-limit touched at all | 5.37% of episodes | **0.00% of episodes, all 10 seeds** |
| Collision touched at all | 0.13% of episodes | 0.017% of episodes |
| Episodic safety cost: mean / p90 / max | 47.68 / 180.63 / 343.01 | 18.41 / 73.26 / 224.07 |

cPPO cuts true singularity crossings by roughly 5.4×, and **eliminates joint-limit touches
entirely across all 10 seeds** — the cleanest single result in this dataset, and notable given
`JOINT_LIMIT_MARGIN` was only reclassified from inactive to active this session (§0). Collision
was already near-zero for both arms and stays near-zero.

**Honest counter-note, not smoothed over:** the *worst single episode* manipulability is
identical between arms (`0.000001` for both). cPPO reduces how *often* and how *consistently*
the policy approaches a singularity — it does not obviously reduce how bad the rare worst-case
excursion is. State this plainly rather than only reporting the metrics that look best.

### 4.1 The stronger finding: cPPO collapses seed-to-seed safety VARIANCE

`ctrl`'s natural (unconstrained-equivalent — λ = 0, but the cost critic still estimates and logs
cost) per-seed episodic cost varies enormously:

| seed | 1 | 2 | 3 | 4 | 5 | 50 | 51 | 52 | 53 | 54 |
|---|---|---|---|---|---|---|---|---|---|---|
| ctrl natural cost (training, tail-mean) | 102.1 | 7.7 | 162.3 | 30.0 | 19.1 | 8.6 | 1.8 | 106.9 | 18.8 | 7.9 |
| cppo natural cost (training, tail-mean) | 18.0 | 16.6 | 11.9 | 19.7 | 24.1 | 23.9 | 17.0 | 9.5 | 23.5 | 12.0 |
| cppo λ (final) | 0 | 0 | 0 | 0 | 0.013 | 0.001 | 0 | 0 | 0.154 | 0 |

Range: `ctrl` 1.8–162.3 (~90×). `cppo` 9.5–24.1 (~2.5×), pulled into a band close to
`cost_limit = 25` regardless of whether that seed's `ctrl` counterpart was very low or very high.

> **Correction 2026-08-01 (same day, while drafting the Results chapter).** This paragraph
> originally ended: *"λ engages (departs from 0) precisely on the seeds whose cost sits closest to
> the budget (5, 50, 53) — internally consistent with the dual-ascent mechanism."* **That reading
> is wrong and is retracted.** The λ row above is λ at the **final iteration**, not a summary of
> its trajectory. A non-zero final λ (seeds 5, 50, 53) means the policy was still sitting at the
> budget when training ended and the dual variable had not relaxed — it does **not** mean λ stayed
> at 0 throughout on the other seven seeds, and §2 rules that out: a run whose λ is identically 0
> at every iteration is algebraically `ctrl` and would converge to `ctrl`'s weights, yet seed 1
> ends at natural cost 18.0 against `ctrl_s1`'s 102.1. λ must have engaged hard on the high-cost
> seeds and relaxed back to 0 once cost was driven under budget — which *is* the dual-ascent
> mechanism, just not the version the retracted sentence described.
>
> **Not yet measured:** the per-iteration λ curves were never extracted for this batch. The
> paragraph above is the reading the converged costs *require*, not a directly observed
> trajectory. Pull `Loss/cost_lambda` per iteration from the training event files to convert the
> inference into evidence. Until then, do not quote a λ peak or an engagement iteration for any
> seed.

Confirmed independently on held-out evaluation episodes (not training rollout): cost mean
47.68 → 18.41 (−61%), but **std across seeds 54.04 → 5.36, a ~10× tightening**. Which basin
unconstrained PPO happens to land in is close to a lottery — some seeds are accidentally safe,
some severely unsafe, for the identical algorithm and environment. cPPO's main measured
contribution in this batch is making that outcome consistent, not just better on average, at
essentially no task-performance cost (§3).

Consequence for the `cost_limit = 25` question the audit's §A2 raised: it is **not** a fixed
"slack or binding" verdict — it depends heavily on which seed. For roughly a third of the 10
seeds the natural cost exceeds or sits close to budget (binding); for the rest it is comfortably
under (slack). `cost_limit` was held at 25 rather than retuned again this session (see
`run_log.md`, Day 24, and `rsl_rl_cppo_cfg.py`'s inline comment) — retuning it further is a
reasonable next step but was deliberately not stacked onto an already-large recalibration pass.

---

## 5. Limitations — explicitly in scope for this batch

- **3 of 5 arms only.** `cppo10` and `sac` are not included. "Does an actively-binding budget
  help" is unanswered here — only "does a budget that's borderline-to-binding depending on seed
  help" is in scope.
- **Two data-hygiene traps found and filtered, not fixed at the source.** (1) 3 superseded
  pre-audit `cppo_s1/s2/s3` training runs (2026-07-30) still sit in the same experiment folder
  as the new ones under identical labels — excluded here by checkpoint-path date; checkpoint
  selection in `run_eval_matrix_v2_3arm.sh` resolves correctly via modification time (verified),
  but this is a standing risk for any future automated aggregation. (2) `eval_policy_results.csv`
  (append-only) carried 20 stale rows from the old, superseded `run_eval_policy.sh` sweep
  (pre-freeze `ppo_s1/s2/s3`, pre-audit `cppo_s1/s2/s3`) — filtered by checkpoint path before
  analysis. The per-episode CSVs under `eval_episodes/` were unaffected (each run overwrites its
  own file rather than appending).
- **λ trajectories were never extracted** — only λ at the final iteration was recorded (§4.1).
  The engagement-then-relaxation account of the high-cost seeds is an inference from the converged
  costs plus §2's equivalence argument, not a measurement. See the §4.1 correction note.
- **`skrl_ppo_cfg.yaml` (the PPO bridge arm) remains unverified under skrl 2.1.0** — open since
  Day 22-23, not touched this session.
- Both arms show a small number of outlier catastrophic-miss episodes (goal distance > 1 m) in
  the pooled evaluation data — not investigated further here.

---

## 6. Provenance / reproducibility

Commit `567e4c0`, tag `matrix-v2`. Training: 10 seeds/arm, 1500 iterations, num_envs = 4096.
Evaluation: `run_eval_matrix_v2_3arm.sh`, 3 eval-seeds (101/102/103), 1000 episodes each,
num_envs = 128, deterministic policy. Full training scalars:
`Comparison_test/ur5_grasp/tools/summarize_runs_report.txt`. Full evaluation data:
`Comparison_test/ur5_grasp/tools/eval_policy_results.csv` (filter to `checkpoint` paths dated
2026-08-01) and per-episode CSVs under `Comparison_test/ur5_grasp/tools/eval_episodes/`.
