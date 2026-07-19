# 09 — Documentation Changelog

Dated log of edits to **this documentation** (separate from the project's `run_log.md`, which logs
the thesis work itself). Add a line each time these pages change, so the docs stay honestly in sync
with the thesis.

**Convention:** when thesis work happens in a module, update the matching `NN_*.md` page here AND
append a dated line below.

---

## 2026-07-19 — Documentation created

- Set up `Thesis_Documentation/` folder inside the thesis working folder.
- Wrote from the existing `logbook/`, `run_log.md`, and `ur5_grasp/` source (project state: Day 9):
  - `00_START_HERE.md` — overview, section map, one-paragraph explainer, frozen stack, repo map.
  - `01_Environment_Setup.md` — ✅ full guide (hardware → driver → conda → PyTorch cu128 → Isaac Sim
    5.0 → Isaac Lab v2.3.0 tag → Cartpole + Franka-Reach validation → TensorBoard → num_envs →
    session checklist).
  - `02_Grasp_Environment.md` — ✅ full guide (retarget Franka lift → UR5e, gripper decision, merged
    USD, the 3 physics bugs, the throwing reward-hack, the proximity weld, PPO baseline retrain,
    play verification).
  - `03_Safety_and_cPPO_Benchmark.md` — ▶ in progress (safety costs, cPPO on rsl_rl, calibration to
    MANIP_FLOOR=0.045, cost_limit=25; runbook Steps 1–5 done; Steps 6–7 marked PENDING).
  - `04_Layer2_IBVS.md` — ⏳ planned outline.
  - `05_Layer3_SimToReal.md` — ⏳ planned outline (incl. RH-P12-RN import reference).
  - `06_Results_and_Experiments.md` — ▶ reproduce-commands table + validation/calibration results;
    headline benchmark table PENDING.
  - `07_Troubleshooting.md` — consolidated every bug + fix hit through Day 9.
  - `08_Glossary.md` — ✅ plain-English terms for beginners.
  - `09_Changelog.md` — this file.

---

## Template for future entries

```
## YYYY-MM-DD — <short title>
- <what changed in the docs and why> (page: NN_*.md)
- <new result / command / fix documented>
```
