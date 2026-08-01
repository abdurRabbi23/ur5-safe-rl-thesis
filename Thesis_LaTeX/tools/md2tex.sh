#!/usr/bin/env bash
# md2tex.sh — one-time helper: port a Thesis_Documentation/*.md chapter draft to LaTeX.
#
#   usage: tools/md2tex.sh ../Thesis_Documentation/Foo_Chapter.md chapters/NN_foo.tex
#
# It does the mechanical 80%: unicode maths -> LaTeX maths, strips hand-typed
# section numbers (LaTeX numbers sections itself), runs pandoc.
# The remaining 20% (labels, \ref, tables, draftonly wrapping) is done by hand
# in the .tex afterwards. Once a chapter is ported, the .tex is the source of
# truth and the .md is frozen as a dated record -- do NOT re-run this over a
# chapter you have already edited.
set -euo pipefail
IN="$1"; OUT="$2"
TMP="$(mktemp)"

sed -E \
  -e 's/√det\(J ?J(ᵀ)\)/$\\sqrt{\\det(JJ^{\\top})}$/g' \
  -e 's/10⁻⁶/$10^{-6}$/g' -e 's/10⁻⁴/$10^{-4}$/g' -e 's/10⁵/$10^{5}$/g' -e 's/10⁶/$10^{6}$/g' \
  -e 's/λ/$\\lambda$/g'  -e 's/γ/$\\gamma$/g' -e 's/η/$\\eta$/g' \
  -e 's/π/$\\pi$/g'      -e 's/Σ/$\\Sigma$/g' -e 's/Ĵ/$\\hat{J}$/g' \
  -e 's/×/$\\times$/g'   -e 's/±/$\\pm$/g'    -e 's/≤/$\\le$/g' -e 's/≥/$\\ge$/g' \
  -e 's/∈/$\\in$/g'      -e 's/−/$-$/g'       -e 's/·/$\\cdot$/g' \
  -e 's/←/$\\leftarrow$/g' -e 's/°/\\textdegree{}/g' -e 's/§/\\S{}/g' \
  -e 's/✅/[done]/g'     -e 's/✏/[draft]/g' \
  -e 's/^(#+) [0-9]+(\.[0-9]+)*\.? /\1 /' \
  "$IN" > "$TMP"

pandoc "$TMP" -f markdown -t latex --top-level-division=chapter --wrap=preserve -o "$OUT"
rm -f "$TMP"
echo "wrote $OUT"
