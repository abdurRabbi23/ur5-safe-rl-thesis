#!/usr/bin/env python3
"""
build_chapter_pdfs.py -- standalone PDF for any one chapter, any set of
chapters together, the cover page, or the bibliography -- pulled straight
out of the real thesis source.

Why this exists: Touhid needs to hand a supervisor "just Chapter 3" or "3
and 4 together" without shipping the whole book. The chapter .tex files are
not self-contained -- they \ref and \pageref things defined in other
chapters (e.g. Chapter 1 points at Chapter 4's results). This script builds
a throwaway wrapper document that includes only the requested chapters, and
forces in the \newlabel values for every cross-reference target defined
elsewhere in the book (read from main.aux, which a full `latexmk -pdf
main.tex` run must have produced first) so nothing prints as "??".

Chapter PDFs carry no title page and no bibliography (2026-08-04, Touhid's
instruction) -- those are separate deliverables, built with --cover and
--bibliography, so a chapter hand-out is just that chapter's own content.

Usage
-----
    python3 tools/build_chapter_pdfs.py 3              # just Chapter 3
    python3 tools/build_chapter_pdfs.py 3 4             # Chapters 3-4, one PDF
    python3 tools/build_chapter_pdfs.py --cover          # cover page alone
    python3 tools/build_chapter_pdfs.py --bibliography   # full reference list alone
    python3 tools/build_chapter_pdfs.py --all             # every chapter + cover + bibliography

Output: Thesis_LaTeX/chapter_pdfs/
    Chapter_<N>_<Title>.pdf              (single chapter)
    Chapters_<N>-<M>_<Title>_<Title>.pdf (combined chapters)
    Cover_Page.pdf
    Bibliography.pdf
All overwritten each run.

Notes
-----
- Requires main.aux AND main.bbl to exist and be reasonably current (run
  `latexmk -pdf main.tex` first if you've edited a chapter or a \cite).
  This script does NOT do a full-thesis build -- it only borrows main.aux's
  label table and main.bbl's resolved reference list.
- Chapter PDFs always build with the [final] format option, so draft notes
  / TODO markers never appear in a hand-out, even before the full thesis is
  finalised.
- Bibliography.pdf is main.bbl (the full book's reference list, from every
  chapter's \cite calls) verbatim -- not just the references cited in
  whatever chapters you happen to be exporting alongside it.
- Does not touch main.tex or any chapter file.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # Thesis_LaTeX/
CHAPTERS_DIR = ROOT / "chapters"
OUT_DIR = ROOT / "chapter_pdfs"
BUILD_DIR = ROOT / "_chapter_build"  # scratch, safe to wipe

CHAPTER_RE = re.compile(r"\\chapter\{([^}]*)\}\s*\\label\{([^}]*)\}")
LABEL_RE = re.compile(r"\\label\{([^}]*)\}")
NEWLABEL_RE = re.compile(r"\\newlabel\{([^}]*)\}")

SYMLINK_ITEMS = ["chapters", "frontmatter", "figures", "thesis-format.sty",
                  "references.bib", "kuet_thesis_style"]


def discover_chapters():
    """Map chapter number -> (path, title, its own \\label{} keys)."""
    chapters = {}
    for path in sorted(CHAPTERS_DIR.glob("*.tex")):
        n = int(path.stem.split("_", 1)[0])
        text = path.read_text()
        m = CHAPTER_RE.search(text)
        title = m.group(1) if m else path.stem
        own_labels = set(LABEL_RE.findall(text))
        chapters[n] = {"path": path, "title": title, "labels": own_labels}
    return chapters


def slugify(title):
    return re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")


def imported_label_block(main_aux, exclude_labels):
    """\\newlabel lines from main.aux for every label NOT defined by the
    chapters we're including -- so \\ref/\\pageref into other chapters
    still resolve, without colliding with labels this build defines itself."""
    if not main_aux.exists():
        sys.exit(
            f"error: {main_aux} not found. Run `latexmk -pdf main.tex` once "
            "(a full build) so there's a label table to borrow from."
        )
    lines = []
    for line in main_aux.read_text().splitlines():
        m = NEWLABEL_RE.match(line)
        if m and m.group(1) not in exclude_labels:
            lines.append(line)
    return "\n".join(lines)


def ensure_symlinks():
    BUILD_DIR.mkdir(exist_ok=True)
    for item in SYMLINK_ITEMS:
        link = BUILD_DIR / item
        if not link.exists():
            link.symlink_to(ROOT / item)


def compile_and_check(tex_name, out_name, allow_bibliography_heading=False):
    """Run latexmk on tex_name inside BUILD_DIR, sanity-check the result,
    and copy it into OUT_DIR/out_name. Returns the output path."""
    log_path = BUILD_DIR / f"{tex_name}.buildlog"
    result = subprocess.run(
        ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", tex_name],
        cwd=BUILD_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    log_path.write_text(result.stdout + result.stderr)
    pdf_path = BUILD_DIR / tex_name.replace(".tex", ".pdf")
    if result.returncode != 0 or not pdf_path.exists():
        print(result.stdout[-3000:])
        sys.exit(f"error: build failed for {tex_name}, see {log_path}")

    text_check = subprocess.run(["pdftotext", str(pdf_path), "-"],
                                 capture_output=True, text=True,
                                 encoding="utf-8", errors="replace").stdout
    if "Draft note" in text_check or re.search(r"\bTODO\b", text_check):
        sys.exit(f"error: draft material leaked into {out_name} -- check source")
    if "??" in text_check:
        sys.exit(
            f"error: unresolved cross-reference (??) in {out_name} -- "
            "main.aux/main.bbl is probably stale, rebuild main.tex first"
        )

    OUT_DIR.mkdir(exist_ok=True)
    out_path = OUT_DIR / out_name
    out_path.write_bytes(pdf_path.read_bytes())
    print(f"built {out_path.relative_to(ROOT)}")
    return out_path


def build_one(nums, chapters):
    """One PDF holding just the given chapter number(s), no title page, no
    bibliography -- content only."""
    nums = sorted(nums)
    missing = [n for n in nums if n not in chapters]
    if missing:
        sys.exit(f"error: no chapter file for number(s) {missing}")

    own_labels = set()
    for n in nums:
        own_labels |= chapters[n]["labels"]

    label_block = imported_label_block(ROOT / "main.aux", own_labels)

    includes = "\n".join(
        f"\\input{{chapters/{chapters[n]['path'].stem}}}" for n in nums
    )

    wrapper = f"""% AUTO-GENERATED by tools/build_chapter_pdfs.py -- do not hand-edit.
% Source of truth is main.tex + chapters/*.tex; this is a throwaway view.
% No title page, no bibliography -- chapter content only.
\\documentclass[12pt,a4paper,oneside]{{book}}
\\usepackage[final]{{thesis-format}}
\\input{{frontmatter/_thesis_details}}

% -- cross-reference targets borrowed from a full main.tex build --
\\makeatletter
{label_block}
\\makeatother

\\begin{{document}}
\\kuetbodystyle
\\setcounter{{chapter}}{{{nums[0] - 1}}}
{includes}
\\end{{document}}
"""

    ensure_symlinks()
    tag = f"ch{nums[0]}" if len(nums) == 1 else f"ch{nums[0]}to{nums[-1]}"
    tex_name = f"chapter_{tag}.tex"
    (BUILD_DIR / tex_name).write_text(wrapper)

    if len(nums) == 1:
        n = nums[0]
        out_name = f"Chapter_{n}_{slugify(chapters[n]['title'])}.pdf"
    else:
        span = (f"{nums[0]}-{nums[-1]}" if nums == list(range(nums[0], nums[-1] + 1))
                else "_".join(map(str, nums)))
        titles = "_".join(slugify(chapters[n]["title"]) for n in nums)
        out_name = f"Chapters_{span}_{titles}.pdf"

    return compile_and_check(tex_name, out_name)


def build_cover():
    """Cover_Page.pdf -- frontmatter/coverpage.tex alone, unnumbered."""
    wrapper = """% AUTO-GENERATED by tools/build_chapter_pdfs.py -- do not hand-edit.
\\documentclass[12pt,a4paper,oneside]{book}
\\usepackage[final]{thesis-format}
\\input{frontmatter/_thesis_details}
\\begin{document}
\\pagestyle{empty}
\\input{frontmatter/coverpage}
\\end{document}
"""
    ensure_symlinks()
    tex_name = "cover.tex"
    (BUILD_DIR / tex_name).write_text(wrapper)
    return compile_and_check(tex_name, "Cover_Page.pdf")


def build_bibliography():
    """Bibliography.pdf -- the full book's reference list, taken verbatim
    from main.bbl (i.e. every chapter's \\cite calls, not just whichever
    chapters were exported alongside it)."""
    main_bbl = ROOT / "main.bbl"
    if not main_bbl.exists():
        sys.exit(
            f"error: {main_bbl} not found. Run `latexmk -pdf main.tex` once "
            "(a full build) so there's a resolved reference list to use."
        )
    bbl_text = main_bbl.read_text()
    if "\\begin{thebibliography}" not in bbl_text:
        sys.exit(f"error: {main_bbl} doesn't look like a compiled bibliography")

    wrapper = f"""% AUTO-GENERATED by tools/build_chapter_pdfs.py -- do not hand-edit.
% main.bbl embedded verbatim -- this is the full book's reference list,
% already resolved by the last full `latexmk -pdf main.tex` run.
\\documentclass[12pt,a4paper,oneside]{{book}}
\\usepackage[final]{{thesis-format}}
\\input{{frontmatter/_thesis_details}}
\\begin{{document}}
\\kuetbodystyle
\\phantomsection
\\addcontentsline{{toc}}{{chapter}}{{References}}
{bbl_text}
\\end{{document}}
"""
    ensure_symlinks()
    tex_name = "bibliography.tex"
    (BUILD_DIR / tex_name).write_text(wrapper)
    return compile_and_check(tex_name, "Bibliography.pdf")


def build_submission(chapters):
    """Thesis_Report_Body_Submission.pdf -- cover page, then every chapter in
    order, with a real bibliography. No other front matter (no title page,
    declaration, approval, acknowledgement, abstract, TOC/LOF/LOT or
    abbreviations -- Touhid's choice, 2026-08-04). The cover page was added
    back on request, 2026-08-04, so the PDF opens on the thesis title rather
    than straight into Chapter 1.

    Self-contained: every chapter is present in this same build, so every
    \\ref/\\pageref/\\cite resolves on its own -- unlike single-chapter
    exports, this one does NOT depend on main.aux/main.bbl being fresh."""
    nums = sorted(chapters)
    includes = "\n".join(
        f"\\input{{chapters/{chapters[n]['path'].stem}}}" for n in nums
    )
    wrapper = f"""% AUTO-GENERATED by tools/build_chapter_pdfs.py -- do not hand-edit.
% Cover page + all chapters, in order, self-contained -- [final].
\\documentclass[12pt,a4paper,oneside]{{book}}
\\usepackage[final]{{thesis-format}}
\\input{{frontmatter/_thesis_details}}
\\begin{{document}}
\\pagestyle{{empty}}
\\input{{frontmatter/coverpage}}
\\mainmatter
\\kuetbodystyle
{includes}

\\backmatter
\\phantomsection
\\addcontentsline{{toc}}{{chapter}}{{References}}
\\IfFileExists{{IEEEtran.bst}}{{\\bibliographystyle{{IEEEtran}}}}{{\\bibliographystyle{{unsrt}}}}
\\bibliography{{references}}
\\end{{document}}
"""
    ensure_symlinks()
    tex_name = "submission.tex"
    (BUILD_DIR / tex_name).write_text(wrapper)
    return compile_and_check(tex_name, "Thesis_Report_Body_Submission.pdf")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chapters", nargs="*", type=int,
                     help="chapter numbers, e.g. 3 4 for a combined Ch.3-4 PDF")
    ap.add_argument("--all", action="store_true",
                     help="build every chapter (separately) plus cover + bibliography")
    ap.add_argument("--cover", action="store_true", help="build Cover_Page.pdf alone")
    ap.add_argument("--bibliography", action="store_true",
                     help="build Bibliography.pdf alone (full reference list)")
    ap.add_argument("--submission", action="store_true",
                     help="build every chapter + real bibliography as ONE pdf, "
                          "no front matter (Thesis_Report_Body_Submission.pdf)")
    args = ap.parse_args()

    chapters = discover_chapters()

    if args.all:
        if args.chapters:
            sys.exit("error: don't mix --all with explicit chapter numbers")
        for n in sorted(chapters):
            build_one([n], chapters)
        build_cover()
        build_bibliography()
        return

    did_something = False
    if args.cover:
        build_cover()
        did_something = True
    if args.bibliography:
        build_bibliography()
        did_something = True
    if args.submission:
        build_submission(chapters)
        did_something = True
    if args.chapters:
        build_one(args.chapters, chapters)
        did_something = True

    if not did_something:
        sys.exit("error: give chapter number(s) (e.g. `3` or `3 4`), or pass "
                  "--cover / --bibliography / --submission / --all")


if __name__ == "__main__":
    main()
