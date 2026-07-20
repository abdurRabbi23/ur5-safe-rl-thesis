# Module 07 — Beginner Documentation (replicate-from-scratch guide)

Status: ▶ ongoing, written parallel to the thesis
Chat type: documentation
Last updated: 2026-07-20 (Day 10)

## Goal
Maintain `Thesis_Documentation/` — a beginner-facing guide that lets someone with no context
replicate the whole thesis from an empty machine to final results. Every step: the command, why/when
to run it, and the expected output. Written alongside the work, not at the end.

## Where it lives
`Thesis_Documentation/` (front door: `00_START_HERE.md`). This is the cleaned-up, beginner version
of the `logbook/` notes + `run_log.md`; nothing here duplicates the deep working state — it
translates it for a fresh reader.

## Current state (Day 10)
- 10 pages built. 01 env-setup + 02 grasp-env fully written (done work); **03 cppo-benchmark now
  COMPLETE — runbook Steps 6-7 done, real benchmark numbers filled, Layer 1 PASS**; 04 IBVS + 05
  sim2real are planned outlines; 06 results holds the headline table + the four generated figures
  (`Thesis_Documentation/assets/`); 07 troubleshooting (all bugs+fixes), 08 glossary, 09 changelog.
- All script/asset paths referenced in the docs verified to exist in the repo.

## Working convention (keep it in sync)
When work happens in a module → update the matching `Thesis_Documentation/NN_*.md` page AND append a
dated line to `Thesis_Documentation/09_Changelog.md` (in addition to the usual module-file +
run_log.md update).

## End-of-session routine (commit + push)
A nightly reminder (scheduled task `thesis-git-push-reminder`, 23:00 daily) nudges this. Each
session, on the lab PC:
```
cd ~/Abdur_Rabbi_THESIS
rm -f .git/index.lock          # clear any stray lock
git add -A
git status -s                  # sanity-check what's staged
git commit -m "<summary of today's work>"
git push origin main
```
Do the docs update (page + 09_Changelog.md) BEFORE committing. Remote is SSH — push from the lab PC
where the key lives. If push asks for a password → `ssh-add ~/.ssh/<key>`; if rejected as "behind"
→ `git pull --rebase origin main` then push.

## Page ↔ module map
- 01_Environment_Setup  ← Module 01
- 02_Grasp_Environment  ← Module 02
- 03_Safety_and_cPPO_Benchmark ← Module 03 (+ 03b runbook)
- 04_Layer2_IBVS        ← Module 04
- 05_Layer3_SimToReal   ← Module 05
- 06_Results_and_Experiments, 07_Troubleshooting, 08_Glossary, 09_Changelog ← cross-cutting

## Next steps
- After the two full runs (Module 03 Steps 6-7): fill the benchmark table in 06 + real curves in 03.
- Begin 04/05 pages when those layers start.

## run_log.md refs
Day 9 (2026-07-19): documentation folder created.
