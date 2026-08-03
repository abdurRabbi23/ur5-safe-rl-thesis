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

**Updated 2026-08-03 (Day 26).** Twelve PDFs are now held in `Thesis_LaTeX/source_papers/` and
all twelve were read for the Chapter 2 rewrite. The tier table below reflects that. The three
tooling references and the remaining framing entries are unchanged.

| Depth | Entries | What you may claim from them |
|---|---|---|
| **PDF held and read** | `khan2026`, `shahid2022`, `ferreira2025`, `schulman2017`, `achiam2017`, `ray2019`, `stooke2020`, `henderson2018`, `shen2022`, `xia2024`, `yoshikawa1985`, `gu2024` | Anything, including specific numbers, tables, figures and method details. Chapter 2 now quotes numbers from nine of these twelve |
| Metadata + abstract verified | `garcia2015`, `brunke2022`, `elguea2023`, `ji2023`, `altman1999`, `khan2025csrt_ibvs`, `universalrobots2023ur5e`, `makoviychuk2021`, `mittal2023`, `rudin2022` | Existence, framing, taxonomy and positioning claims only. **Do not attribute specific numerical results to these.** |

If an examiner asks whether you read all twenty-two: the answer is that load-bearing claims
come from the twelve papers you hold and read, and the rest are cited for framing and
positioning, which is standard practice. Do not overstate.

### Numbers now quoted in Chapter 2, and where each came from

Every one of these was read off the PDF, not recalled. If a figure is challenged in the viva,
this is the page to check against.

| Number | Source | Where in the paper |
|---|---|---|
| PPO-Lag. violation 0.026 vs CPO 0.593, cost limit d = 25, 3 seeds | `ray2019` | Table 1 and §5.2 hyperparameters |
| PID rule λ = (K_P Δ + K_I I + K_D ∂)₊; K_P = K_D = 0 recovers plain Lagrangian; separate cost critic; 1/(1+λ) rescale | `stooke2020` | Algorithm 2, §5.2, §6.2 |
| t = −9.0916, p = 0.0016 over 2 × 5 seeds; bootstrap CIs (Table 3) | `henderson2018` | Fig. 5 caption, Table 3 |
| SAC 87 % / PPO 82 % grasp, 75 % / 68 % post-grasp; reward Eq. 5 with λ=0.1, r_s=10, r_p=5; ablation ±10/12/8/−8; 100k steps, lr 3e−4, batch 64, MLP 2×256 | `ferreira2025` | Abstract, Eqs. 5--6, Tables 3--4 |
| 100 % grasp success on 4 objects (10/10 each), zero-shot on hardware; 10⁷ steps, 600-step episodes, 250 Hz policy / 500 Hz controller | `shahid2022` | §4.1.2, §5.1, Table 1 |
| 93 % dynamic obstacle avoidance, UR5e, SAC, composite reward | `xia2024` | Abstract |
| r = λ₁r_o + λ₂r_a + λ₃r_m with r_m = √det(JJᵀ); λ₁=1, λ₂=0.2, λ₃=0.05; 77.4 % → 96.8 %; mean manipulability 3.63 → 3.72; 5 seeds | `shen2022` | Eqs. 8--11, Tables 2--3 |
| w = √det(JJᵀ) = σ₁…σ_m = ellipsoid volume; w = \|det J\| when m = n; two-link w = ℓ₁ℓ₂\|sin θ₂\|, best posture θ₂ = ±90°; joint-speed normalisation | `yoshikawa1985` | §2, §3.1 |
| SOPM PPO 17.76 / cPPO 12.32; MOAM PPO 38.80 / cPPO 29.95; MLP 2×64, 8-dim obs, 250 epochs × 2000 steps, cost_lim 25, γ=0.99, λ_GAE=0.97, penalty_lr 5e−2 | `khan2026` | Table 3, §4.2--4.3 |
| 2H3W framing (five open problems) | `gu2024` | §1, Fig. 1 |

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
| UR5e hardware specifications (payload, reach, DOF, repeatability, joint speed) | `universalrobots2023ur5e` | **Added 2026-08-03.** New §1.1 (platform section). The 3.14 rad/s joint-speed ceiling used in training is licensed by this source's max-joint-speed figure (180 deg/s = pi rad/s), not asserted from memory |
| Interim photograph of a UR5e in a human-robot collaborative workspace | `xia2024proactive` Fig. 1 | Figure `figures/ur5e_platform_interim.png`, reused under the paper's CC BY-NC-ND 4.0 licence, credited in the caption. **Placeholder — swap for Touhid's own UR5e photograph when supplied**, see `Thesis_LaTeX/figures/README.md` |

### Chapter 2 — Motivation and Background Study

> **DRAFTED 2026-08-02, EXPANDED 2026-08-03** — the real file is
> `Thesis_LaTeX/chapters/02_literature_review.tex` (NOT `02_background.tex`; that name was wrong
> in this file and in `06_writing.md`). Now **twelve sections, pp. 20–41 of the `[draft]` build**,
> written against the twelve PDFs in `Thesis_LaTeX/source_papers/`. Four reproduced figures, eight
> tables, ten display equations. **§2.11 promises predictability, not uniform improvement — do
> not upgrade that wording**, §4.6 shows the cost band is entered from both directions.
>
> Sections as built: 2.1 how to read this chapter (roadmap + key-findings box) · 2.2 the safety
> requirement · 2.3 safe RL and the García/Gu taxonomy · 2.4 the CMDP · 2.5 deep constrained
> policy optimisation (PPO, CPO, PPO-Lagrangian, PID) · 2.6 safety in robot learning · 2.7 deep
> RL on manipulators · **2.8 experimental methods of the reviewed studies (new comparative
> table)** · 2.9 manipulability and singularity · 2.10 reproducibility and seed variance ·
> 2.11 research gap and positioning (two boxed gaps + positioning table) · 2.12 summary.

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
| Five seeds, and dispersion reported rather than means alone | `henderson2018matters` | **Justifies the protocol.** **Corrected 2026-08-03:** this row previously said "Ten seeds… cite where n = 10 is set". That was stale — the locked scope is **5 seeds (1, 3, 4, 52, 54)**, see CLAUDE.md "Results scope". Cited in Ch. 3 §3.7.1 (`sec:m-arms`) where n = 5 is set |
| Reward design and sim-to-real practice for contact-rich manipulation is established | `elguea2023review` | Use to present the reward/cost design as conventional rather than ad hoc |
| The weld abstraction differs from full physical grasping | `ferreira2025grasping` | Their 87 %/82 % is a *full grasp*; ours is a weld. **State the difference so our 99.86 % is not read as comparable** |
| UR5e specifications, restated as a methodology table (payload, reach, DOF, repeatability, mass, joint speed, safety certification) | `universalrobots2023ur5e` | **Row added 2026-08-03** for the new Ch. 3 §3.1.4 preliminaries. Same source and same figures already licensed for Ch. 1 §1.1; this row just extends it to Ch. 3, where each spec is tied to the modelling decision it constrains. Numbers must match Ch. 1 exactly, do not re-derive |
| On-policy and off-policy methods are both established on robotic grasping, so choosing on-policy is a positioned choice rather than the only option | `shahid2022continuous_grasping` | **Row added 2026-08-03** for Ch. 3 §3.1.2. Already licensed as the PPO-vs-SAC template in Ch. 2 and as the off-policy complement in Ch. 7. Cite for the existence of both families, **not** for any numerical claim about SAC in this thesis |
| A cost budget constrains an expectation, not a worst case, and a hardware safety case has to be read that way | `brunke2022safe` | **Row added 2026-08-03** for Ch. 3 §3.2. Same claim already licensed in Ch. 7 against the §4.5 counter-result; stating it at the formulation is where it belongs, since it is a property of Eq. (3.1) itself |
| The model-free/model-based taxonomy of RL algorithms, the policy-optimisation vs Q-learning split within model-free, and which named algorithms sit where | `achiam2018spinningup` | **NEW SOURCE, entry 23, added 2026-08-03.** Verified directly from the publisher page (© 2018 OpenAI; author Joshua Achiam, same author as `achiam2017cpo`). Licenses Fig. 3.1, which is **redrawn in TikZ from the taxonomy content, not a reproduction of OpenAI's SVG** — the caption says so. Also licenses the standard on-policy/off-policy framing in §3.2. **Educational resource: use for taxonomy and framing only, never for a numerical claim or as the origin of any algorithm.** PPO's origin stays `schulman2017ppo` |

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
- [x] Cite the three remaining tooling entries (`makoviychuk2021isaacgym`, `mittal2023orbit`,
      `rudin2022walk`). *(done 2026-08-03 in Chapter 3: `mittal2023orbit` and
      `makoviychuk2021isaacgym` at §3.2, `rudin2022walk` at §3.2, §3.3 and again at the
      gradient-clip audit §3.3.1. Note the chapters were NOT split — the book is six chapters and
      Chapter 3 holds the whole methodology.)*
- [ ] Re-run the `[final]` build once the Board of Examiners names land — verified 2026-08-02
      that `[final]` compiles clean (34 pages, 0 errors, 0 undefined citations) once the six
      `\todo{}` markers in `frontmatter/approval.tex` are filled. Those six are the **only**
      remaining hard-error blockers.

## run_log.md refs

- 2026-08-02 (Day 25, evening) — 21-entry bibliography verified and merged; TODO-A/TODO-B
  resolved; `\nocite{*}` removed; `[final]` build confirmed clean apart from the examiner names.
