# 04 — Layer 2: Image-Based Visual Servoing (IBVS)

**Status:** ⏳ PLANNED (not started) · **Layer:** 2 (stretch) · **Roadmap:** Weeks 11–13

> This page is a **placeholder outline** so the documentation map is complete. It will be filled in
> with real commands and outputs when Layer 2 work begins. Layer 2 starts **only after Layer 1
> (section 03) is signed off** — it must never put the must-pass result at risk.

---

## What Layer 2 is (plain words)

Layer 1 lets the arm read the exact cube position (privileged info). A real robot doesn't get that —
it has a **camera**. **IBVS (Image-Based Visual Servoing)** closes the loop *in the image*: the arm
moves so that the object's appearance in the camera (pixel positions of image features) reaches a
desired target, without ever computing the object's 3D pose. The link from "pixel error" to "how to
move the joints" is the **image Jacobian**.

The thesis contribution here is to **RL-tune the image Jacobian** — using fuzzy state coding and a
mixture parameter β to blend a classical IBVS controller with a learned correction, so servoing
stays accurate near singularities and when features approach the edge of view.

---

## Planned sub-steps (to be documented as they happen)

1. **Camera setup** — eye-in-hand RGB-D. Use the plain **`Camera`** sensor (NOT `TiledCamera`,
   which hangs on Blackwell — see `01_Environment_Setup.md`).
2. **Feature detection** — YOLOv8 to detect the object / image features in the camera frame.
3. **Classical IBVS baseline** — implement the standard image-Jacobian controller; verify it
   servos the arm to a target view in sim.
4. **RL-tuned image Jacobian** — fuzzy state coding + mixture parameter β; train the correction and
   compare against classical IBVS.
5. **Field-of-view constraint** — extend the safety costs so losing the object off-frame becomes a
   monitored/penalised event (ties back to section 03's cost machinery).

---

## Success criterion (to confirm later)

The arm grasps using **only camera input**, and the RL-tuned image Jacobian measurably beats
classical IBVS on servoing accuracy and/or robustness near singular / edge-of-view conditions.

## Key references

Shi 2020 (IBVS + Q-learning); Zhang (fuzzy IBVS). See the thesis proposal for full citations.
