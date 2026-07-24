# Module 04 — IBVS Visual Loop (Layer 2, stretch)

Status: 🟢 STARTED — Phase 1 (camera) DONE (2026-07-24, Day 13). Layer 1 signed off.
Chat type: vision / IBVS
Last updated: 2026-07-24 (Day 13)

## Goal
Add the image-based visual servoing loop with an RL-tuned image Jacobian (fuzzy state
coding, mixture parameter β), replacing privileged pose with an eye-in-hand camera.

## Hardware decision (Day 13)
RGB **webcam only** — no RGB-D available. Monocular IBVS with approximate depth; the
unmeasured Z becomes the job of the RL-tuned image Jacobian (a cleaner contribution, and
it matches Khan 2026's monocular CSRT baseline). Sim camera configured RGB-only to match.

## Phase plan
1. ✅ Camera → cube pixel (eye-in-hand RGB, verified).
2. ⏳ Classical IBVS baseline (colour-centroid detection + interaction matrix).
3. ⏳ RL-tuned image Jacobian (cPPO correction + FOV cost term).
4. ⏳ Benchmark RL-tuned vs classical + figures.

## Phase 1 result (verified)
- `ur5_grasp/scripts/ibvs_camera_test.py` — wrist-mounted `CameraCfg` injected into the
  PLAY env (Layer 1 files untouched). Renders RGB; world→pixel projection confirmed
  (on-axis point projects to image centre; cube pixel tracks the cube).
- **Verified camera mount** (eye-in-hand on `wrist_3_link`, ROS convention):
  `pos=(-3e-05, 0.00368, -0.03983)`, `rot=(-0.03285, 0.70643, 0.70629, 0.03228)`.
- **Approach axis is wrist −z** (not +z). The env `ee_frame` offset `[0,0,0.16]` is
  approximate/sign-flipped vs the true fingertip TCP — camera aim was recovered
  empirically via `recommend_aim()`.

## Guardrail
Never let Layer 2 endanger Layer 1. (Layer 1 = pass bar, signed off.)

## Gotchas (Day 13)
- Camera sensors REQUIRE `--enable_cameras`; headless training never exercised this path.
- `CUDA error 804` / "Failed to query CUDA device count" on first camera run = an apt
  driver update (→580.173) with the old kernel module still loaded. Fix = reboot.
  Consider `apt-mark hold` on the nvidia driver to freeze the stack.

## Key references
Shi 2020 (IBVS + Q-learning), Zhang (fuzzy IBVS), Khan 2026 (classical monocular baseline).

## run_log.md refs
- 2026-07-24 (Day 13) — Layer 2 kickoff + Phase 1 camera verified.
