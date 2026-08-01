# Chapter 4 — Results and Discussion (Layer 1: Safe Reinforcement Learning for Grasping)

**Status:** ✏ Draft (2026-08-01, Day 24) · Thesis-book chapter prose · **Layer:** 1 (must-pass)
**Scope:** the corrected cPPO-vs-PPO comparison, matrix v2, partial batch (3 of 5 arms, 10 seeds).
**Companion chapter:** `Methods_Chapter_Layer1.md` (Chapter 3 material — CMDP formulation,
environment, cost function, algorithm, calibration, protocol).

> **Sourcing rule for this draft.** Every numerical value below is taken from
> `Comparison_test/results/MATRIX_V2_PARTIAL_3ARM.md`, which is the source of truth for this
> batch. No number has been introduced from any other file, and no number has been rounded,
> re-derived or estimated except where a ratio is stated as approximate and its inputs are given
> alongside it. The withdrawn Day-19 single-seed results
> (`results/LAYER1_RESULTS_3seed.md`, `LAYER1_FINDINGS.md`, and the draft prose section in
> `06_Results_and_Experiments.md`) are not used anywhere in this chapter.

> **Citation placeholders.** `[TODO-A]`, `[TODO-B]` mark positions where a reference is required
> but no sourced entry yet exists in the project bibliography (`logbook/08_project_context.md`).
> They must be replaced with real IEEE-numbered entries before submission; they are not
> placeholders for text, only for citation numbers. Bracketed numerals `[1]`–`[3]` refer to the
> provisional local list at the end of this chapter and will be renumbered against the thesis-wide
> reference list.

---

## 4.1 Experimental design and provenance

The results reported in this chapter come from a single frozen state of the code base, committed
as `567e4c0` and tagged `matrix-v2`. Freezing the environment, cost function and calibrated
thresholds before the first training run of the comparison, rather than after, is a deliberate
part of the fairness protocol: it makes it impossible for a threshold to be adjusted in response
to a result that has already been seen. All runs use the frozen weld environment
`Isaac-Lift-Cube-UR5e-v0` described in Chapter 3.

Three experimental arms were trained. The `ppo` arm is an unconstrained Proximal Policy
Optimisation baseline. The `cppo` arm is the constrained PPO-Lagrangian agent `[TODO-B]` with an
episodic cost budget of 25. Between them sits `ctrl`, a control arm that is identical to `cppo` in
every respect — it constructs and trains the same additional cost critic, and logs the same cost
quantities — except that its Lagrange multiplier is pinned to zero, so the constraint can exert no
influence on the policy update. The purpose of this third arm is explained in Section 4.2; it is
the instrument that makes the comparison interpretable rather than merely suggestive.

Each arm was trained on ten random seeds (1 through 5, and 50 through 54) for 1500 iterations at
4096 parallel environments using `rsl_rl` 3.0.1, giving thirty trained policies in total. All
thirty final checkpoints were verified present on disk rather than inferred from the absence of
errors in the training logs. Evaluation was then carried out on the frozen, deterministic policy
with observation corruption disabled, over three evaluation seeds (101, 102 and 103, disjoint from
the training seeds) at 1000 episodes each, so that every arm is scored over 30,000 evaluation
episodes and every individual policy over 3000. Reporting evaluation statistics from the frozen
policy rather than from training-time telemetry is itself a correction carried forward from an
earlier iteration of this work, in which safety percentages had been read from the TensorBoard
scalars of a still-exploring policy and therefore could not describe the policy that would
actually be deployed.

The safety thresholds were re-calibrated against a converged 1500-iteration baseline immediately
before the freeze, because three task-defining changes had been made to the environment since the
thresholds were originally set. The manipulability floor was raised from 0.045 to 0.06 in order to
restore the baseline violation rate to the calibration band used in Chapter 3. The joint-limit
margin was retained at 0.175 rad but reclassified: with a wider goal-sampling box the baseline
policy now spends 33.7 % of its time inside that margin, so joint-limit proximity is a second
genuinely active constraint rather than a monitored-but-satisfied one, and it is in fact the
larger of the two. The collision floor of 0.05 m was confirmed still inactive. The cost budget was
held at 25; Section 4.6 shows why that value turns out not to admit a single slack-or-binding
verdict.

**Table 4.1 — Experimental configuration.**

| Item | Value |
|---|---|
| Commit / tag | `567e4c0`, tag `matrix-v2` |
| Task | `Isaac-Lift-Cube-UR5e-v0` (frozen weld environment) |
| Arms trained | `ppo`, `ctrl`, `cppo` |
| Arms not trained in this batch | `cppo10`, `sac` |
| Training seeds | 1, 2, 3, 4, 5, 50, 51, 52, 53, 54 (n = 10 per arm) |
| Training budget | 1500 iterations, 4096 environments, `rsl_rl` 3.0.1 |
| Evaluation seeds | 101, 102, 103 (n = 3, disjoint from training) |
| Evaluation protocol | 1000 episodes per checkpoint × evaluation seed, 128 environments, deterministic policy, observation corruption off |
| `MANIP_FLOOR` | 0.06 (recalibrated from 0.045) |
| `JOINT_LIMIT_MARGIN` | 0.175 rad (unchanged value, reclassified active) |
| `COLLISION_Z_FLOOR` | 0.05 m (unchanged, confirmed inactive) |
| `cost_limit` | 25.0 |

---

## 4.2 Validity check: the control arm reproduces the baseline exactly

An earlier version of this comparison reported a large advantage for the constrained agent that
was subsequently traced, in a line-by-line audit against the upstream library, to an
implementation artifact rather than to the safety constraint. A single global gradient-norm clip
had been applied across all parameters handed to the optimiser; because the constrained agent
carries a third network, the cost critic's gradients entered that norm and scaled down the actor's
step on every update. The constrained arm was therefore not PPO-plus-a-constraint, it was PPO with
a systematically quieter optimiser, and a quieter optimiser is a well-known stabiliser on shaped-reward
manipulation tasks. Because the multiplier had also sat at zero for essentially the whole of those
runs, the constraint could not have been responsible for the gap at all. That result was withdrawn
in full, the clip was partitioned so that the actor and reward critic receive treatment identical
to the baseline, and the `ctrl` arm was added specifically so that the correction could be
verified rather than assumed.

The verification is the strongest that this class of check admits. Across all ten seed pairs,
every training scalar — mean reward and every safety quantity — agrees between `ppo_sN` and
`ctrl_sN` to four decimal places. The agreement extends to chaotic near-zero quantities where any
divergence in trajectory would be expected to show first: the minimum-manipulability tail mean
reads 7.419 × 10⁻⁶ for both `ppo_s3` and `ctrl_s3`. Agreement at that precision is not what
statistical equivalence looks like, and it was therefore treated as a suspected logging fault
rather than as a result until it had been checked at the file level.

Two checks were carried out. First, the possibility that the two arms were reading the same
event file was excluded directly: the files have different MD5 hashes, different sizes (3.13 MB
for `ppo` against 3.59 MB for `ctrl`, the difference being consistent with the control arm's
additional cost-critic logging), and were written by different process IDs. Second, and
decisively, the two final checkpoints were opened and every stored tensor compared by content
hash. All 68 tensors constituting `ppo_s1`'s trained actor and reward critic were found
byte-for-byte inside `ctrl_s1`'s checkpoint, which carries 100 tensors in total, the remainder
being the control arm's own cost critic. Parameter names recovered from the serialised stream
confirm that these are the weight and bias tensors of the four actor and four critic layers. The
two arms did not merely reach statistically indistinguishable policies; at the level of the
stored weights they reached the same policy.

The result was then reproduced independently at evaluation time. Every evaluation metric matches
exactly between `ppo` and `ctrl` on the frozen deterministic policy across all 90 valid
checkpoint-by-evaluation-seed combinations. Because the two arms are exactly equal wherever they
are compared, they are reported jointly as a single `ppo / ctrl` column throughout the remainder
of this chapter.

Interpretation requires one caveat that should be stated rather than glossed. With the clip
partitioned and the multiplier pinned to zero, the control arm's actor loss is algebraically
identical to the baseline's at every step, so identical *updates* are expected. Identical
*weights* additionally require that the random-number stream driving action sampling and
minibatch permutation was not displaced by the cost critic's extra parameter draws at
construction. The audit had assumed the opposite, and treated the resulting offset as unavoidable
seed noise to be absorbed by the control arm. The empirical outcome contradicts that assumption.
The effect is verified beyond reasonable doubt, but the mechanism — plausibly separate generator
streams for host and device — was not traced in the library source, and is recorded here as an
open question rather than asserted as an explanation. Nothing in the chapter depends on the
explanation; the observation alone is what licenses the comparison that follows.

---

## 4.3 How this comparison must be read

The audit that withdrew the earlier result also fixed the form in which the corrected result may
be reported. A direct constrained-versus-baseline number is not permitted as a headline, because
such a number silently sums two effects of different kinds. What is reported instead is the
decomposition

    (cppo − ppo)  =  (ctrl − ppo)  +  (cppo − ctrl)

in which the first term is the cost of merely attaching a cost critic — the implementation
artifact — and the second is the effect of the constraint itself with everything else held fixed.
Only the second term is a safe-RL result. The first term is the quantity that was
mistakenly reported as the second in the withdrawn version of this work.

Section 4.2 establishes that the first term is exactly zero, on every seed and at every point of
comparison. This is what makes the decomposition useful rather than merely cautious: because the
artifact term vanishes identically, the whole of any observed difference between the constrained
agent and the baseline is attributable to the constraint, and the two remaining columns of every
table below can be read directly. Had the first term been non-zero, no constrained-versus-baseline
number could have been reported at all, because the arms would still have differed by something
unnamed.

One further constraint on reading applies to the safety numbers. The pre-registered safe-RL claim
of this project is the comparison between the constrained agent at a budget of 10 — a budget below
the natural operating cost on every previously observed seed — and the control arm. That arm,
`cppo10`, is not part of this batch, and neither is the off-policy `sac` arm. What this batch
measures is the effect of a budget of 25, which Section 4.6 shows to be slack on some seeds and
binding on others. The findings below are therefore reported as findings about a
borderline-to-binding budget, and the question of whether an actively binding budget helps further
remains open. Section 4.7 returns to this.

---

## 4.4 Task performance

Table 4.2 reports training-time performance as a tail mean over the final tenth of training,
averaged across the ten seeds.

**Table 4.2 — Training-time performance (tail mean over final 10 % of iterations, n = 10 seeds).**

| Arm | Mean reward (± std) | `viol_singularity`, soft-margin step fraction (± std) |
|---|---|---|
| `ppo` / `ctrl` (identical) | 133.57 ± 1.58 | 0.318 ± 0.261 |
| `cppo` | 132.65 ± 1.80 | 0.261 ± 0.124 |

The reward decomposition is (cppo − ppo) = 0.000 + (−0.920), so the entire difference of
approximately 0.7 % arises from the constraint and none from the artifact. That difference should
not, however, be presented as a measured task penalty: at 0.920 it is smaller than the
seed-to-seed standard deviation of either arm, and it is therefore better read as an upper bound
on any reward cost the constraint imposes than as evidence that a cost was imposed at all.

The soft-margin violation fraction in the second column is included for completeness and is
deliberately not used as the safety headline. It counts the fraction of control steps on which a
continuous margin falls on the wrong side of a binary threshold, which exaggerates differences
between policies whose margins differ only slightly, and it is measured on a still-exploring
policy. Its own dispersion illustrates the problem: the baseline's standard deviation of 0.261 is
as large as the constrained agent's mean. The metric is nevertheless informative in one respect
that anticipates Section 4.6 — the spread more than halves, from 0.261 to 0.124, while the means
barely separate.

Evaluation-time task performance is reported in Table 4.3. Following the audit's reporting rule,
goal-reach is given as a distance distribution together with success at three thresholds, never as
a single figure. The reason is structural rather than statistical. Under the weld abstraction
described in Chapter 3, the cube's pose is the tool frame's pose once the weld latches, so
"cube within tolerance of the goal" reduces to "tool frame within tolerance of the goal". A
converged policy solves that on nearly every episode and a diverged one fails on nearly every
episode, which drives any single-threshold success rate towards a ceiling and leaves it unable to
rank two policies that have both converged. It was exactly this ceiling that produced the
implausible 100 % against 0 % figures in the withdrawn version of this work.

**Table 4.3 — Evaluation-time task performance (frozen deterministic policy; mean over 10 training
seeds, each the mean of 3 evaluation seeds; 30,000 episodes per arm).**

| Metric | `ppo` / `ctrl` | `cppo` |
|---|---|---|
| Lift success (≥ 50 % of commanded goal height) | 99.86 % | 99.87 % |
| Goal-reach < 1 cm | 94.28 % | 96.49 % |
| Goal-reach < 2 cm | 99.08 % | 99.17 % |
| Goal-reach < 5 cm | 99.81 % | 99.85 % |
| Goal distance, mean / median / p90 (m) | 0.0060 / 0.0047 / 0.0080 | 0.0054 / 0.0042 / 0.0068 |

The two arms are indistinguishable on the task at every threshold and across the whole distance
distribution. The constrained agent is marginally ahead on each row, and its distance distribution
is shifted very slightly towards the goal at the mean, median and ninetieth percentile alike, but
no per-seed dispersion is available for these rates and the margins are small; the direction
should not be leaned on. What the table supports is the negative claim, and it supports it
robustly across five independent measures: constraining the policy did not cost task performance.
This reproduces the original Layer 1 headline of safety at no task cost, but now on ten seeds with
the confounder removed, rather than on one seed with it present.

Both arms produce a small number of catastrophic-miss episodes, with a maximum goal distance
exceeding one metre in each case. These were not investigated and are recorded as an open item;
they are noted here so that a reader encountering them in the per-episode data is not misled into
treating them as an artifact of one arm.

---

## 4.5 Safety

Table 4.4 reports safety on the frozen policy, pooled over the 30,000 evaluation episodes per arm.
Following the audit's reporting rule, the section leads with episodes that reached an actual
kinematic singularity — a manipulability measure `[TODO-A]` below 10⁻⁴, which is a statement about
the arm's genuine loss of a degree of freedom rather than about a calibrated soft margin — and with
the mean episode-minimum manipulability.

**Table 4.4 — Safety on the frozen policy, pooled over 30,000 evaluation episodes per arm.**

| Metric | `ppo` / `ctrl` | `cppo` |
|---|---|---|
| True singularity crossings (w < 10⁻⁴) | 1.343 % (403 / 30,000 episodes) | 0.250 % (75 / 30,000 episodes) |
| Mean episode-minimum manipulability | 0.05471 | 0.06169 |
| Worst single-episode manipulability | 0.000001 | 0.000001 |
| Joint limit touched at all | 5.37 % of episodes | 0.00 % of episodes, all 10 seeds |
| Collision touched at all | 0.13 % of episodes | 0.017 % of episodes |
| Episodic safety cost, mean / p90 / max | 47.68 / 180.63 / 343.01 | 18.41 / 73.26 / 224.07 |

The constraint reduces true singularity crossings by a factor of approximately 5.4, from 403
episodes to 75 out of 30,000. This is a stricter and more meaningful measurement than the
soft-margin fraction of Table 4.2, and the effect survives the change of metric, which the
withdrawn result did not.

The joint-limit row is the cleanest single result in the dataset. Joint-limit contact occurs in
5.37 % of baseline episodes and in none of the constrained agent's 30,000 episodes, on any of the
ten seeds. Two qualifications belong with it. First, this is an observed zero over a finite sample
and not a proof of impossibility; the honest statement is that no joint-limit contact was observed,
with the sample size given so that a reader can bound the claim themselves. Second, the result is
notable precisely because the joint-limit term had been classified as inactive by construction
until the recalibration described in Section 4.1 reclassified it, on the evidence of a 33.7 %
baseline within-margin rate, as the larger of the two active constraints. The constrained agent
eliminated observable contact on a constraint that the original Methods narrative did not treat as
operative, which means the budget is being spent across more than the single manipulability term
that earlier write-ups of this project described. Collision was near zero for both arms before and
remains so; it is reported for completeness and confirms that the collision floor is genuinely
inactive at these settings.

One counter-result must be stated plainly rather than omitted because it is unflattering. The
worst single-episode manipulability is identical for both arms at 0.000001. Whatever the
constraint does, it does not make the rare worst-case excursion shallower. It reduces how often
and how consistently the policy approaches a singularity, and the aggregate consequences of that
are visible in the episodic-cost row, where the constrained agent's worst episode costs 224.07
against the baseline's 343.01 and its ninetieth percentile 73.26 against 180.63 — the worst
*episode* is less costly overall even though the worst *instant* is equally deep. But a claim that
constrained reinforcement learning bounds the depth of the worst singular excursion is not
supported by this data, and is not made. For a safety argument this distinction matters
practically: on hardware, a policy that visits a near-singular configuration one fifth as often but
just as deeply when it does still requires the same instantaneous protection, and buys its margin
in expected exposure rather than in worst-case severity.

---

## 4.6 The principal finding of this batch: collapse of seed-to-seed safety variance

The most substantial effect measured in this batch is not visible in any mean. It appears only
when the ten seeds are examined individually, which Table 4.5 does.

**Table 4.5 — Per-seed natural episodic cost (training, tail mean) and the constrained agent's
final multiplier.**

| Seed | 1 | 2 | 3 | 4 | 5 | 50 | 51 | 52 | 53 | 54 |
|---|---|---|---|---|---|---|---|---|---|---|
| `ctrl` natural cost | 102.1 | 7.7 | 162.3 | 30.0 | 19.1 | 8.6 | 1.8 | 106.9 | 18.8 | 7.9 |
| `cppo` natural cost | 18.0 | 16.6 | 11.9 | 19.7 | 24.1 | 23.9 | 17.0 | 9.5 | 23.5 | 12.0 |
| `cppo` λ (final iteration) | 0 | 0 | 0 | 0 | 0.013 | 0.001 | 0 | 0 | 0.154 | 0 |

The control arm's row is the behaviour of unconstrained policy optimisation with the cost merely
observed and never acted upon, and it is extraordinarily inconsistent. Its natural episodic cost
ranges from 1.8 on seed 51 to 162.3 on seed 3, a spread of roughly ninety-fold, for the identical
algorithm in the identical environment differing only in the random seed. Seeds 51, 2 and 54
produce policies that are accidentally very safe. Seeds 3, 52 and 1 produce policies that are
severely unsafe. Nothing in the training procedure distinguishes them and nothing in the training
telemetry would warn an engineer which one they had obtained.

The constrained agent's row spans 9.5 to 24.1, a spread of roughly two and a half fold, and every
seed is pulled into a band beneath the budget of 25 irrespective of where its unconstrained
counterpart sat. Seed 3, whose control counterpart is the worst in the batch at 162.3, ends at
11.9.

This must not be read as a uniform improvement, and the per-seed data makes the qualification
unavoidable. The band is entered from *both* directions: on six of the ten seeds — 2, 5, 50, 51,
53 and 54 — the constrained agent's episodic cost is **higher** than its control counterpart's,
and on the same six seeds its training-time soft-margin singularity fraction is higher too. Seed
51 is the extreme case, rising from 1.8 to 17.0. The improvement in the mean is carried entirely
by the four seeds whose control counterparts were catastrophic (1, 3, 4 and 52, falling from
102.1, 162.3, 30.0 and 106.9 to 18.0, 11.9, 19.7 and 9.5 respectively). What the constraint
supplies is therefore not a reduction applied to every run, but a *ceiling*: it prevents the
disastrous outcomes without guaranteeing that a fortunate run stays as fortunate as it would have
been. Since which of the two a given training run will produce is not knowable in advance — that
is precisely the lottery described above — trading an unpredictable draw between 1.8 and 162.3 for
a reliable band around 15 is the correct trade for a system intended to run on hardware. But it is
a trade, not a free improvement, and it should be presented as one.

It is worth noting that this pattern is specific to the training-time telemetry. On the frozen
policy over 30,000 evaluation episodes per arm, the constrained agent is ahead on the aggregate
safety measures that matter (Table 4.4), including a 5.4-fold reduction in true singularity
crossings. The per-seed training rows and the pooled evaluation rows are measuring different
things — an exploring policy against a deterministic one, and a soft margin against an actual
crossing — and they are not in conflict, but neither should be quoted as if it were the other.

The effect is confirmed independently on held-out evaluation episodes rather than on training
rollouts. Mean episodic cost falls from 47.68 to 18.41, a reduction of 61 %, but the more important
quantity is the standard deviation across seeds, which falls from 54.04 to 5.36 — approximately a
tenfold tightening, and a larger proportional change than the change in the mean. It is worth
noting that the baseline's standard deviation of 54.04 exceeds its own mean of 47.68, which is the
formal signature of the lottery described above.

The engineering reading is that unconstrained optimisation on this task does not have a safety
level; it has a distribution of safety levels, and which one is drawn is close to arbitrary. The
constrained agent's contribution in this batch is to make the outcome *predictable*, at essentially
no task cost. For a manipulator intended to run on real hardware this is arguably the more useful
property of the two: a mean improvement tells an integrator what to expect on average across
training runs they will never perform, whereas a variance collapse tells them what to expect from
the single policy they actually trained. A safety argument that depends on having drawn a
fortunate seed is not a safety argument.

The multiplier row requires careful reading, and one point of interpretation is corrected here
relative to the batch's own results file. The values shown are λ at the final iteration only, not
a summary of its trajectory. A non-zero final λ, on seeds 5, 50 and 53, indicates that the policy
was still sitting at the budget when training ended and the dual variable had not relaxed. It does
*not* follow that λ remained at zero throughout training on the other seven seeds, and the data
rule that out: by the argument of Section 4.2, a run whose multiplier is identically zero at every
iteration is algebraically the control arm and would converge to the control arm's weights, yet
seed 1 ends at a natural cost of 18.0 against its control counterpart's 102.1. The multiplier must
therefore have engaged substantially on that seed and then relaxed to zero once the cost was
driven under budget — which is the intended behaviour of dual ascent, and the same qualitative
pattern of engagement-and-relaxation observed in the earlier single-seed study of this project.
The full λ trajectories were not extracted for this batch, so this is stated as the reading the
data requires rather than as a directly measured curve, and pulling those trajectories from the
training logs is recorded in Section 4.7 as outstanding work.

Finally, this table settles a question left open by the audit in a way the audit did not
anticipate. The audit had asked whether the budget of 25 was slack or binding, and treated that as
having a single answer. It does not. For roughly a third of the seeds the natural cost exceeds or
approaches the budget, so the constraint binds; for the remainder it is comfortably slack. The
budget was held at 25 rather than retuned, so that the retuning would not be stacked onto an
already large recalibration pass in the same session. The consequence for reporting is the one
already stated in Section 4.3: this batch measures a budget that is borderline-to-binding
depending on the seed, and that is the claim it can support.

---

## 4.7 Limitations

Four limitations bound what this chapter establishes, and they are stated here in full rather than
distributed as caveats.

The first and most important is that this is a partial batch: three of the five pre-registered arms
were trained. The `cppo10` arm, which sets the budget below the natural operating cost on every
observed seed, is absent, and with it the comparison that this project registered in advance as
"the safe-RL claim" — the effect of a constraint that is actively binding on every seed rather
than on some. The `sac` arm is likewise absent, so no off-policy comparison is offered here, and
the algorithm-family question examined in comparable work on manipulation tasks [2] remains open in
this setting. Everything reported above concerns a budget of 25 that binds on part of the seed
population. It would be a misreading of Section 4.6 to conclude that a tighter budget would tighten
the band further; that is a plausible hypothesis and it is untested.

The second concerns the multiplier trajectories discussed in Section 4.6. What was recorded for
this batch is λ at the final iteration; the argument that λ engaged and then relaxed on the
high-cost seeds is a deduction from the converged costs and from the equivalence established in
Section 4.2, not a measurement. Extracting the per-iteration λ curves from the training logs would
convert a sound inference into direct evidence and should be done before this chapter is
finalised.

The third is a pair of data-hygiene faults that were found during analysis, filtered around, and
not repaired at source. Three superseded pre-audit constrained runs from the gradient-clip-bug era
still occupy the same experiment directory as the current runs under identical labels; the results
reported here exclude them by checkpoint-path date, and the evaluation script's checkpoint
selection was verified to resolve to the newer run, but both protections rest on file metadata
rather than on the stale runs having been removed. Separately, the append-only evaluation results
file was found to carry twenty stale rows from a superseded evaluation sweep, which were filtered
by checkpoint path before analysis; the per-episode files were unaffected, since each run
overwrites its own rather than appending. Neither fault affected the numbers reported here — both
were caught and excluded — but both are standing risks to any future automated aggregation, and
they are documented rather than quietly fixed because the discipline of recording near-misses is
part of this project's method. It is worth observing that the entire correction that produced this
chapter began as exactly such a near-miss that was not caught in time.

The fourth is the counter-note of Section 4.5, restated because it is the sharpest limit on the
safety claim itself. The constrained agent's worst single-episode manipulability is identical to
the baseline's. The constraint demonstrably reduces the frequency and the seed-to-seed consistency
of near-singular operation, and it reduces the cost of the worst episode, but it does not reduce
the depth of the worst instant. Any hardware safety case built on this result must rest on
expected exposure rather than on worst-case severity, and must retain whatever instantaneous
protection it would otherwise have required.

---

## 4.8 Summary

Three claims are established by this batch. First, the control arm reproduces the unconstrained
baseline exactly — to identical stored weights, on all ten seeds, and again independently at
evaluation — which confirms the gradient-clipping correction and licenses the constrained-versus-baseline
comparison to be read directly, since the artifact term of the decomposition is exactly zero.
Second, the constraint costs no measurable task performance: reward differs by less than the
seed-to-seed standard deviation, and goal-reach is equal or marginally better at every threshold
and across the whole distance distribution. Third, on safety, the constraint reduces true
singularity crossings by roughly a factor of 5.4 and eliminates all observed joint-limit contact,
but its largest measured effect is on variance rather than on the mean: it collapses a
ninety-fold seed-to-seed spread in natural episodic cost to roughly two and a half fold, and a
tenfold spread in evaluated cost standard deviation, converting an outcome that was close to a
lottery into a predictable one.

The comparison this project registered in advance as its central safe-RL claim — an actively
binding budget against the control arm — is not answered here and is the immediate next
experiment. What is answered, and answered on a ten-seed, checkpoint-verified footing, is that a
previously reported effect of this kind was an implementation artifact, that the artifact has been
removed and its removal verified as strongly as such a thing can be verified, and that the
corrected comparison still shows a substantial and differently-shaped safety benefit. Reporting
that sequence honestly is a more defensible contribution than the original headline it replaces
[1].

---

## Provisional references cited in this chapter

To be merged into the thesis-wide IEEE numbered list; numbering here is local to this draft.

[1] F. Khan *et al.*, "Reinforcement learning for precision grasping and safety-critical
coordination in a robotic arm," *Intelligent Service Robotics*, vol. 19, no. 16, 2026,
doi: 10.1007/s11370-025-00668-0.

[2] A. A. Shahid *et al.*, "Learning continuous control actions for robotic grasping with
reinforcement learning," *Autonomous Robots*, vol. 46, pp. 483–498, 2022,
doi: 10.1007/s10514-022-10034-z. *(Verify exact title against the PDF before submission — the
entry in `08_project_context.md` records the venue and DOI but abbreviates the title.)*

[3] M. M. Khan, "CSRT tracking and classical image-based visual servoing on a 5-DOF manipulator,"
BSc thesis, Dept. of Mechatronics Engineering, KUET, Khulna, Bangladesh, Dec. 2025. *(Not cited in
this chapter; listed because Chapter 4 of the final book may reference it for baseline
positioning.)*

**`[TODO-A]`** — Yoshikawa's manipulability measure. Required at Section 4.5 where w = √det(JJᵀ)
is first used as a safety quantity in this chapter. Not currently in the project bibliography;
must be sourced.

**`[TODO-B]`** — PPO-Lagrangian / constrained policy optimisation. Required at Section 4.1 where
the constrained agent is named. Not currently in the project bibliography; must be sourced. Note
that reference [1] uses the method but is not its origin.

---

## Draft notes for revision (delete before typesetting)

- Formatting when typeset: Times New Roman (size unresolved — 12 per project instructions, 14 per
  a personal note; confirm with the supervisor before locking any chapter), justified, 1.25 line
  spacing, tables and captions centre-aligned. See `logbook/06_writing.md`.
- Figures are not yet regenerated for matrix v2. The four figures in
  `Thesis_Documentation/assets/` were built from the withdrawn Day-19 single-seed data and must
  not be used with this chapter. A per-seed cost plot corresponding to Table 4.5 would be the
  single most valuable new figure, since the variance finding is much clearer graphically than in
  a ten-column table.
- Section 4.2's discussion of the withdrawn result assumes the reader has met the audit in
  Chapter 3. If Chapter 3 does not currently narrate the withdrawal, either add it there or expand
  the first paragraph of 4.2 into a standalone account.
- **One number is outside the source-of-truth file: 33.7 %** (the baseline joint-limit
  within-margin rate, used in §4.1 and §4.2). It is *not* in `MATRIX_V2_PARTIAL_3ARM.md`; it comes
  from the Day-24 `run_log.md` entry and `logbook/09_comparison_test.md`, both of which record it
  as the Step-4 recalibration finding that reclassified the joint-limit constraint as active.
  It is a Methods/calibration figure rather than a result of this batch. Flagged rather than
  silently kept — cut it or promote it into `MATRIX_V2_PARTIAL_3ARM.md` §0, but do not leave it
  sourced only to a logbook.
- Every other numeral in this chapter was checked mechanically against
  `MATRIX_V2_PARTIAL_3ARM.md` and found present there verbatim; each derived ratio recomputes from
  its stated inputs (90×, 2.5×, 5.4×, 10×, −61 %, 0.7 %, 1.343 %, 0.250 %). The only other values
  not literally in that file are the section numbers, the "Day-19" date, and 3000 = 3 × 1000
  episodes per policy.
