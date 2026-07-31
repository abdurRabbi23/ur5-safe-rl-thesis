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

# Layer 1 — evaluation results (frozen policies)

Source: `ur5_grasp/tools/eval_policy_results.csv` — 20 rows read, 2 stale duplicate(s) dropped, 18 used.
Checkpoints: 6   Eval seeds: 101, 102, 103   Episodes per (checkpoint, seed): 1000   num_envs: 128

**Protocol.** Deterministic frozen policies, observation corruption off. Lift success means the cube reaches at least 50% of THAT episode's commanded goal height. Goal-reach is bounded at 1 cm. Safety violations are counted DURING EVALUATION, per step, on the frozen policy — not read off training TensorBoard scalars as the Day-22 table did.

**Frame sanity check:** mean commanded goal height = 0.3741 m (expected ~0.375 from the pos_z range 0.25-0.50). PASS — the lift bar is computed in the right frame.

## Per checkpoint (mean over eval seeds 101/102/103, 1000 episodes each)

| Checkpoint | Lift % | Goal @1cm | @2cm | @5cm | Dist (m) | Sing % | Joint % | min w | Cost |
|---|---|---|---|---|---|---|---|---|---|
| `ppo_s1` | 99.8 | 4.2 | 20.6 | 64.7 | 0.0476 | 63.6 | 53.7 | 0.0075 | 218.0 |
| `ppo_s2` | 9.8 | 0.0 | 0.0 | 0.0 | 0.4419 | 85.8 | 52.3 | 0.0000 | 442.1 |
| `ppo_s3` | 100.0 | 100.0 | 100.0 | 100.0 | 0.0042 | 92.0 | 0.0 | 0.0100 | 123.8 |
| `cppo_s1` | 100.0 | 97.2 | 100.0 | 100.0 | 0.0059 | 59.2 | 0.0 | 0.0396 | 25.1 |
| `cppo_s2` | 100.0 | 99.6 | 100.0 | 100.0 | 0.0043 | 14.3 | 0.0 | 0.0655 | 10.3 |
| `cppo_s3` | 100.0 | 92.8 | 100.0 | 100.0 | 0.0073 | 61.8 | 0.0 | 0.0328 | 17.8 |

## How noisy is the exam? (sd over the 3 eval seeds, per checkpoint)

| Checkpoint | Goal @1cm sd | Sing % sd | Cost sd |
|---|---|---|---|
| `ppo_s1` | 1.05 | 1.39 | 3.16 |
| `ppo_s2` | 0.00 | 0.13 | 3.46 |
| `ppo_s3` | 0.06 | 0.02 | 0.87 |
| `cppo_s1` | 0.85 | 1.15 | 0.11 |
| `cppo_s2` | 0.17 | 0.72 | 0.57 |
| `cppo_s3` | 0.72 | 2.31 | 0.49 |

Largest eval-seed sd on goal-reach: **1.05 percentage points**. Compare that with the training-seed sd in the next table. The exam is essentially noise-free; all the spread that matters comes from the training seed.

## Headline — mean ± sd over the 3 TRAINING seeds

| Metric | CPPO | PPO |
|---|---|---|
| Lift success (>=50% of goal height) | 99.99 % ± 0.02 | 69.89 % ± 52.01 |
| Goal-reach < 1 cm | 96.52 % ± 3.45 | 34.72 % ± 56.54 |
| Goal-reach < 2 cm | 99.99 % ± 0.02 | 40.20 % ± 52.80 |
| Goal-reach < 5 cm | 99.99 % ± 0.02 | 54.89 % ± 50.71 |
| Final cube-goal distance (m) | 0.0058 ± 0.0015 | 0.1645 ± 0.2411 |
| Singularity, % of steps | 45.07 % ± 26.72 | 80.48 % ± 14.92 |
| Joint-limit, % of steps | 0.00 % ± 0.00 | 35.34 % ± 30.62 |
| Collision, % of steps | 0.00 % ± 0.00 | 0.00 % ± 0.00 |
| Manipulability, mean episode min | 0.0459 ± 0.0172 | 0.0058 ± 0.0052 |
| Episodic safety cost | 17.75 ± 7.41 | 261.31 ± 163.49 |

Per-seed values:

- **Lift success (>=50% of goal height)** — cppo 99.97 / 100.00 / 100.00  |  ppo 99.83 / 9.83 / 100.00
- **Goal-reach < 1 cm** — cppo 97.17 / 99.60 / 92.80  |  ppo 4.20 / 0.00 / 99.97
- **Goal-reach < 2 cm** — cppo 99.97 / 100.00 / 100.00  |  ppo 20.60 / 0.00 / 100.00
- **Goal-reach < 5 cm** — cppo 99.97 / 100.00 / 100.00  |  ppo 64.67 / 0.00 / 100.00
- **Final cube-goal distance (m)** — cppo 0.0059 / 0.0043 / 0.0073  |  ppo 0.0476 / 0.4419 / 0.0042
- **Singularity, % of steps** — cppo 59.18 / 14.25 / 61.77  |  ppo 63.61 / 85.85 / 91.97
- **Joint-limit, % of steps** — cppo 0.00 / 0.00 / 0.00  |  ppo 53.69 / 52.34 / 0.00
- **Collision, % of steps** — cppo 0.00 / 0.00 / 0.00  |  ppo 0.00 / 0.00 / 0.00
- **Manipulability, mean episode min** — cppo 0.0396 / 0.0655 / 0.0328  |  ppo 0.0075 / 0.0000 / 0.0100
- **Episodic safety cost** — cppo 25.13 / 10.31 / 17.82  |  ppo 217.98 / 442.10 / 123.85

`cost_limit` = 25 (undiscounted episodic budget). `MANIP_FLOOR` = 0.045.

## Episode-level detail (pooled over all eval seeds)

| Checkpoint | Episodes | Numerically singular (w < 1e-4) | Over cost budget | Median cost | Lifted at some point | Still lifted at the end | Early terminations |
|---|---|---|---|---|---|---|---|
| `ppo_s1` | 3000 | 11.6 % | 82.2 % | 230.32 | 99.9 % | 99.8 % | 0.10 % |
| `ppo_s2` | 3000 | 100.0 % | 100.0 % | 500.42 | 100.0 % | 9.8 % | 0.00 % |
| `ppo_s3` | 3000 | 7.9 % | 100.0 % | 124.34 | 100.0 % | 100.0 % | 0.00 % |
| `cppo_s1` | 3000 | 0.0 % | 42.2 % | 15.90 | 100.0 % | 100.0 % | 0.00 % |
| `cppo_s2` | 3000 | 0.1 % | 12.4 % | 0.00 | 100.0 % | 100.0 % | 0.00 % |
| `cppo_s3` | 3000 | 0.0 % | 28.2 % | 10.41 | 100.0 % | 100.0 % | 0.00 % |

**How to read this.** *Numerically singular* means the arm's manipulability fell to ~0 at some point in the episode — an actual singularity crossing, not merely dipping under the 0.045 floor. *Over cost budget* is the fraction of episodes whose undiscounted safety cost exceeded `cost_limit` = 25; this is the constraint cPPO was trained to respect and PPO was never told about. The gap between *lifted at some point* and *still lifted at the end* isolates a policy that raises the cube and then fails to hold it at the commanded height.
