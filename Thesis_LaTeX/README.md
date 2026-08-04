# Thesis_LaTeX — the thesis book

Built 2026-08-02 (Day 25). This is where the thesis book is typeset.
`Thesis_Documentation/` keeps the Markdown chapter drafts; a chapter stops being
edited there the moment it is ported here.

## Build

```bash
cd Thesis_LaTeX
latexmk -pdf main.tex          # or the LaTeX Workshop build button in VS Code
```

Engine is **pdflatex** with **newtx** (Times New Roman metrics). If newtx is not
installed the preamble falls back to `mathptmx` and warns — same metrics, so the
page layout does not move.

**After editing a chapter, or adding a new one, and wanting `chapter_pdfs/` (per-chapter,
cover, bibliography, submission copy) refreshed:** full step-by-step procedure, including
troubleshooting for two build breakages already hit once, is in `logbook/06_writing.md`,
"Offline rebuild procedure".

## Layout

| Path | What it is |
|---|---|
| `main.tex` | Document skeleton: font-size switch, front-matter order, chapter list, bibliography |
| `thesis-format.sty` | All formatting. **This is the swap point for the official KUET template.** |
| `chapters/` | One `.tex` per chapter. Source of truth once ported. |
| `frontmatter/` | Title page, declaration, approval, board of examiners, acknowledgement, abstract, abbreviations — in KUET's required order |
| `references.bib` | IEEE numeric bibliography |
| `figures/` | Figures for the book (empty — Chapter 4 figures still need regenerating from matrix-v2) |
| `tools/` | One-time porting helpers, `md2tex.sh` + `cleanup.py`. Do not re-run over an edited chapter. |

## Two switches, both in `main.tex`

**Font size.** Line 16:

```latex
\documentclass[12pt,a4paper,oneside]{extbook}
```

12 vs 14 is still unresolved (open since Day 7). Change the number, rebuild,
nothing else moves. `extbook` is used instead of `book` because the standard
classes cannot do 14pt.

**Draft vs final.** Line 22:

```latex
\usepackage[draft]{thesis-format}
```

- `draft` — provenance boxes print in red, `[TODO-A]`/`[TODO-B]` print as loud
  red markers, the provisional reference list and revision notes at the end of
  Chapter 4 are kept in the file but not printed.
- `final` — all of that disappears, and any surviving `\todocite` becomes a
  **hard build error**. The unsourced citations cannot be forgotten.

Verified: `final` currently fails on exactly two placeholders, §4.1 and §4.5.

## Known gaps

- The official KUET `.cls`/`.sty` is not in the repo yet. Everything in
  `thesis-format.sty` and `frontmatter/titlepage.tex` is a stand-in built from
  the rules in `logbook/06_writing.md` and `logbook/08_project_context.md`.
- Chapters 1, 2, 5, 6 are not written; their `\input` lines are commented out in
  `main.tex` and `\setcounter{chapter}{2}` keeps Methodology at 3 and Results
  at 4 in the meantime.
- Tables came through pandoc as `longtable` without captions or labels, so the
  List of Tables is empty and "Table 4.1" is bold text rather than a real float.
  Convert them to captioned floats during typesetting.
- Chapter 4 figures must be regenerated from matrix-v2 before typesetting.
- ~26 overfull hboxes, mostly long file paths inside `\texttt` in draft notes.
  They go away with the draft notes.
