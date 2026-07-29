# Module 08 — Project Context (imported from the original "THESIS 4200" Claude Project)

Status: ◻ reference — static background, not an active work-stream. Update if any row changes.
Imported: 2026-07-29 (Day 19), from a memory-handoff dump of the old Project's custom
instructions + `memory.md` + uploaded-knowledge list. That project has no raw transcripts,
so this is "everything in its distilled memory," not a literal conversation recovery.

## Thesis identity
- Title (as filed): *"Safe Adaptive Image-Based Visual Servoing with Constrained
  Reinforcement Learning for Precision Grasping on a UR5 Manipulator: From Simulation to
  Real Hardware."*
- University: Khulna University of Engineering & Technology (KUET), Khulna-9203, Bangladesh.
- Department: Mechatronics Engineering.
- Degree: **BSc** in Mechatronics Engineering (not MSc — this was an explicit correction in
  the old project's memory; trust it).
- Supervisor: **Dr. Md. Helal-An-Nahiyan**, Professor, Dept. of Mechanical Engineering, KUET.
- External examiner precedent: Md. Shohanur Rahman, Asst. Professor, Dept. of Mechatronics
  Engineering, KUET — served on the predecessor's (Masrul Khan's) board.

## ⚠️ Not recorded anywhere — get these from the supervisor
- Defense date.
- Submission deadline (old memory said "~1.5 months remaining" as of its last update, which
  is itself now stale — treat as unknown, not as a real number).
- Page/word limit (Masrul Khan's predecessor book ran ~75 pages incl. front matter — a
  reference point, not a requirement).
- Whether a specific font **size** is mandated (see conflict below).

## Required KUET thesis-book structure
Front matter, in order: Title page → Declaration → Approval → Board of Examiners →
Acknowledgement → Abstract → Table of Contents → List of Tables → List of Figures → List of
Abbreviations.

Chapters:
1. Introduction (Background, Problem Description, Objectives, Scope)
2. Literature Review (Historical Background, Related Works)
3. Research Methodology (Hardware Setup, Software Framework, Mathematical Modeling)
4. Results & Discussion
5. **Relation with a Real-World Problem** — includes **SDG mapping**. KUET-specific
   requirement, easy to forget, has no equivalent in a generic ML thesis structure.
6. Conclusions and Future Works
References — **IEEE numeric style**, `[n]` in text, numbered list.

Template source: Md Masrul Khan's KUET BSc thesis book (Dec 2025) — see References below.

## Formatting — one open conflict
`logbook/06_writing.md` already flags this (Day 7), still unresolved: project instructions
say Times New Roman **12**; a separate personal note says **14**. KUET precedent (Khan's
book) uses 12 for body text — 14 would be unusually large for a thesis book. Confirm with
the supervisor rather than guessing; don't let a chapter draft lock in the wrong size.
Otherwise settled: justified, 1.25 line spacing, full page width; figures/tables + captions
centre-aligned; a few purposeful colours, not decorative.

Not settled, and the predecessor's book isn't a reliable guide (it mixes conventions):
person/voice (first person vs. passive), British vs. American spelling, methodology tense.
Pick these before drafting Chapter 3, not during.

## People — do not conflate
- **Fawad Khan et al.**, "Reinforcement learning for precision grasping and safety-critical
  coordination in a robotic arm," *Intelligent Service Robotics* 19:16 (2026),
  DOI 10.1007/s11370-025-00668-0. Safety Gym + Panda arm, PPO vs cPPO. **This is the cPPO
  reference** — read Sections 3–4 (the Lagrangian machinery) before extending the cPPO
  benchmark. Still unread as of the last memory update.
- **Md Masrul Khan** (roll 1931011), KUET Mechatronics BSc 2025, same lab, same supervisor.
  CSRT tracking + classical IBVS on a custom 5-DOF arm, ROS 2 Humble. This thesis is
  positioned as the **RL/safety upgrade of Masrul Khan's work** — use his book for lit-review
  positioning and as the classical-IBVS baseline to compare against. Same supervisor means
  the examiners already know that prior work.

## Core references
| File (in old Project, not this repo) | What it is |
|---|---|
| Fawad Khan et al. 2026 | cPPO grasping — see above |
| Asad Ali Shahid et al., *Autonomous Robots* 46:483–498 (2022), DOI 10.1007/s10514-022-10034-z | PPO vs SAC + sim-to-real on Franka |
| Haobin Shi et al., *IEEE Trans. Fuzzy Systems* 28(12):3244 (2020), DOI 10.1109/TFUZZ.2020.2991147 | Adaptive IBVS + RL with fuzzy state coding — source of the mixture parameter β |
| Lei Zhang et al., arXiv:2312.15809 (2023) | Closed-loop multi-perspective visual servoing with RL |
| Your own thesis proposal (Word, 25 May 2026) | Original abstract — still names Gazebo as a candidate simulator, **superseded** by the Isaac Sim 5.0.0 freeze. Don't let that stale text leak into Chapter 3. |
| Md Masrul Khan's KUET thesis book (Dec 2025), + `Thesis_book_draft_3.md` markdown conversion | Structural template incl. Declaration/Approval/Board pages, IEEE reference formatting |
| Journal of Robotics 2026 — Khan, CSRT + IBVS | Journal version of the predecessor's work |

**⚠️ Missing: Xia 2024 (UR5e safe DRL)** is named as a core reference in the project
instructions but no PDF exists for it in the old Project or (checked 2026-07-29) this repo.
Needs re-sourcing before it's cited.

**⚠️ None of the above PDFs/markdown files are in this working folder.** They exist only in
the old Project's uploaded knowledge. If they're needed for lit review or Chapter 2 writing
in this session, they need to be uploaded here first.

## Scope-pivot history — resolved, don't re-litigate
The old project's memory (last updated before Day 18) records an **unresolved** debate: a
proposed pivot from the Layer 1→3 progression to a broader multi-algorithm comparison
(PPO/cPPO/SAC/TD3/DDPG), with that Claude refusing to commit to a title change pending two
questions — what's the central claim, and how is on-policy vs. off-policy fairness defended.

**This is stale. The pivot happened and is already well underway in this repo**, as a
narrower, better-scoped version of exactly what was being asked for:
- Central claim resolved as the registered hypothesis in `logbook/03c_multialgo_benchmark.md`
  (SAC's entropy vs. TD3's determinism vs. cPPO's direct control of the safety axis) —
  not a generic benchmark.
- Fairness protocol is written down (equal env-step budget, not wall-clock; documented LR
  sweep; same eval harness) — same file, "Fairness protocol" section.
- DDPG was dropped, keeping it to PPO/cPPO/SAC/TD3 with an explicit cut order and a hard
  date (TD3 first cut, Aug 6 EOD).
- PPO ×3 seeds are already trained (Day 19).

No action needed here — just don't reopen the "is this pivot justified" conversation from
the old memory as if it's live. It was answered by narrowing the scope, and answered well.

## Decisions with rationale (from old memory, cross-check before citing as current)
- **Robotiq 2F-85 rejected from the critical path** (early decision) — Isaac Lab mimic-joint
  / kinematic-loop handling was an open upstream issue (GitHub #2424, #2626). Approved plan
  at the time was a simplified prismatic gripper. **Superseded in practice**: the current env
  (`ur5_grasp/robots/ur5e_robotiq.py`) uses the actual 2F-85 asset with a kinematic WELD
  abstraction for the grasp itself, which sidesteps the mimic-joint problem a different way
  (weld triggers on action sign, not joint dynamics) rather than switching geometry. Worth
  one sentence in Methods explaining why the abstraction exists, per
  `Thesis_Documentation/Methods_Chapter_Layer1.md` §2 — already written.
- No pre-built Isaac Lab UR5 config existed — the `ArticulationCfg` was hand-written off the
  UR10 pattern in `isaaclab_assets/robots/universal_robots.py`, starting from
  `Isaac-Lift-Cube-Franka-v0`. (Historical; env is now frozen — see `03c` / `HANDOFF.md`.)
- GitHub repo `ur5-safe-rl-thesis` (`git@github.com:abdurRabbi23/ur5-safe-rl-thesis.git`) is
  public, daily-push habit established. Local `main` and `origin/main` have since diverged —
  see the open task from 2026-07-29 in this session.

## Operational knowledge already covered elsewhere in this repo
(Not duplicated here — confirmed present when this file was written.)
- NVIDIA driver ≥570 (machine runs 580.159.03), PyTorch 2.7.0+cu128, numpy 1.26.0 pin:
  `Thesis_Documentation/01_Environment_Setup.md`.
- Tailscale (`100.109.10.66`) + NoMachine remote-access workflow, tmux session discipline,
  TensorBoard `--bind_all` on port 6006: `Thesis_Documentation/10_Command_Reference.md`.
- Lagrangian cPPO's silent-failure mode (constraint quietly does nothing while training looks
  healthy — check loss combination and λ sign convention): already the lesson embedded in the
  Day 19 `cost_limit`/episode-length coupling writeup, `logbook/03c_multialgo_benchmark.md`.

Not yet written anywhere — worth a line in `Thesis_Documentation/07_Troubleshooting.md` if it
recurs: flatdict build fails under `setuptools>=82` (pin `setuptools<81`,
`--no-build-isolation`); torchaudio needs manual reinstall after the Isaac Lab installer
churns the torch version; the Warp `cuDeviceGetUuid unsupported by driver 580` warning is
benign; "connection refused" = process down vs. hang/timeout = network/firewall, different
fixes; `>>` vs `>` cost a clobbered log once.

## Open / promised items (from old memory, re-verify still true before acting)
1. Get from the supervisor and write down: defense date, submission deadline, page limit,
   mandated font size. Highest priority — blocks final formatting decisions.
2. Read Fawad Khan et al. Sections 3–4 before extending the cPPO benchmark further.
3. Re-time `num_envs` for the current grasping env before setting any *new* training budget
   beyond what's already frozen — 8192 was validated for Franka Reach, not this env. (Likely
   moot: Layer 1 is frozen at 4096 and PPO ×3 seeds already ran clean at that number — flag
   only if `num_envs` is revisited.)
4. Layer 2 (IBVS) reference implementation to consult: `github.com/aparame/RL_UR5_IsaacLab`.

## Refs
Source: memory-handoff dump from the "THESIS 4200" Claude Project, pasted into this session
2026-07-29. See `run_log.md` Day 19 for the import note.
