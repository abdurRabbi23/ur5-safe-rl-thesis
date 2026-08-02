# NEXT SESSION — Chapter 2 (Motivation and Background Study)

Paste the fenced block below into the new Cowork session after connecting this folder.
Written 2026-08-02 (Day 25, late evening).

```
Read logbook/00_INDEX.md for background, then logbook/HANDOFF.md, then THIS file's context
below. Note that 00_INDEX's "Current status" section is STALE (Day 19/23) — HANDOFF.md is real.

=============================================================================
WHERE CHAPTER 2 STANDS
=============================================================================
A FULL FIRST DRAFT EXISTS: Thesis_LaTeX/chapters/02_background.tex, written 2026-08-02.
Do NOT rewrite it from scratch. It builds clean and is the source of truth.

Verified at time of writing: latexmk -pdf exits 0, 47 pages total, 0 LaTeX errors,
0 undefined citations, 0 undefined references, 18 bibitems. Chapter 2 occupies pp. 14–22
of the draft build (9 pp including the draft-note box, which does not print in [final]).
Target was 8–10 pp, so length is on spec.

Ten sections:
  2.1 The safety requirement in learned manipulation   <- the shaped-reward-vs-constraint premise
  2.2 Safe reinforcement learning                      <- Garcia taxonomy + Table 2.1, Gu 2024
  2.3 The constrained Markov decision process          <- Altman, Lagrangian relaxation
  2.4 Constrained policy optimisation in deep RL       <- PPO, CPO, PPO-Lagrangian, PID, benchmarks
  2.5 Safety in robot learning                         <- Brunke (control vs ML vocab), Elguea
  2.6 Deep RL for robotic manipulation                 <- Shahid, Ferreira (UR5), Xia (UR5e)
  2.7 Manipulability and singularity avoidance         <- Yoshikawa; Shen as the reward-based contrast
  2.8 Reproducibility and seed variance                <- Henderson; justifies n=10
  2.9 Research gap and positioning                     <- LOAD-BEARING. Khan 2026 + the two gaps
  2.10 Summary

=============================================================================
RULES THAT GOVERN THIS CHAPTER — do not violate
=============================================================================
1. READ logbook/10_references.md FIRST. It is the claim map: which source licenses which
   claim, and which chapter carries it. Rule: do not cite anything that is not in the claim
   map. If a new claim needs a source, add the row to the map first, then write the sentence.

2. CLAIM DISCIPLINE. Reading status is recorded in 10_references.md. Papers held in full:
   khan2026, shahid2022, ferreira2025. Foundations known well: schulman, achiam, ray, stooke,
   altman. Everything else is metadata + abstract only — cite those for framing, taxonomy and
   positioning ONLY. Do NOT attribute specific numerical results to a paper not held.
   The only numbers currently quoted from a third party are Ferreira's 87%/82% grasp success,
   and that paper IS held.

3. NEVER cite khan2026 as the origin of PPO-Lagrangian. It uses the method. ray2019 is the
   origin. This is written into the bib annote and into the claim map.

4. references.bib annotations live in `annote`, not `note`. BibTeX typesets `note` and the
   annotations contain maths characters — renaming them back BREAKS THE BUILD. Already caught
   once.

5. Reference list currently shows 18 of 21 entries. The three uncited ones are the tooling
   references (makoviychuk isaacgym, mittal orbit, rudin rsl_rl) which belong in Chapters 3–4.
   A short list is correct, not a fault.

=============================================================================
WHAT TO DO IN THIS SESSION — in order
=============================================================================
A. Read 02_background.tex end to end and revise for voice and accuracy. It was drafted fast.
   Specific things flagged in its own draftnote:
   - Decide whether 2.8 (seed variance) belongs in Chapter 2 or moves to Chapter 3. It is
     placed in 2 because it motivates the ten-seed protocol, but it is arguably method.
   - Check length against the built PDF once the KUET .cls lands (formatting may reflow).

B. Check 2.9 against Chapter 6's actual findings. 2.9 promises the reader two things: the
   decomposition into implementation vs constraint terms, and dispersion across seeds.
   Chapter 6 delivers both — but 6.6 also carries a NUANCE that 2.9 must not contradict:
   the constrained agent's cost band is entered from BOTH directions (on six of ten seeds its
   episodic cost is HIGHER than the control arm's; the mean improvement is carried by the four
   catastrophic seeds). 2.9 as drafted is careful to promise "predictability" rather than
   "improvement" — KEEP IT THAT WAY. Do not upgrade it to a uniform-improvement claim.

C. Then write Chapter 1 (Introduction). Template mandates 1.1 General, 1.2 Scope of present
   Investigation, 1.3 Project report layout. The claim map has a dedicated Chapter 1 table.
   1.2 must state the scope restriction plainly — the thesis was filed promising IBVS and
   hardware transfer and delivers neither. 1.1 should reuse the 2.1 premise (shaped reward vs
   constraint) without repeating it verbatim.

D. Update run_log.md with a dated entry and refresh logbook/06_writing.md when either lands.

=============================================================================
DEADLINE — this dominates every decision
=============================================================================
SUBMISSION 06 AUGUST. DEFENCE 08 AUGUST. Written: Ch 2, 3, 6. Stubs: Ch 1, 4, 5, 7.

Critical path:
  03 Aug  revise Ch 2, write Ch 1
  04 Aug  split Ch 3 -> 3/4/5 (env+calibration+protocol to 4, software to 5); per-seed cost
          figure; convert pandoc longtables to captioned floats so List of Tables populates
  05 Aug  Ch 7, Ch 5 SDG section, front matter, full build, proofread
  06 Aug  submit

BLOCKERS ONLY TOUHID CAN CLEAR — chase before writing anything else:
  - Board of Examiners members 2 and 3 (name/designation/department) for
    frontmatter/approval.tex. Six \todo{} markers. THE ONLY remaining hard-error blocker on
    the [final] build — verified 2026-08-02 that [final] compiles clean once they are filled.
  - Font size 12 vs 14, open since Day 7. One line in main.tex. If it lands on the 5th you
    are reflowing a finished book.
  - Official KUET .cls/.sty still not in the repo; thesis-format.sty is a stand-in.
```
