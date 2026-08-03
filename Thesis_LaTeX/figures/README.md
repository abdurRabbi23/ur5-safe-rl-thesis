# Figures — status

## Pending — needs Touhid

**UR5e platform photograph, Chapter 1 §1.1.** `ur5e_platform_interim.png` is currently in place
(extracted from `xia2024proactive` Fig. 1, a real UR5e in a human-robot collaborative workspace,
reused under that paper's CC BY-NC-ND 4.0 licence and credited in the figure caption). This is a
placeholder, not the final figure.

**When you supply your own UR5e photograph:**
1. Save it here as `ur5e_platform.jpg` (or `.png`).
2. In `chapters/01_introduction.tex`, find the `kuetfigure` environment for `fig:i-ur5e-photo`
   (search "ur5e_platform_interim") and swap the `\includegraphics` path to the new file.
3. Rewrite the caption to drop the Xia et al. credit line (the citation stays useful for the
   platform-spec claims elsewhere in that section, just not for the photo itself).
4. Delete `ur5e_platform_interim.png` and remove the corresponding row in
   `logbook/10_references.md`'s claim map.
5. Rebuild (`latexmk -pdf`) and check the figure still fits its slot at a readable size.

Any photo works as long as it clearly shows a UR5e (or UR5e + gripper) — lab photo, phone photo,
doesn't need to be professional.

## In place

- `kuet_monogram.png` — the KUET crest on the title page, supplied by Touhid 2026-08-03.
  1762 × 2000 px, transparent background, drawn at 28 mm height. `frontmatter/titlepage.tex`
  looks for `kuet_monogram.pdf` first and falls back to `.png`, then to an empty `monogram`
  framebox if neither exists, so simply dropping a vector `kuet_monogram.pdf` in here would take
  precedence with no code change. Not used on the cover page, which the KUET spec has as
  text only.
### Chapter 4 — all eleven figures (regenerated 2026-08-04)

**One script produces all of them:** `Comparison_test/results/scripts/make_final_results_figs.py`,
which consumes `final_results_summary.json` written by `build_final_results_data.py`. Both read
`Comparison_test/final_results/` and nothing else. Do not hand-edit any of these; edit the script
and re-run it.

| File | Fig. | Content |
|---|---|---|
| `fig_mean_reward.pdf` | 4.1 | Mean episodic reward, 3 arms |
| `fig_reaching_object.pdf` | 4.2 | Reaching-object reward |
| `fig_lifting_object.pdf` | 4.3 | Lifting-object reward |
| `fig_eval_task_performance.pdf` | 4.4 | Success rates zoomed + failure rate on log axis |
| `fig_eval_safety_violations.pdf` | 4.5 | Four safety outcomes, 2×2, independently scaled |
| `fig_constraints_components.pdf` | 4.6 | Cost split into singularity / joint limit / collision |
| `fig_manipulability.pdf` | 4.7 | Mean episode-minimum manipulability |
| `fig_mean_episode_cost.pdf` | 4.8 | Episodic cost vs budgets, log axis |
| `per_seed_cost.pdf` | 4.9 | Per-seed cost, vertical segment per seed |
| `fig_seed_variance.pdf` | 4.10 | Per-seed cost over training, one panel per arm |
| `lambda_traj.pdf` | 4.11 | Lagrange multiplier, per seed, both constrained arms |

**Superseded scripts, do not use:** `make_ch4_figs.py` (produced the black-line-art `per_seed_cost`
and `lambda_traj`) and `make_per_seed_cost_fig.py` (two arms, reads the flat `results/tb_csv/`
tree). Both are kept only as a record.

Two layout constraints are load-bearing and are documented in the script:

- `per_seed_cost` puts **seeds on the x-axis** with one vertical segment per seed. Section 4.6
  says "each seed contributes one vertical segment joining its three arm values" and argues for
  it over sorted bands. Transposing the figure would contradict the prose.
- `lambda_traj` is **per seed, not the across-seed mean**. Section 4.7 quotes individual peak
  values (15.84 to 48.05 at d=25) and the caption says "all five seeds".

Curve figures are EMA-smoothed (weight 0.88) for legibility, and **every caption says so**. No
number in the chapter comes from a smoothed curve. `fig_mean_episode_cost` additionally clips its
vertical axis below 1; the caption states that too.

## Colour convention (set 2026-08-04, supersedes the earlier "black line art only" rule)

The rule from 2026-08-03 was *"black line art, no colour and no fill; arms distinguished by
marker and line style, never by colour."* **That rule is withdrawn**, on Touhid's instruction of
2026-08-04, and replaced by a fixed palette applied book-wide:

| Arm | Colour | Hex |
|---|---|---|
| `ctrl`, reported as PPO (baseline) | red | `#D11A1A` |
| `cppo`, d = 25 | blue | `#1257A8` |
| `cppo15`, d = 15 | green | `#17803D` |

An arm is the same colour in every figure in the book, including Chapter 2's design diagram
(`lit_arms.pdf`), so the key a reader learns in Chapter 2 carries into every results plot. Text
is near-black `#1A1A1A`, never grey. Body font is Times New Roman, loaded from
`Thesis_LaTeX/fonts/` (see the README there).

**Two consequences worth knowing.** Red and green are the common colour-blind confusion pair, and
they converge to near-identical greys in a black-and-white print. Where more than three series
share a panel (`lambda_traj`, five seeds) line style is used *in addition to* colour, which keeps
those panels readable either way. If the department requires a monochrome submission, the palette
is one dictionary at the top of `make_final_results_figs.py`, and the two Chapter 2 tools carry
the same constants.

  Both are black line art with no colour and no fill; arms are distinguished by marker and line
  style. Do not hand-edit either; regenerate from the script if the data changes.
- `ur5e_platform_interim.png` — Chapter 1, Figure 1.1 (see "Pending" above).

### Chapter 2 figures, reproduced from the source papers (added 2026-08-03)

All four were extracted from the PDFs in `Thesis_LaTeX/source_papers/` with `pdftoppm` at
400 dpi plus a crop (or `pdfimages` where the figure was an embedded raster), not re-drawn.
Every one carries its source in the caption. **Check the reproduction statements with the
supervisor before the `[final]` submission build** — the licence column below is what the
captions currently claim.

| File | Used in | Source | Licence |
|---|---|---|---|
| `lit_stooke_pid_lagrangian.png` | Fig. 2.1, §2.5 | `stooke2020pid` Fig. 1 (p. 2) | ICML 2020 / arXiv author preprint |
| `lit_ferreira_ur5env.png` | Fig. 2.2, §2.7 | `ferreira2025grasping` Fig. 1 (p. 7) | **CC BY 4.0** (MDPI) |
| `lit_shen_manipulability.png` | Fig. 2.3, §2.9 | `shen2022reactive` Fig. 12 (p. 14) | **CC BY 4.0** (MDPI) |
| `lit_henderson_seed_variance.png` | Fig. 2.4, §2.10 | `henderson2018matters` Fig. 5 (p. 5) | AAAI 2018 / arXiv author preprint |
| `lit_twolink_w.pdf` | Fig. 2.3, §2.9 | **Original** — regenerate with `python3 Thesis_LaTeX/tools/make_ch2_manip_fig.py` | Ours |
| `lit_arms.pdf` | Fig. 2.6, §2.11 | **Original** — regenerate with `python3 Thesis_LaTeX/tools/make_ch2_design_fig.py` | Ours |

Both originals are vector, black line art only, no colour and no fill, matching the chapter's
formatting rule. Do not hand-edit either; edit the script and re-run.

- `lit_twolink_w.pdf` plots `w = l1*l2*|sin(theta2)|` for a planar two-link arm, the closed form
  Yoshikawa gives for the simplest multijoint mechanism. It exists to make "a straightened arm
  is a weak arm" visible rather than asserted.
- `lit_arms.pdf` is the experimental-design diagram. **Its arm names and settings must stay in
  step with Chapter 3, Table 3.11** (`ctrl`, `cppo` at d=25, `cppo15` at d=15, plus the plain
  `ppo` arm trained but not reported separately). An earlier version of this figure showed
  PPO / ctrl / cPPO and contradicted that table; if the arms change again, fix the script, not
  the caption.

The two CC BY ones are unambiguously reusable with attribution. The two preprint ones are
reproduced as fair academic quotation with full credit, which is normal practice in a thesis but
is the pair to raise if the department asks. Two figures considered and rejected on licence
grounds: `khan2026` Fig. 6 (Springer, not open access) and `yoshikawa1985` (IJRR/SAGE, not open
access) — the Yoshikawa material is carried as equations instead, which are not copyrightable.
