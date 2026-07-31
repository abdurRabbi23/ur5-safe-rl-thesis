> # 🛑 SUPERSEDED 2026-07-31 (Day 23, late) — DO NOT QUOTE
>
> An algorithm audit found this comparison CONFOUNDED. `Loss/cost_lambda` was 0.0 for
> essentially every iteration of all three cPPO runs, and at lambda = 0 the PPO-Lagrangian
> update is algebraically stock PPO — so the constraint cannot be what separated the arms.
> The prime suspect is a single global `clip_grad_norm_` spanning the cost critic, which
> shrank the actor's step in the cPPO arm only.
>
> Full working: `ALGORITHM_AUDIT.md`. Replacement protocol: `../RUN_CHECKLIST_v2.md`.
>
> This file is kept, not deleted: a large apparent effect turning out to be an
> implementation artifact is part of the thesis's diagnostic-discipline narrative.

# Layer 1 — cPPO vs PPO, 3 seeds (2026-07-30, Day 22)

**Task:** `Isaac-Lift-Cube-UR5e-v0` — UR5e + Robotiq 2f-85, proximity-weld grasp.
**Provenance:** `Comparison_test/`, git `d57063a`, tag `comparison-matrix-v0`, clean tree.
Env code byte-identical to `layer1-env-freeze` (verified by `git show … | diff`).
**Training:** 1500 iterations, `num_envs=4096`, seeds 1/2/3, rsl_rl 3.0.1. 10–11 min per run.
**Constraint:** `MANIP_FLOOR=0.045`, `cost_limit=25`, `lambda_lr=0.035`, `lambda_init=0`.
**Evaluation:** 512 episodes per checkpoint, frozen policy, **fixed eval seed 42 for all six**
(identical cube spawns for every policy), `min_height=0.04 m`, `success_tol=0.05 m`.

---

## Headline table (mean ± sd over 3 seeds)

| Metric | PPO (unconstrained) | cPPO (Lagrangian) | Change |
|---|---|---|---|
| **Lift success** | **100.00 % ± 0.00** | **100.00 % ± 0.00** | — |
| **Goal-reach success** | **52.86 % ± 50.25** | **100.00 % ± 0.00** | **+47 pts** |
| Train reward | 132.00 ± 37.25 | **162.78 ± 4.04** | +23.3 % |
| Singularity violation ⚠ | 83.72 % ± 9.12 | **42.27 % ± 24.74** | −49.5 % |
| Joint-limit violation ⚠ | 30.27 % ± 28.06 | **0.85 % ± 0.82** | −97.2 % |

> ⚠ **SUPERSEDED 2026-07-31 (Day 23) — do not quote these two rows in the thesis.**
> They are tail-means over the final 10 % of *training* iterations: a stochastic, still-improving
> policy with exploration noise on, averaged over 4096 envs. They describe the learning process,
> not the frozen policy. Re-measure with `../run_eval_policy.sh`, which counts violations during
> evaluation on the deterministic policy, then rewrite this file.
>
> Also superseded: goal-reach as a single 5 cm threshold. It saturates at exactly 0 or 100
> because the weld leaves almost no within-policy spread in the final cube-goal distance —
> `ppo_s1`'s 58.59 % is the one knife-edge case. Report the distance distribution plus success
> at 2 / 5 / 10 cm instead. The ppo_s2 failure itself is real (train reward 90.7 vs 166.4).
| Cost per step | 1.01 ± 0.68 | **0.07 ± 0.03** | −92.7 % |
| Manipulability (min) | 2.6e−05 ± 4.1e−05 | **1.3e−02 ± 1.1e−02** | ~500× |

Training metrics are tail-means over the final 10 % of iterations.

## Per-seed detail

| Run | Reward | Sing. viol | Joint viol | Cost/step | λ final | Ep. cost | Lift | Goal |
|---|---|---|---|---|---|---|---|---|
| ppo_s1 | 141.93 | 73.87 % | 35.40 % | 0.757 | — | — | 100 % | 58.59 % |
| ppo_s2 | 90.80 | 85.42 % | 55.42 % | 1.773 | — | — | 100 % | **0.00 %** |
| ppo_s3 | 163.29 | 91.88 % | 0.00 % | 0.485 | — | — | 100 % | 100 % |
| cppo_s1 | 163.87 | 54.82 % | 0.93 % | 0.097 | 0.155 | 24.26 | 100 % | 100 % |
| cppo_s2 | 166.16 | 13.77 % | 0.00 % | 0.039 | 0.000 | 9.78 | 100 % | 100 % |
| cppo_s3 | 158.30 | 58.23 % | 1.63 % | 0.083 | 0.059 | 20.89 | 100 % | 100 % |

## Findings

**1. cPPO dominates on every axis.** Safety *and* task, on all three seeds. The original
hypothesis was "safety at no task cost"; the measured result is stronger — safety at a task
*gain*.

**2. The real story is consistency, not the means.** PPO's goal-reach is 0 %, 58.6 %, 100 %
across three seeds (sd = 50.25) — a lottery. cPPO is 100 % on all three (sd = 0). Same for
reward: sd 37.25 vs 4.04. An unconstrained baseline that produces a completely failed policy on
1 of 3 seeds is not a reliable baseline, and that is a result in itself.

**3. Lift success is 100 % everywhere and carries little information.** The weld latches the
cube whenever the policy commands close within 6 cm, so lifting is nearly free. **Goal-reach is
the discriminating metric** and should be the headline. Do not report lift success alone.

**4. λ → 0 because the constraint was satisfied, not because it failed.** Episodic cost is
9.78–24.26 against a budget of 25. The Lagrangian met its budget and the multiplier correctly
decayed. See limitation 2 below for why the violation *fraction* is nevertheless high.

## Limitations (state these explicitly in the write-up)

**1. The Day-10 single-seed result is retired.** Day 10 reported cPPO 6.65 % vs PPO 16.86 %
singularity violation from one seed each. Three seeds give 42.3 % vs 83.7 % — ~5× higher in both
arms. The env code was verified byte-identical to the frozen tag and the runs' own dumped
`params/*.yaml` confirm every locked setting, so this is **seed variance, not a code change**.
The Day-10 figures should not appear as results.

**2. `cost_limit = 25` is loose, and that explains the 42 % violation rate.**
`costs.py` computes `c_manip = clamp(1 − w/0.045, 0, 1)` — a *margin*, while `viol_singularity`
counts `(w < floor)` as binary. A 25-unit budget over 250 steps permits ~0.1 cost/step, i.e.
`w ≈ 0.0405` — only 10 % under the floor. So the arm can sit just below the floor almost
continuously and still satisfy the constraint. The constraint behaved exactly as specified; the
*specification* is the weak point. The Day-9 calibration no longer describes this system.

**3. The grasp is a weld, not contact.** All numbers above are on the abstraction declared in
Methods §2. They support claims about safe *reaching and manipulation*, not about grasp
mechanics. The real-contact result is the SimpleGripper (62.8 mm pad stall, cube held after pin
release) and is a separate experiment on a separate env — do not merge the two.

**4. Reward is not a fair cross-algorithm axis on its own** — cPPO optimises a different
objective. Reward is reported for completeness; goal-reach success is the comparable metric.

## Open (cheap) experiment, not run

Because λ decayed to ~0, the constraint is *slack* at the end of training. Tightening
`cost_limit` (≈8–10) should bind it and push the violation fraction down — plausibly at no task
cost, since cPPO is already saturated at 100 % goal-reach. Cost: ~1 hour for six runs.
Not run: SAC/TD3 are unstarted and are the entire schedule risk (TD3 hard cut Aug 6).

## Reproduce

```bash
cd ~/Abdur_Rabbi_THESIS/Comparison_test
./run_ppo_cppo_seeds.sh                                  # 6 runs, ~66 min
../IsaacLab/isaaclab.sh -p ur5_grasp/tools/summarize_runs.py
./run_eval_success.sh                                    # 512 episodes x 6
```

Raw data: `logs/batch_report.txt`, `ur5_grasp/tools/summarize_runs_report.txt`,
`ur5_grasp/tools/eval_success_report.txt`, `ur5_grasp/tools/eval_success_results.csv`,
`results/tb_csv/*.csv`.
