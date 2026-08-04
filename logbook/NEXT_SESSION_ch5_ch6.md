# NEXT SESSION — Chapters 5 and 6 (and the Abstract)

Written 2026-08-04 (Day 27) after the Chapter 4 figure and review pass. Everything below the
line is a ready-to-paste prompt. Paste the whole fenced block into a new chat with this folder
connected.

**State at handoff:** `[draft]` builds clean, 87 pages, 0 errors, 0 undefined references.
`[final]` also builds clean at 84 pages, so **there are no hard-error blockers left in the book**.
Chapters 1 to 4 are written. Chapters 5 and 6 are stubs holding only a draftnote. The abstract is
a stub. All 23 bibliography entries are cited.

**Warning: another session was editing `chapters/03_methodology.tex` at 13:07 on 2026-08-04,**
while this handoff was being written. Run `git status` and `git diff` before touching anything,
and do not assume Chapter 3's wording is what you last saw.

---

```
Read logbook/00_INDEX.md for background, then CLAUDE.md in full, then this whole block.
Note that 00_INDEX's "Current status" section is STALE (dated Day 19/23) and that
logbook/HANDOFF.md predates the Chapter 3 and Chapter 4 rewrites. THIS file is the current word.

=============================================================================
THE JOB
=============================================================================
Write Chapter 5 (Relation with a Real-World Problem), Chapter 6 (Conclusions and Future
Works), and then the Abstract. In that order. The abstract goes last because it is assembled
from Chapter 1's opening claims and Chapter 6's closing ones.

Success criteria, all three must hold before calling it done:
  1. latexmk exits 0 in BOTH [draft] and [final] mode, with 0 errors and 0 undefined
     references or citations.
  2. grep -c -- '---' returns 0 for chapters/05_real_world.tex, chapters/06_conclusion.tex
     and frontmatter/abstract.tex.
  3. No claim in either chapter contradicts Chapter 4, and no number appears that is not
     already in Chapter 4. Chapters 5 and 6 introduce NO new numbers of their own.

=============================================================================
FIRST, CHECK FOR CONCURRENT WORK. THIS HAS BITTEN THIS PROJECT TWICE.
=============================================================================
Two separate sessions have already collided on this book. On 2026-08-03 a session was asked to
write Chapter 4 that had already been written hours earlier, and caught it only by noticing a
figure filename it did not recognise. On 2026-08-04 a third session was editing Chapter 3 while
a handoff was being written.

Before writing anything:
    git -C <repo> status --short
    git -C <repo> log --oneline -5
    stat -c '%y' Thesis_LaTeX/chapters/*.tex
If 05_real_world.tex or 06_conclusion.tex is longer than its stub, STOP and read it. Someone
else may have started. Do not overwrite.

=============================================================================
WHAT CHAPTER 5 IS, AND WHY IT IS EASY TO GET WRONG
=============================================================================
Chapter 5 is a KUET requirement with no counterpart in a generic ML thesis. The accepted book
(kuet_thesis_style/Thesis_book_draft_3.pdf, its Chapter 5) runs about TWO PAGES, has NO
sub-sections, and moves through four beats in order:
    1. industrial relevance
    2. the engineering contribution
    3. the socio-economic argument
    4. an explicit mapping onto named UN Sustainable Development Goals
The accepted book names SDG 4, 8, 9 and 12. Confirm which of those this thesis can honestly
claim; do not simply copy all four because the exemplar did.

The honest argument available to this thesis, and it is a good one:
  - A manipulator whose safety requirement is a STATED BUDGET rather than a hand-tuned reward
    penalty is easier to certify, easier to audit, and easier to hand to a non-specialist
    operator. The budget d is a number an integrator can put in a specification. A reward
    weight is not.
  - The Chapter 4 variance finding is a RELIABILITY result, and reliability is what an
    industrial deployment actually buys. An integrator does not care about the mean across
    training runs they will never perform; they care what they get from the single policy they
    trained. Section 4.6 makes exactly this argument. Reuse it, do not re-derive it.
  - The joint-limit result (10.70 % of baseline episodes touch a limit, 0.00 % for both
    constrained arms) is the most legible industrial safety claim in the thesis.

HARD CONSTRAINT ON CHAPTER 5: nothing in this thesis ran on hardware. Layer 3 was never
executed. Do not imply a deployed system, a validated safety case, or a certified controller.
The claim is about what the METHOD makes possible, not about what was demonstrated. If a
sentence would embarrass you if an examiner asked "on which robot?", cut it.

Also note the counter-result from Section 4.5, and do not write around it: the worst
single-episode manipulability is identical on all three arms. A hardware safety case built on
this work must rest on expected exposure, not worst-case severity, and must keep whatever
instantaneous protection it would otherwise have needed. brunke2022safe is pre-assigned in the
claim map for exactly this point.

=============================================================================
WHAT CHAPTER 6 IS
=============================================================================
Two sections, per the accepted book: 6.1 Conclusion, 6.2 Future Works.

6.1 Conclusion must answer the objectives set in Chapter 1 Section 1.2, one by one, in the
order Chapter 1 states them. Open chapters/01_introduction.tex at \label{sec:i-objectives} and
work down the itemize list. There is one general objective and six specific ones. Every one of
them was met; say so plainly and point at the section that did it. Do not introduce new
findings here.

The four claims Chapter 4 Section 4.9 establishes are the raw material:
  1. the control arm reproduces the baseline exactly, so the artifact term is zero by
     verification and the comparison can be read directly;
  2. the constraint costs no measurable task performance at either budget;
  3. safety improves, and the largest effect is on VARIANCE not on the mean (a twentyfold
     seed spread collapses to roughly two; the same collapse appears in task precision, which
     was not anticipated);
  4. the multiplier engages sharply near iteration 50 and relaxes to zero, which is documented
     dual-ascent behaviour rather than a quirk.
Quote these, do not recompute them, and introduce no number that is not already in Chapter 4.

6.2 Future Works is where the abandoned and cut work goes, framed as POSITIONED GAPS rather
than as omissions or apologies:
  - Layer 2, image-based visual servoing with an RL-tuned image Jacobian. Design content is in
    logbook/04_layer2_ibvs.md. The policy currently receives privileged object pose; closing
    that loop with an eye-in-hand camera is the natural next step and Chapter 3 already says so.
  - Layer 3, sim-to-real transfer to the physical UR5e over ROS 2 Humble. Design content and
    the known gaps are in logbook/05_layer3_sim2real.md. Note honestly that the real gripper is
    a ROBOTIS RH-P12-RN while the simulation used a lumped-mass abstraction of a Robotiq 2F-85,
    so the gripper is a real transfer gap, not a detail.
  - The cut sac arm: the on-policy versus off-policy question. Cite shahid2022continuous_grasping.
  - PID-Lagrangian as the natural successor to plain dual ascent, since Section 4.7 measured
    exactly the overshoot that Stooke et al. designed it to remove. Cite stooke2020pid. This is
    the strongest single item in the section because the thesis MEASURED the motivating problem.
  - More seeds. Section 4.8 says five is enough to show the lottery exists but not enough to
    put a confidence interval on the effect size.

=============================================================================
CITATIONS — PRE-ASSIGNED, DO NOT INVENT
=============================================================================
logbook/10_references.md is the claim map. Its section headed "Chapter 7 — Conclusion and
Future Work" MEANS THIS CHAPTER 6 (the book was renumbered from seven chapters to six; the
heading was never updated). It pre-assigns:
    stooke2020pid                 PID-Lagrangian as the natural extension
    shahid2022continuous_grasping off-policy comparison; also sim-to-real is demonstrated in
                                  the literature
    brunke2022safe                a hardware safety case rests on expected exposure, not
                                  worst-case severity
RULES: do not cite anything absent from the claim map. Never cite khan2026rl_precision_grasping
as the origin of PPO-Lagrangian; ray2019benchmarking is the origin. Chapter 5 may need no
citations at all, and that is acceptable; the accepted book's Chapter 5 is largely uncited.

Reading honesty: brunke2022safe is in the "metadata and abstract verified" tier, NOT the
"read in full" tier. Use it for framing and positioning only. Do not attribute a specific
number or result to it. See the tier table in 10_references.md.

=============================================================================
WRITING RULES, ALL MANDATORY
=============================================================================
1. HUMANIZER. Every piece of thesis prose goes through the humanizer skill before it is
   written to a file. Invoke Skill(humanizer), run its draft -> audit -> final loop, then save.
   Not optional. Two calibrations for this thesis, both in logbook/11_writing_style.md:
     - The skill's PERSONALITY AND SOUL section does NOT apply. A thesis is technical writing;
       neutral, plain and precise IS the correct human voice. Do not add stance or first person.
     - Em dashes (---) are cut everywhere. Rebuild the sentence around each one; do not sed
       them. Keep -- in numeric ranges (pp. 483--498). Check: grep -c -- '---' must return 0.
2. NO COLOUR AND NO BOXES IN PROSE. Black text, no frames, no background tint. (This restricts
   prose only. Figures ARE in colour since 2026-08-04; see Thesis_LaTeX/figures/README.md.)
3. Formatting is already handled by thesis-format.sty. Do not set fonts or spacing by hand.
   Table captions above, figure captions below, via the kuettable / kuetfigure environments.
4. Chapters 5 and 6 are prose. Neither needs a figure or a table. Do not add one to look
   thorough. If a figure genuinely helps, ask first.
5. Simple words, concise, concrete. Explain with a real example where one exists.

=============================================================================
LENGTH
=============================================================================
Chapter 5: about 2 pages, matching the accepted book. Resist expanding it.
Chapter 6: 3 to 4 pages. 6.1 slightly longer than 6.2.
Abstract: one paragraph, 200 to 300 words, NO citations. Its headline is the Chapter 4 result,
that the constrained agent holds task performance while collapsing seed-to-seed safety variance.

=============================================================================
WHEN DONE
=============================================================================
- Full latexmk build in BOTH modes. To test final:
  change \usepackage[draft]{thesis-format} to [final] in main.tex, build, then CHANGE IT BACK.
- Confirm 0 errors, 0 undefined references, em-dash count 0 in all three new files.
- Delete the draftnote block from each stub as you replace it.
- Add a dated entry to run_log.md and update logbook/06_writing.md's next steps.
- Re-read Chapter 1's objectives against your 6.1 and confirm each one is actually answered.

=============================================================================
STATE OF THE BOOK, 2026-08-04
=============================================================================
[draft] latexmk exit 0, 87 pages, 0 errors, 0 undefined refs. [final] exit 0, 84 pages.
  Ch 1 Introduction        p.  1   done
  Ch 2 Literature Review   p.  8   done, reconciled against Ch 3
  Ch 3 Methodology         p. 27   done (BEING EDITED by another session as of 2026-08-04 13:07)
  Ch 4 Results             p. 49   done, 10 figures, 5 tables, reviewed 2026-08-04
  Ch 5 Real-World Relation p. 68   ** STUB — THIS JOB **
  Ch 6 Conclusion          p. 69   ** STUB — THIS JOB **
  Abstract                         ** STUB — THIS JOB, write last **
All 23 bibliography entries are cited. No hard-error blockers remain.

Known open items NOT part of this job, do not fix silently:
  - Chapter 3 Section 3.8 calls the singularity term "the operative constraint of this thesis",
    contradicting its own Table 3.9 (joint limit ~86 % of realised cost, singularity ~14 %).
    Chapter 2 was hedged on 2026-08-03; Chapter 3 was left alone. Flag it, do not fix it while
    another session is in that file.
  - Chapter 2 Section 2.2 still overlaps Chapter 1 Section 1.2 closely.
  - frontmatter/approval.tex leaves Examiner 2 deliberately blank for hand completion.

DEADLINE: submission 06 August 2026, defence 08 August 2026.
```
