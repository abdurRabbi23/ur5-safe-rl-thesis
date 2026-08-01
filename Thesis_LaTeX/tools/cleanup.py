#!/usr/bin/env python3
"""One-time post-pandoc cleanup. See tools/md2tex.sh -- run once per chapter, never again."""
import re, sys, pathlib

def clean(p, chapter_title, short_labels):
    t = pathlib.Path(p).read_text()

    # 1. pandoc \hypertarget{id}{% \n \section{T}\label{id}}  ->  \section{T}\label{id}
    t = re.sub(r'\\hypertarget\{[^}]*\}\{%\n(\\(?:chapter|section|subsection)\{.*?\}\\label\{[^}]*\})\}',
               r'\1', t)

    # 2. table cells: drop pandoc's minipage scaffolding
    t = re.sub(r'\\begin\{minipage\}\[[bt]\]\{[^}]*\}\\raggedright\n(.*?)\\strut\n\\end\{minipage\}',
               lambda m: m.group(1).strip(), t, flags=re.S)

    # 3. readable chapter title
    t = re.sub(r'\\chapter\{.*?\}\\label\{[^}]*\}', lambda _: chapter_title, t, count=1)

    # 4. citation placeholders -> a macro that renders a visible marker
    t = t.replace(r'\texttt{{[}TODO-A{]}}', r'\todocite{A}').replace(r'\texttt{{[}TODO-B{]}}', r'\todocite{B}')
    t = t.replace(r'{[}TODO-A{]}', r'\todocite{A}').replace(r'{[}TODO-B{]}', r'\todocite{B}')

    # 5. short, stable labels
    for slug, short in short_labels.items():
        t = t.replace('\\label{%s}' % slug, '\\label{%s}' % short)

    # 6. horizontal rules from the markdown are not thesis furniture
    t = t.replace(r'\begin{center}\rule{0.5\linewidth}{0.5pt}\end{center}', r'%--- (md section break)')
    return t

r = pathlib.Path('chapters/04_results.tex')
m = pathlib.Path('chapters/03_methodology.tex')

mt = clean(m, r'\chapter{Research Methodology}\label{ch:methods}',
           {'problem-formulation':'sec:m-cmdp',
            'simulation-environment-and-task':'sec:m-env',
            'state-action-and-reward':'sec:m-mdp',
            'the-safety-cost-function':'sec:m-cost',
            'constrained-policy-optimisation-cppo':'sec:m-cppo',
            'constraint-calibration-and-cost-budget':'sec:m-calib',
            'training-protocol':'sec:m-train',
            'evaluation-protocol':'sec:m-eval'})
# in-prose forward references -> real \ref
for n, lab in [('2','sec:m-env'),('3','sec:m-cost'),('4','sec:m-cppo'),('5','sec:m-calib')]:
    mt = mt.replace('(Section %s)' % n, '(Section~\\ref{%s})' % lab)
mt = mt.replace('(Sections 6--7)', '(Sections~\\ref{sec:m-train}--\\ref{sec:m-eval})')

rt = clean(r, r'\chapter{Results and Discussion}\label{ch:results}',
           {'experimental-design-and-provenance':'sec:r-design',
            'validity-check-the-control-arm-reproduces-the-baseline-exactly':'sec:r-validity',
            'how-this-comparison-must-be-read':'sec:r-reading',
            'task-performance':'sec:r-task',
            'safety':'sec:r-safety',
            'the-principal-finding-of-this-batch-collapse-of-seed-to-seed-safety-variance':'sec:r-variance',
            'limitations':'sec:r-limits',
            'summary':'sec:r-summary'})

# draft-only tail: provisional refs + revision notes are kept, but never printed in the book
i = rt.index(r'\section{Provisional references cited in this chapter}')
rt = (rt[:i] + '\\begin{draftonly}\n'
      + rt[i:].replace(r'\section{', r'\section*{', 2) + '\n\\end{draftonly}\n')

m.write_text(mt); r.write_text(rt)
print('cleaned both chapters')
