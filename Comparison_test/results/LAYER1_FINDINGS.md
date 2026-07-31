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

# Layer 1 — what the evaluation actually shows

Written 2026-07-31 (Day 23). Companion to `LAYER1_RESULTS_eval.md`, which holds the numbers and
is **regenerated** by `results/scripts/summarize_eval.py --write`. This file is the
interpretation and is hand-written — keep the two separate so a re-run never silently rewrites a
claim.

Data: 6 checkpoints × 3 eval seeds (101/102/103) × 1000 episodes = 18 000 scored episodes,
deterministic frozen policies, observation corruption off, safety counted during evaluation.

---

## 1. The headline

| Metric | cPPO | PPO |
|---|---|---|
| Goal-reach < 1 cm | **96.52 % ± 3.45** | 34.72 % ± 56.54 |
| Lift (≥ 50 % of goal height) | **99.99 % ± 0.02** | 69.89 % ± 52.01 |
| Episodic safety cost (budget 25) | **17.75 ± 7.41** | 261.31 ± 163.49 |
| Joint-limit, % of steps | **0.00 % ± 0.00** | 35.34 % ± 30.62 |
| Episodes reaching an actual singularity | **0.0 – 0.1 %** | 7.9 – 100 % |

cPPO is better on every axis. The registered hypothesis was *safety at no task cost*; the
measurement is **safety at a task gain**. That was already the Day-22 conclusion — what is new is
that it now rests on evaluation of the frozen policy rather than on training curves.

## 2. The strongest number is the episodic cost, not the violation fraction

**PPO spends 261 cost per episode against a budget of 25 — more than ten times over.** cPPO
spends 17.75. Per episode, PPO exceeds the budget in 82–100 % of episodes; cPPO in 12–42 %.

This is the cleanest statement available because it is the *exact quantity the Lagrangian
constrains*. No threshold was chosen for reporting convenience — `cost_limit = 25` was fixed on
Day 9, before any of these runs existed.

Honest caveat: cPPO's *mean* is under budget while individual episodes exceed it, and
`cppo_s1` averages 25.13, marginally above 25. That is correct behaviour, not a violation — the
constraint bounds the expectation over the training distribution, and this is a different (eval)
distribution. Do not present per-episode excursions as constraint failures.

## 3. Use "did the arm actually go singular", not the violation fraction

Three ways of asking the same safety question, and they do **not** separate the algorithms
equally well:

| Measure | PPO | cPPO | separation |
|---|---|---|---|
| % of steps with w < `MANIP_FLOOR` (0.045) | 80.5 % | 45.1 % | 1.8× |
| Mean episode-minimum manipulability | 0.0058 | 0.0459 | 8× |
| % of episodes reaching w < 1e-4 (truly singular) | 7.9 / 11.6 / 100 % | 0.0 / 0.1 / 0.0 % | ~100× |

The step-fraction is a **binary test on a soft margin**, which is exactly the Day-22 "limitation
2" concern — a policy can sit 10 % under the floor forever and register 100 % violation while
never being in any danger. The episode-minimum and the singularity-crossing count do not depend
on where the floor was drawn, and they show cPPO essentially never loses a degree of freedom
while PPO does so routinely. **Lead with the crossing count; report the step fraction with the
caveat attached.**

## 4. PPO's problem is not that it is worse on average — it is that it is three different algorithms

Per-seed goal-reach @1 cm: **4.2 / 0.0 / 100.0 %**. These are not noisy versions of one policy:

- `ppo_s1` — competent but imprecise. 64.7 % within 5 cm, only 4.2 % within 1 cm; mean final
  distance 4.8 cm. It also drives into joint limits 53.7 % of steps and drops the cube off the
  table in ~0.1 % of episodes.
- `ppo_s2` — a distinct failure mode, now identified: **it lifts and then puts the cube back
  down.** 100 % of episodes get the cube above the bar at some point (peak z ≈ 0.39–0.45 m), but
  only 9.8 % are still there at the end; final height settles near 0.136 m against goals of
  0.27–0.50 m. Every single episode reaches an actual singularity, and its cost is 500.
  A plausible reading is that it loses height control because it is operating from singular
  configurations — **plausible, not demonstrated.** Say so.
- `ppo_s3` — the awkward one, and it must be reported. On task it *matches or beats* cPPO
  (100 % @1 cm, mean distance 0.0042 m vs cPPO's 0.0058 m). On safety it is the **worst** run in
  the whole matrix by step-fraction (92.0 %), sits 5× over the cost budget, and goes numerically
  singular in 7.9 % of episodes.

`ppo_s3` is the honest counterweight to the headline: **unconstrained PPO can reach cPPO-level
task performance — but the run that does so is also the one living deepest in near-singular
configurations.** The thesis argument should be "the constraint buys reliability and safety",
not "PPO cannot do the task".

## 5. The exam is not the problem — the training seed is

Largest spread of a single frozen checkpoint across the three eval seeds: **1.05 percentage
points** on goal-reach. Spread across training seeds: **56.5 points**. Roughly a 50× ratio.

This settles the question the Day-22 table could not answer, because it used one eval seed:
`ppo_s2`'s 0 % is a property of the policy, not bad luck in the cube spawns. Separating the two
variance sources is the reason the protocol runs three eval seeds, and it is worth one sentence
in Methods.

---

## Limitations — state these, do not paper over them

1. **Two of the three cost terms are inert.** Collision cost is 0.00 % of steps for every run, and
   joint-limit is 0 % for all of cPPO. The "constrained" method is, in practice, constrained by
   the singularity term alone. This was known from Day 9 and is confirmed here at eval time.
2. **The grasp is a proximity weld**, so lifting is close to free — 5 of 6 checkpoints lift 100 %
   of the time even under the new 50 %-of-goal-height rule. Lift success is a sanity check, not a
   discriminating result. Goal-reach at 1 cm is the discriminating metric.
3. **Goal-reach saturates at 2 cm.** cPPO and `ppo_s3` are all ≥ 99.97 % at 2 cm and 5 cm; only
   the 1 cm bound separates them. If finer resolution between cPPO seeds is wanted later, tighten
   to 5 mm rather than adding runs.
4. **Three training seeds is a small sample.** PPO's standard deviation exceeds its mean on
   goal-reach. No significance test is claimed and none should be — the argument is the
   qualitative one (one seed in three fails outright), not a p-value.
5. **`MANIP_FLOOR = 0.045` is conservative.** cPPO sits under it 45 % of the time while never
   approaching an actual singularity (episode-minimum w ≈ 0.046, crossings ≈ 0 %). The floor is
   doing its job as a *margin*; it should not be read as "cPPO was unsafe 45 % of the time".
6. **Only the rsl_rl runs are scored.** The skrl-PPO bridge and SAC are not in this table yet.
7. **Measurement is one control step (20 ms) before terminal**, because `ManagerBasedRLEnv` resets
   done envs inside `step()`. Documented in `eval_policy.py`.

## Housekeeping issues found while checking this run

- **The summary CSV had two stale rows** (`ppo_s1@103`, `ppo_s2@101`) left by the sweep that
  crashed on the InferenceMode bug. They were bit-identical to the good rows — a free determinism
  confirmation — but averaging them in would have double-weighted two checkpoints.
  `summarize_eval.py` now de-duplicates on `(label, eval_seed)`, last row wins. **Never average
  that CSV with a plain glob.**
- **`eval_policy.py`'s `except` block never fires.** Hydra's `hydra_main` catches the exception
  first, so the traceback goes to Hydra's own error output and not into the flushed report. The
  Day-23 crash was only visible because it was on screen. If a future run fails, the report will
  end mid-sentence rather than containing a traceback — that truncation *is* the signal.
