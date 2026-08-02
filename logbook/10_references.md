# Module 10 — References and the Claim Map

Status: ▶ ACTIVE — this is the file to read before writing Chapters 1, 2, 5 or 7
Chat type: writing / literature
Created: 2026-08-02 (Day 25, evening)

## What this file is for

`references.bib` says *what* the sources are. This file says *what each one licenses you to
claim, and where*. Without it, a new chat writes generic literature-review filler
("Achiam et al. proposed constrained policy optimisation") instead of argument
("expressing a safety requirement through reward shaping requires the designer to guess a
trade-off weight; expressing it as a constraint requires only that they state a budget").

**Rule: do not cite anything in this thesis that does not appear in the claim map below.**
If a new claim needs a source, add a row here first, then write the sentence.

## Status — 2026-08-02

- `Thesis_LaTeX/references.bib` holds **21 verified entries**. Every DOI, venue, volume and
  page range was checked against the publisher record, not reconstructed from memory.
- **`[TODO-A]` and `[TODO-B]` are RESOLVED and removed from the prose.** The `[final]` build
  no longer fails on them.
- `\nocite{*}` is deleted from `main.tex`. The reference list is now driven by real `\cite`
  calls, so it currently shows **5 entries** — the five cited in Chapter 6. It will grow as
  Chapters 1, 2, 4, 5 and 7 are written. **A short reference list is correct behaviour right
  now, not a fault.**
- Full annotations, journal quartiles, impact factors and open-access status: the annotated
  bibliography document delivered with this batch. `references.bib` carries a condensed
  version of each in an `annote` field (BibTeX styles ignore `annote`, so it never typesets —
  do **not** rename these back to `note`, that breaks the build on the maths characters).

## Reading status — be honest about this in the viva

| Depth | Entries | What you may claim from them |
|---|---|---|
| Read in full (PDF in the project) | `khan2026`, `shahid2022`, `ferreira2025` | Anything, including specific numbers and method details |
| Foundations, known well | `schulman2017`, `achiam2017`, `ray2019`, `stooke2020`, `altman1999` | Substantive technical claims about the algorithms — Touhid confirmed 2026-08-02 he knows this material |
| Metadata + abstract verified | the remaining 13 | Existence, framing, taxonomy and positioning claims only. **Do not attribute specific numerical results to these.** |

If an examiner asks whether you read all twenty-one: the answer is that load-bearing claims
come from papers you read, and the rest are cited for framing and positioning, which is
standard practice. Do not overstate.

---

## THE CLAIM MAP

Each row: the claim you are licensed to make → the entry that licenses it → where it goes.

### Chapter 1 — Introduction

| Claim | Cite | Notes |
|---|---|---|
| Safety on collaborative manipulators is an active industrial concern, not an academic exercise | `xia2024proactive` | UR5e platform match — same robot as ours |
| A reward function is an awkward vehicle for a safety requirement on a physically-interacting system | `achiam2017cpo` | This is the paper's own motivating argument; use it to open the problem statement |
| **The framing contrast: shaped reward vs constraint** — a shaped reward makes the designer guess a trade-off weight; a constraint lets them state a budget | `shen2022reactive` (reward) vs `achiam2017cpo`, `altman1999cmdp` (constraint) | **Strongest single framing available to this thesis.** Shen puts manipulability in the reward; we put it in a constraint. Build the problem statement on this |
| Unconstrained RL outcomes vary dramatically with random seed alone | `henderson2018matters` | Motivates why predictability, not just mean safety, is the useful property |
| The research gap: prior cPPO-vs-PPO work on manipulators reports no control arm isolating the cost-critic implementation effect, and no seed-to-seed dispersion | `khan2026rl_precision_grasping` | **The gap statement.** Both are gaps this thesis fills. Phrase as a gap in the literature, not as a criticism of the authors |
| Predecessor work in the same lab used classical IBVS; this thesis is the RL/safety upgrade | `khan2025csrt_ibvs` | Positioning, already decided |

### Chapter 2 — Motivation and Background Study

> **DRAFTED 2026-08-02** — `Thesis_LaTeX/chapters/02_background.tex`, ten sections, pp. 14–22.
> The spine below is what was built. Continue in a separate session via
> `logbook/NEXT_SESSION_ch2.md`. **§2.9 promises predictability, not uniform improvement — do
> not upgrade that wording**, §6.6 shows the cost band is entered from both directions.

**Spine as built (chronological, ~8–10 pages):**

1. **Safe RL as a field** — `garcia2015survey` defines the two-branch taxonomy (modify the
   optimisation criterion vs modify the exploration process). State plainly that this thesis
   is in the first branch. → `gu2024review` for the modern state of the art, and for the claim
   that the constrained-criterion (CMDP) approach is now the prevailing formalism.
2. **The CMDP formalism** — `altman1999cmdp` for the tuple and the duality result behind the
   Lagrangian relaxation.
3. **Deep constrained policy optimisation** — `achiam2017cpo` founds the family;
   `ray2019benchmarking` specifies PPO-Lagrangian and, critically, **reports CPO
   underperforming Lagrangian methods on Safety Gym — this is your published justification
   for choosing PPO-Lagrangian over CPO, so state it explicitly**; `stooke2020pid` on
   multiplier dynamics; `ji2023safetygymnasium` as the current benchmark standard.
4. **Safety in robot learning specifically** — `brunke2022safe` reconciles control-theoretic
   and learning-theoretic safety vocabularies. Needed because our safety quantities
   (manipulability, joint-limit margin, collision distance) are control constructs enforced by
   a learning mechanism. `elguea2023review` for what is standard in contact-rich manipulation.
5. **RL on manipulators, narrowing to the UR5** — `shahid2022continuous_grasping` (PPO vs SAC
   template, sim-to-real at 100 %), `ferreira2025grasping` (UR5 + Robotiq, PPO 82 % / SAC 87 %),
   `xia2024proactive` (UR5e safety).
6. **Singularity and manipulability** — `yoshikawa1985manipulability` for the measure itself,
   `shen2022reactive` as the reward-based contrast.
7. **The gap** — `khan2026rl_precision_grasping`. Close the chapter on this; it hands straight
   to Chapter 1's problem statement and to the methodology.

### Chapters 3–5 — Methodology, Simulation Set-up, Implementation

| Claim | Cite | Notes |
|---|---|---|
| The problem is a CMDP: maximise return subject to E[Σ c_t] ≤ d | `altman1999cmdp` | First sentence of the formulation |
| The baseline arm is PPO — clipped surrogate, GAE, multi-epoch minibatch update | `schulman2017ppo` | |
| The constrained arm is PPO-Lagrangian | `ray2019benchmarking` + `achiam2017cpo` | **Resolved TODO-B.** `khan2026` uses the method but is NOT its origin — never cite it as such |
| Manipulability w = √det(JJᵀ) | `yoshikawa1985manipulability` | **Resolved TODO-A. MANDATORY at the cost-function definition** — that is the book's *first* use of w, earlier than the Results chapter. Currently cited in Ch. 6 only; **Ch. 3 still needs it** |
| Simulation platform, and why 4096 parallel environments is reasonable | `makoviychuk2021isaacgym` | Reports 2–3 orders of magnitude speed-up from GPU-resident physics + training |
| The environment framework (`Isaac-Lift-Cube-UR5e-v0` is an Isaac Lab task) | `mittal2023orbit` | Isaac Lab has no paper; Orbit is its predecessor and the citable reference |
| The training library, `rsl_rl` 3.0.1 | `rudin2022walk` | Also cite at §4.2 where the audit against upstream is described |
| Ten seeds, and dispersion reported rather than means alone | `henderson2018matters` | **Justifies the protocol.** Cite where n = 10 is set |
| Reward design and sim-to-real practice for contact-rich manipulation is established | `elguea2023review` | Use to present the reward/cost design as conventional rather than ad hoc |
| The weld abstraction differs from full physical grasping | `ferreira2025grasping` | Their 87 %/82 % is a *full grasp*; ours is a weld. **State the difference so our 99.86 % is not read as comparable** |

### Chapter 6 — Results and Discussion  *(already written and cited)*

| Claim | Cite | Status |
|---|---|---|
| Manipulability measure as a safety quantity | `yoshikawa1985manipulability` | ✅ in place, §4.5 |
| The cppo arm is PPO-Lagrangian | `ray2019benchmarking`, `achiam2017cpo` | ✅ in place, §4.1 |
| Algorithm-family question (on- vs off-policy) remains open | `shahid2022continuous_grasping` | ✅ in place, §4.7 |
| Reporting the correction is more defensible than the headline it replaces | `khan2026rl_precision_grasping` | ✅ in place, §4.8 |
| **λ engaged then relaxed on the high-cost seeds** | `stooke2020pid` | ⚠ **NOT YET CITED — add it.** Dual ascent oscillating and overshooting is exactly this behaviour. It converts the §4.6 inference from a deduction into documented expected optimiser behaviour. Highest-value remaining citation in the chapter |
| The ninety-fold seed spread is a known failure mode, not an anomaly | `henderson2018matters` | ⚠ **NOT YET CITED — add at the head of §4.6.** Makes the variance finding land as measurement rather than surprise |

### Chapter 7 — Conclusion and Future Work

| Claim | Cite | Notes |
|---|---|---|
| PID-Lagrangian is the natural extension for smoother multiplier behaviour | `stooke2020pid` | |
| An off-policy (SAC) comparison is the recognised complement — grounds the cut `sac` arm | `shahid2022continuous_grasping` | Makes Limitation #1 a positioned gap rather than an omission |
| Sim-to-real transfer of learned grasping policies is demonstrated in the literature | `shahid2022continuous_grasping` | Supports the Layer-3 future work without over-claiming |
| A hardware safety case must rest on expected exposure, not worst-case severity | `brunke2022safe` | Pairs with the §4.5 counter-result (worst single-episode manipulability is identical across arms) |

---

## Things that will cost marks if forgotten

1. **`yoshikawa1985manipulability` must be cited in Chapter 3**, not only Chapter 6. The cost
   function is the book's first use of w.
2. **Add `stooke2020pid` and `henderson2018matters` to Chapter 6** — see the ⚠ rows above.
   Both are already in `references.bib`; this is two `\cite` calls.
3. **Never cite `khan2026rl_precision_grasping` as the origin of PPO-Lagrangian.** It uses the
   method. `ray2019benchmarking` is the origin.
4. **`shahid2022continuous_grasping` title was wrong** in `08_project_context.md` (abbreviated
   form). The verified title is in `references.bib` and the old one is superseded.
5. Do not rename `annote` back to `note` in `references.bib` — the annotations contain maths
   characters and BibTeX will typeset `note`, breaking the build.

## Next steps

- [x] Add the two missing Chapter 6 citations (`stooke2020pid`, `henderson2018matters`). *(done)*
- [x] Cite `yoshikawa1985manipulability` in Chapter 3 at the cost-function definition. *(done)*
- [x] Write Chapter 2 against the spine above. *(drafted 2026-08-02 — 10 sections, pp. 14–22,
      18 of 21 entries now cited. Continue via `logbook/NEXT_SESSION_ch2.md`.)*
- [ ] Write Chapter 1 against the Chapter 1 rows above.
- [ ] Cite the three remaining tooling entries (`makoviychuk2021isaacgym`, `mittal2023orbit`,
      `rudin2022walk`) when Chapters 3–4 are split and written. They are the only uncited
      entries left.
- [ ] Re-run the `[final]` build once the Board of Examiners names land — verified 2026-08-02
      that `[final]` compiles clean (34 pages, 0 errors, 0 undefined citations) once the six
      `\todo{}` markers in `frontmatter/approval.tex` are filled. Those six are the **only**
      remaining hard-error blockers.

## run_log.md refs

- 2026-08-02 (Day 25, evening) — 21-entry bibliography verified and merged; TODO-A/TODO-B
  resolved; `\nocite{*}` removed; `[final]` build confirmed clean apart from the examiner names.
