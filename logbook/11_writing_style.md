# Module 11 — Writing Style and the Humanizer Rule

Status: ▶ ACTIVE — applies to every piece of thesis prose from 2026-08-02 onward
Chat type: writing
Created: 2026-08-02 (Day 25, evening), on Touhid's instruction

## The rule

**Every piece of thesis prose goes through the `humanizer` skill before it is written to a file.**
Invoke `Skill(humanizer)`, run its draft → audit → final loop, then save. It is not optional and
does not depend on whether the text "looks" AI-generated.

Applies to: all chapters, abstract, front matter, figure and table captions, appendices.
Does not apply to: logbook files, `run_log.md`, code comments, commit messages. Those are working
notes, not the book.

## Two calibrations for this thesis specifically

**1. PERSONALITY AND SOUL does not apply.** The skill has a section on injecting voice, opinion
and first person. It explicitly exempts technical and reference writing, and a thesis is exactly
that. Neutral, plain and precise *is* the correct human voice here. Do not add stance or
self-reference to sound less robotic; that would make the writing worse, not more human.

**2. Em dashes are cut; numeric ranges are kept.** The skill's §14 treats `---` as a hard
constraint, and at the density found here it is the single strongest tell in this book. But in
LaTeX `--` is also the correct en dash for numeric ranges. Those stay.

| LaTeX | Meaning | Action |
|---|---|---|
| `---` | prose em dash, used as an aside or break | **Cut.** Replace with a full stop, comma, colon, or parentheses, or restructure |
| `--` between numerals (`483--498`, `8--10`) | numeric range | **Keep.** Correct typography |
| `-` | hyphen | Keep |

Replacement is an editing job, not a substitution job. Do **not** `sed` them. Each one needs the
sentence rebuilt around it, because an em dash usually marks a clause boundary that a comma alone
cannot carry.

**Check before saving any chapter:**

```
grep -c '\-\-\-' Thesis_LaTeX/chapters/NN_*.tex     # must be 0
grep -on '[0-9]\+--[0-9]\+' Thesis_LaTeX/chapters/NN_*.tex   # these should survive
```

## Audit — book-wide, 2026-08-02

The prose was already clean on most axes. A full scan of all six chapters found **zero** hits for
AI vocabulary (crucial, pivotal, underscore, showcase, testament, vibrant, delve, intricate,
fostering, tapestry, interplay), **zero** copula avoidance (serves as, stands as, boasts), and
**zero** curly quotes or emoji. The problem is concentrated in one pattern.

| Chapter | File | Em dashes | Status |
|---|---|---|---|
| 1 Introduction | `01_introduction.tex` | **0** | ✅ **drafted and humanized 2026-08-02 (Day 25, night)** — full 1.1–1.4, not just reserved prose. Verified via `grep -c '\-\-\-'` = 0. |
| 2 Literature Review | `02_literature_review.tex` | **0** | ✅ **rewritten and re-humanized 2026-08-03** (expanded to 12 sections, 22 pp.). Verified 0 em dashes, 0 unicode dashes, 0 negative parallelisms. **The §2.1/Chapter 1 overlap flagged on 2026-08-02 is partly resolved**: the old §2.1 is now §2.2 and a new orientation section sits in front of it, but the shaped-reward-vs-constraint paragraph still restates Chapter 1 §1.2. Still flagged for Touhid. |
| 3 Research Methodology | `03_methodology.tex` | **0** | ✅ **written and humanized 2026-08-03 (Day 26)** — all 8 cleared as part of writing the chapter, not as a sweep. New §3.3 and §3.3.1 went through the draft → audit → final loop before saving; the own-draft audit caught three "-ing" tails, one copula avoidance, two filler phrases and one inherited "Crucially". Verified `grep -c -- '---'` = 0. |
| 4 Results and Discussion | `04_results.tex` | 44 | ◻ backlog — **the big one** (recount 2026-08-02 night; was logged as 45). 5 removed on 2026-08-02 when the table captions became real floats |
| 5 Relation with a Real-World Problem | `05_real_world.tex` | 2 | stub, fix when written |
| 6 Conclusions and Future Works | `06_conclusion.tex` | 2 | stub, fix when written |

Also found and fixed in Chapter 2: one "not merely" (§9 negative parallelism). One "in order to"
remains elsewhere in the book.

## Why Chapter 4 is left for a supervised pass

`04_results.tex` holds 50 of the 81, and it is the chapter an examiner reads hardest. Its prose is
also the most carefully hedged in the book: the withdrawal narrative, the decomposition rule, the
§4.5 counter-result, and the "band entered from both directions" qualification all depend on exact
wording. Rebuilding 50 sentences there without re-reading each in context risks changing a claim by
accident, which is a worse outcome than an em dash. Do it as a deliberate pass with the results
open, not as a cleanup sweep.

## What a fixed em dash looks like

Four worked examples from the Chapter 2 pass, showing that the replacement varies by what the dash
was doing:

| Before | After | Move |
|---|---|---|
| `...has no natural units --- it is a number tuned until...` | `...has no natural units. It is a number tuned until...` | full stop |
| `...is itself changed --- by a risk-sensitive transformation, by...` | `...is itself changed: by a risk-sensitive transformation, by...` | colon |
| `The quantities constrained in this work --- the manipulability measure, ... --- are control-theoretic constructs` | `The quantities constrained in this work (the manipulability measure, ...) are control-theoretic constructs` | parentheses |
| `It trains a three-arm comparison --- an unconstrained baseline, ... --- on ten independent seeds each, and reports...` | `It trains a three-arm comparison on ten independent seeds each: an unconstrained baseline, ... It then reports...` | restructured into two sentences |

The fourth is the important one. A paired em dash wrapping a long list cannot become a comma pair
without the sentence collapsing, so the sentence has to be rebuilt.

## Next steps

- [x] Chapter 2 humanizer pass. *(done 2026-08-02, verified 0 em dashes, builds clean)*
- [x] Chapter 1 written and humanized. *(done 2026-08-02, Day 25 night, verified 0 em dashes,
      builds clean)*
- [ ] Chapter 4 supervised pass, 44 instances. Highest value, highest care required.
- [x] Chapter 3 pass, 8 instances. *(done 2026-08-03 as part of writing the chapter; verified 0)*
- [ ] Chapters 5, 6 when they are written, as part of writing them.
- [ ] Decide what to do about the Chapter 1 / Chapter 2 §2.1 overlap found 2026-08-02 night.
- [ ] Final book-wide check before submission: `grep -rc '\-\-\-' Thesis_LaTeX/chapters/` all zero.

## run_log.md refs

- 2026-08-02 (Day 25, evening) — rule set; Chapter 2 pass completed; book-wide audit recorded.
