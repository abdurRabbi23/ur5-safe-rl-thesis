# TensorBoard CSV exports — Layer 1 benchmark (2026-07-19)

Raw scalar exports from the two full 1500-iter runs, saved so figures can be built
without re-exporting from TensorBoard. Each CSV is `Wall time, Step, Value` (1000 rows,
TB-downsampled from 1500 iters).

Runs: `logs/rsl_rl/ur5e_lift` (PPO) and `logs/rsl_rl/ur5e_lift_cppo` (cPPO, 2026-07-19_12-05-49).

## Files & final values

| File | Scalar | Final value | Note |
|---|---|---|---|
| `cppo/cppo_mean_reward.csv` | Train/mean_reward | 166.3 | climbs 0.73 → 166 |
| `cppo/cppo_viol_singularity.csv` | safety/viol_singularity | 0.0665 | peak 0.517 → 0.0665 |
| `cppo/cppo_cost_lambda.csv` | Loss/cost_lambda | 0.0 | peak 16.7, never railed at 100 |
| `cppo/cppo_mean_episode_cost.csv` | Loss/mean_episode_cost | 2.24 | peak 80.2; budget cost_limit=25 |
| `cppo/cppo_cost_total.csv` | safety/cost_total | 0.0149 | per-step aggregate cost |
| `cppo/cppo_learning_rate.csv` | Loss/learning_rate | — | adaptive LR; not a result metric |
| `ppo/ppo_mean_reward.csv` | Train/mean_reward | 167.2 | — |
| `ppo/ppo_viol_singularity.csv` | safety/viol_singularity | 0.1686 | peak 0.748 |
| `ppo/ppo_cost_total.csv` | safety/cost_total | 0.0201 | — |

## Which figures each supports

- **Reward overlay** (PPO vs cPPO): `ppo_mean_reward` + `cppo_mean_reward`.
- **Singularity-violation overlay + bar**: `ppo_viol_singularity` + `cppo_viol_singularity`.
- **Per-step cost overlay**: `ppo_cost_total` + `cppo_cost_total`.
- **cPPO cost-vs-budget**: `cppo_mean_episode_cost` with a `cost_limit=25` reference line.
- **λ dynamics** (cPPO only): `cppo_cost_lambda`.

PPO has **no** `cost_lambda` or `mean_episode_cost` — those are Lagrangian-only metrics, so
those two figures are cPPO single-curve plots (expected, not missing data).

Reference lines for the write-up: `cost_limit = 25`, `MANIP_FLOOR = 0.045`.
Formatting: centred figures + centred captions, a few purposeful colours only.
