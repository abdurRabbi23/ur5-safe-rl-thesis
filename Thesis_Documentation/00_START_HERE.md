# Thesis Work Documentation — START HERE

**Thesis:** Safe Adaptive Image-Based Visual Servoing with Constrained Reinforcement
Learning for Precision Grasping on a UR5 Manipulator — From Simulation to Real Hardware.

**Author:** Touhid (abrabbi9999@gmail.com)

---

## What this documentation is

This is a **replicate-from-scratch guide**. If you know basic Python but nothing about this
project, you should be able to read these pages top to bottom and rebuild the whole thesis on
your own machine — from an empty computer to the final results.

Every step tries to tell you three things:

1. **What** command to run (the exact terminal line).
2. **Why and when** you run it (what it does, what must be done before it).
3. **What you should see** (the expected output, so you know it worked).

When something can break, there is a note on what the error means and how to fix it.

> This is a **living document**, written *in parallel* with the thesis. Finished work is fully
> written up. Work that is still ongoing is marked `IN PROGRESS`, and work that has not started
> is marked `PLANNED` with a short outline so the map is complete from day one.

---

## How to use it (recommended reading order)

Read in order the first time. Later, jump straight to the section you need.

| # | File | What it covers | Status |
|---|------|----------------|--------|
| 00 | `00_START_HERE.md` | This page — overview, map, how to read | — |
| 01 | `01_Environment_Setup.md` | Hardware, drivers, Isaac Sim, Isaac Lab, PyTorch, validation | ✅ Done |
| 02 | `02_Grasp_Environment.md` | UR5e grasp env, gripper, the "weld" fix, PPO baseline | ✅ Done |
| 03 | `03_Safety_and_cPPO_Benchmark.md` | Safety costs, cPPO, calibration, the core benchmark | ✅ Done (Layer 1 PASS) |
| 04 | `04_Layer2_IBVS.md` | Image-based visual servoing loop (stretch goal) | ⏳ Planned |
| 05 | `05_Layer3_SimToReal.md` | Transfer to the real UR5e (optional goal) | ⏳ Planned |
| 06 | `06_Results_and_Experiments.md` | Configs, TensorBoard, benchmark tables and plots | ✅ Layer 1 results + figures done |
| 07 | `07_Troubleshooting.md` | Every bug hit + the fix, in one place | ▶ Growing |
| 08 | `08_Glossary.md` | Plain-English terms for beginners | ✅ Done |
| 09 | `09_Changelog.md` | Dated log of edits to this documentation | ▶ Ongoing |

`assets/` holds screenshots, plots, and diagrams referenced by the pages above.

---

## The thesis in one paragraph (for a total beginner)

A **UR5** is a robot arm. We want it to **pick up an object precisely** while never doing
anything unsafe (hitting the table, bending a joint past its limit, or twisting into a "locked"
pose called a *singularity*). We teach the arm using **reinforcement learning (RL)** — the arm
practises millions of times in a **simulator** and is rewarded for good grasps. Plain RL will
happily break safety rules if that earns more reward, so we use **constrained RL (cPPO)**, which
learns to grasp *while keeping rule-breaking under a fixed budget*. The headline experiment
compares **cPPO vs plain PPO**: both learn to grasp, but cPPO stays safe and PPO does not. Later
layers add a **camera-guided** control loop (IBVS) and move the trained policy onto the **real
robot**.

---

## The three layers (scope)

The thesis is built in three layers so the must-have result is protected:

- **Layer 1 — Safe RL grasping in simulation (MUST PASS).** cPPO vs PPO benchmark. This alone is
  a complete, defensible thesis. Covered in sections 02–03 and 06.
- **Layer 2 — IBVS visual loop (STRETCH).** Camera-in-the-loop servoing with an RL-tuned image
  Jacobian. Section 04.
- **Layer 3 — Sim-to-real (OPTIONAL).** Run the trained policy on the physical UR5e over ROS 2.
  Section 05.

**Golden rule:** never let Layer 2/3 work put Layer 1 at risk.

---

## The frozen software stack (what you must match)

Replicating the thesis means matching these versions. Blackwell GPUs (RTX 50-series) in
particular force some of these choices — see `01_Environment_Setup.md` for why.

| Component | Exact choice |
|-----------|--------------|
| GPU | NVIDIA RTX 5090 (Blackwell, `sm_120`) |
| NVIDIA driver | 580.x (must be 570+ for Blackwell) |
| Simulator | Isaac Sim **5.0.0** (frozen) |
| RL framework | Isaac Lab **2.3.0** — pinned to the **v2.3.0 tag**, not the branch |
| Python | 3.11 (conda env named `isaaclab`) |
| PyTorch | 2.7.0 + CUDA 12.8 (`cu128` wheels) — required for Blackwell |
| RL trainer | `rsl_rl` 3.0.1 (PPO baseline **and** our cPPO share it) |
| Vision (Layer 2) | YOLOv8, eye-in-hand RGB-D |
| Real robot (Layer 3) | ROS 2 Humble + Universal_Robots_ROS2_Driver |

---

## Where the real work lives (map of the repo)

This documentation *describes* the project; the project itself lives in these folders:

- `ur5_grasp/` — the thesis code package (robot config, environment, safety costs, cPPO,
  training scripts). Git-tracked.
- `IsaacLab/` — the upstream Isaac Lab clone (large, **not** committed; you clone it yourself).
- `logbook/` — the developer's private working notes (`00_INDEX.md`, per-module files) and the
  `run_log.md` daily timeline. This documentation is the *cleaned-up, beginner-facing* version of
  those notes.
- `results/` — result tables and figures for the write-up.
- `Thesis_Documentation/` — **you are here.**

If you are the author continuing the thesis: keep working in `logbook/` + `run_log.md` as before,
then fold anything a beginner would need into these pages and add a line to `09_Changelog.md`.
