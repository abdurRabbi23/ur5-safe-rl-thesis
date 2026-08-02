# KUET MTE thesis format — measured spec

Extracted 2026-08-02 from `kuet_thesis_style/*.docx` (the official department templates).
Values marked **[measured]** come from the Word XML — page setup, style definitions — and are
exact. Values marked **[stated]** are the template's own written instructions. Where the two
disagree it is recorded as a conflict, not silently resolved.

This file is the authority for `thesis-format.sty`. If the two ever disagree, this file is right.

---

## 1. Page setup **[measured]**

| Property | Value |
|---|---|
| Paper | A4 (11907 × 16839 twips = 210 × 297 mm) |
| Top margin | 1699 twips = **30 mm** |
| Left margin | 1699 twips = **30 mm** (binding edge) |
| Right margin | 1440 twips = **25 mm** |
| Bottom margin | 1440 twips = **25 mm** |
| Gutter | 0 |
| Columns | 1 |
| Running header | **none** — no `header*.xml` exists in the body template |

The "25 mm / 30 mm" callouts drawn on the cover and title page templates agree with this:
30 mm top and left, 25 mm right and bottom.

## 2. Page numbering **[measured]**

| Section | Format | Position | Notes |
|---|---|---|---|
| Cover page | none | — | not counted |
| Title page | i | not printed | |
| Declaration → Approval | ii, iii | **centred** footer | `pgNumType start=2 fmt=lowerRoman` |
| Acknowledgement → Abbreviations | iv onward | **centred** footer | `pgNumType start=4` |
| Chapter 1 onward | 1, 2, 3 … | **right-aligned** footer | arabic restart |

The footer alignment genuinely changes between front matter (centre) and body (right). Both
were read out of the respective `footer*.xml`.

## 3. Type **[measured from styles.xml]**

Everything is Times New Roman. Sizes below are the real ones (Word stores half-points).

| Element | Style name in template | Size | Weight | Alignment | Spacing |
|---|---|---|---|---|---|
| Body text | `Normal` | **12 pt** | regular | **justified** | line 1.5, space-after 0 |
| Chapter heading | `Heading 1` / `Chapter_Heading_MTE_Thesis` | **14 pt** | **bold** | centred | keep-with-next |
| Section (x.y) | `Heading 2` / `MTE_Thesis_section` | **12 pt** | **bold** | left | 6 pt before, 6 pt after |
| Sub-section (x.y.z) | `Heading 3` / `Subsection_MTE_Thesis` | **12 pt** | *italic* | left | 6 pt before, 6 pt after |
| Caption (fig + table) | `Caption` / `Caption_Table_MTE_Thesis` | **10 pt** | regular (not bold) | centred | 6 pt before, 6 pt after |
| Front-matter page titles | — | **14 pt** | **bold** | centred | |

**Line spacing is 1.5 throughout** (`w:line="360" w:lineRule="auto"` on `Normal`).

## 4. Floats **[stated]**

- **Tables**: caption goes **above** the table. Table itself centred. Caption format
  `Table 1.1. Title of the Table` — chapter.number, a full stop, then the title. Blank line
  after the table.
- **Figures**: caption goes **below** the figure. Format `Figure 1.1. Caption of a figure.`
  The template says to place the graphic in a 1×1 borderless table; in LaTeX a centred
  `figure` float is the equivalent and no table is needed.
- Graphics should be 300 dpi TIFF/EPS or vector, fonts embedded. Our matplotlib figures should
  therefore be emitted as **PDF**, not PNG.
- Caption label and number are **not bold** — the `Caption` style carries no bold run property.

## 5. Required page order

Cover page → Title page → Declaration → Approval (with the Board of Examiners table inside it)
→ Acknowledgement → Abstract → Table of Contents → List of Tables → List of Figures →
List of Abbreviations → Chapters → References → Appendices.

Notes:
- **Board of Examiners is not a separate page.** It is a table inside APPROVAL. (The repo's
  `logbook/08_project_context.md` lists it as its own page — that is wrong.)
- The final list page is **List of Abbreviations** (accepted book). The generic template calls
  it "List of Nomenclature" and mixes units, symbols and acronyms in one two-column table; we
  keep the book's title and separate the symbols into a second block.
- List of Tables / List of Figures use a three-column layout: number, description, page, with a
  bold header row.

## 6. Chapter structure — THE BOOK GOVERNS, NOT THE TEMPLATE

Two sources disagree. `kuet_thesis_style/Thesis_book_draft_3.pdf` is the accepted BSc book of
Md Masrul Khan (roll 1931011, December 2025, 85 pp), same department, same supervisor. The
generic template lists a different, hardware-shaped structure that the department evidently does
not enforce.

**Decision 2026-08-02: follow the accepted book for structure, the template for formatting.**
The book is US Letter with a 38 mm left margin, so it is not a formatting precedent — page setup,
type and captions all still come from the template as measured in sections 1–4 above.

```
CHAPTER 1  Introduction
           1.1 Background  1.2 Problem Description  1.3 Objectives  1.4 Scope
CHAPTER 2  Literature Review
           2.1 Historical Background  2.2 Related works
CHAPTER 3  Research Methodology
           3.1 Hardware Setup  3.2 Software Framework  3.3 Mathematical Modeling
CHAPTER 4  Results and Discussion
CHAPTER 5  Relation with a Real-World Problem      <- includes explicit SDG mapping
CHAPTER 6  Conclusions and Future Works
           6.1 Conclusion  6.2 Future Works
References
```

Differences from the generic template, all resolved in favour of the book:

- **Six chapters, not seven.** The template's "Design procedure / Experimental set-up / Circuit
  Diagram" and "Implementation" chapters do not exist in the accepted book; their content folds
  into Chapter 3.
- **Chapter 5 is the SDG chapter.** The template has no equivalent. The book devotes ~2 pages to
  it with no sub-sections and names SDG 4, 8, 9 and 12 explicitly. Easy to forget; it has no
  counterpart in a generic ML thesis.
- **"List of Abbreviations"**, not "List of Nomenclature".
- **Chapter headings set the title in UPPERCASE** below the `CHAPTER n` line — measured off the
  book, which settles what the template left ambiguous.

Section names within chapters are not mandated. Chapter 3's are adapted to a simulation study
(platform and robot model / software framework / mathematical modelling).

### The generic template's structure, for the record

```
CHAPTER 1  Introduction
           1.1 General
           1.2 Scope of present Investigation
           1.3 Project report layout
CHAPTER 2  Motivation / Background Study
CHAPTER 3  Methodology
CHAPTER 4  Design procedure / Experimental set-up / Circuit Diagram
           4.1 Introduction  4.2 Materials and methods  4.3 Experimental Set-up
           4.4 Experimental Procedure  4.5 Experimental Data
CHAPTER 5  Implementation
CHAPTER 6  Results and Discussions
           6.1 Results  6.2 Discussions
CHAPTER 7  Conclusion and Future Work
           7.1 Conclusion  7.2 Future Work
References
Appendix A, Appendix B …
```

Section headings are **not** auto-numbered in the Word template — "1.1", "2.3.1" are typed by
hand. LaTeX will number them automatically, which produces the same result more reliably.

## 7. Fixed boilerplate wording

**Cover page** (all centred, Times New Roman): title 20 pt bold → seven blank lines → student
name 18 pt bold → roll number 18 pt bold → blank → `Date of Defense: Month, Year` 16 pt →
blank → `Department of Mechatronics Engineering` / `Khulna University of Engineering &
Technology` / `Khulna-9203, Bangladesh` 15 pt.

**Title page**: title 14 pt bold → three blank lines → *A thesis submitted in partial
fulfillment of the requirements for the degree of / Bachelor of Science / in / Mechatronics
Engineering* → `by` → student name 12 pt bold → two blank lines → `Supervised by` → supervisor
name 12 pt bold → two blank lines → **university monogram** → department / university /
`Khulna-9203, Bangladesh` 12 pt → `Date of Defense: Month Year` 12 pt bold.

**Declaration** (14 pt bold centred heading, three blank lines, then 12 pt justified):

> This is to certify that the thesis work entitled "(Title)" has been carried out by (Student)
> under the supervision of (Supervisor) in the Department of Mechatronics Engineering, Khulna
> University of Engineering & Technology, Khulna, Bangladesh. The above thesis work or any part
> of this work has not been submitted anywhere for the award of any degree.
>
> The above declarations are true. Understanding these, this work has been submitted for the
> evaluation of an undergraduate thesis.

Then `Signature of Supervisor` / `Signature of Candidate` side by side, and a date.

**Approval** (14 pt bold centred heading, then 12 pt justified):

> This is to certify that the thesis work submitted by (Student) entitled "(Title)" has been
> approved by the board of examiners for the partial fulfillment of the requirements for the
> degree of Bachelor of Science in the Department of Mechatronics Engineering, Khulna University
> of Engineering & Technology, Khulna, Bangladesh in (Month Year).

followed by the BOARD OF EXAMINERS table: numbered rows, each with a signature line, `Name:`,
`Designation:`, `Department:`, `KUET, Khulna-9203, Bangladesh.`, and a role in the right column
(Chairman (Supervisor), External, …).

The template's own declaration text says **"fulfillment"** (US spelling). Keep it verbatim —
it is boilerplate, not our prose.

---

## 8. Conflicts and gaps

Resolved 2026-08-02 unless marked OPEN.

| # | Issue | Resolution |
|---|---|---|
| C1 | **Line spacing** | **1.5 (template wins).** `logbook/06_writing.md`'s "1.25" was almost certainly the LaTeX *stretch factor* for the same thing: LaTeX's baseline is already 1.2×, so Word 1.5 = stretch 1.25 = `\onehalfspacing`. Implemented as `\onehalfspacing`. Do not "fix" this to `\setstretch{1.5}` — that gives Word 1.8. |
| C2 | **Body font size** | **12 pt body, 14 pt chapter headings.** Closes the Day-7 "12 vs 14" question: 14 pt is the heading size, which is where the personal note came from. |
| C3 | **Chapter structure** | **Six chapters, following the accepted book — see section 6.** Reversed 2026-08-02 from the seven-chapter template order, once `Thesis_book_draft_3.pdf` was found in the repo. The SDG chapter IS required: it is Chapter 5 of the accepted book. |
| C4 | **Table body font** | **12 pt** (the template's prose), overriding the 10 pt in its own `MTE_Thesis_Table` style. |
| C5 | **Paragraph separation** | **Block paragraphs: no first-line indent, 6 pt between.** |
| C6 | **Date of Defense** | 08 August, 2026. Submission 06 August, 2026. |
| C7 | **Appendices** | **OPEN.** Note the accepted book has none. |
| C8 | **Roll number** | 2031023. Student name: Md. Abdur Rabbi. |

### Inferred, not measured

- **Chapter heading layout** — RESOLVED against the accepted book: two centred 14 pt bold lines,
  `CHAPTER n` then the title in uppercase.
- **Section heading alignment.** The template says "Left Indent", which is ambiguous. Read as
  left-aligned with no indent, since the style sets `ind left=0`. Still inferred.
