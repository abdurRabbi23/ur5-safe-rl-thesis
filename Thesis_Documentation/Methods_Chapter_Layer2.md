# Methodology — Image-Based Visual Servoing for the UR5e (Layer 2)

**Status:** ✅ Draft (2026-07-25) · Thesis-book chapter prose · **Layer:** 2 (stretch)
**Scope:** the classical monocular IBVS baseline (camera, detection, self-measured image Jacobian, and
proportional servo) that the RL-tuned image Jacobian of the following chapter is compared against.
Formatting note: prose draft for the thesis book (Times New Roman 14, justified, 1.25 spacing when
typeset; tables and figures centred with centred captions). Numbers verified against
`ur5_grasp/scripts/ibvs_servo.py` and the recorded runs of 2026-07-25.

---

## 1. Motivation and scope

The Layer 1 policy observes the cube's pose directly, which isolates the safe-reinforcement-learning
contribution from perception but does not correspond to a physically realisable sensor. Layer 2
replaces that privileged observation with an eye-in-hand camera and closes the control loop in the
image plane, a scheme known as image-based visual servoing (IBVS). In IBVS the controller does not
estimate the object's three-dimensional pose; it drives an image feature — here the pixel centroid of
the cube — toward a desired location in the frame, mapping the pixel error to end-effector motion
through an *image Jacobian*. This chapter defines the classical monocular baseline: the camera model
(Section 2), the appearance-based detector (Section 3), the self-measured image Jacobian (Section 4),
and the servo law with its mapping to joint motion (Section 5). The experimental configuration and the
baseline's measured behaviour are reported in Sections 6 and 7, and the identified limitation and its
relation to the RL-tuned extension are discussed in Section 8. Consistent with the three-layer scope,
all Layer 2 code is additive and does not modify the Layer 1 environment or policy.

A deliberate hardware decision constrains the design: the camera is monocular RGB, with no depth
channel, so as to match the single webcam intended for the Layer 3 hardware transfer. The consequent
absence of measured depth is not incidental — the unknown feature depth is precisely the quantity the
RL-tuned image Jacobian of the next chapter is intended to compensate for, and the monocular setting
matches the classical baseline of Khan (2026).

## 2. Eye-in-hand camera

An RGB camera is rigidly mounted on the arm's third wrist link and injected into the play environment
at run time, so that the Layer 1 environment definition is untouched. The plain `Camera` sensor is
used rather than the tiled variant, which hangs on the Blackwell GPU under the frozen Isaac Sim
version. The sensor renders a 320×240 image through a pinhole model (18 mm focal length, 20.955 mm
horizontal aperture), and a dome light is added so the otherwise unlit headless scene is visible; the
environment's debug-visualisation markers are disabled so that they cannot enter the frame or mislead
the detector.

The mount pose was not known a priori and had to be recovered empirically, because the natural first
guess was wrong in an instructive way. A camera placed at the fingertips is buried inside the gripper
mesh and renders black; moving it outward along the wrist axis to clear the mesh, but keeping it
aimed back at the grasp point, produces the opposite failure — the lens then looks straight back at
the gripper and never sees the workspace. The correct geometry was established by instrumenting the
simulator to report the cube's position in the wrist frame across a sweep of candidate mounts and arm
poses (`mount_finder.py`). That measurement showed the cube lying along the wrist's positive-z axis at
the servo pose, and the mount was accordingly fixed beside the gripper at `(0.06, 0, 0)` m in the
wrist frame, oriented to look along wrist +z at the grasp region. With this mount the cube is framed
cleanly against the table, as intended for an approaching eye-in-hand view.

## 3. Appearance-based cube detection

The single image feature servoed upon is the cube's centroid, obtained by an appearance-based detector
that requires no prior knowledge of the cube's colour. The DexCube asset presents bright,
multi-coloured faces, whereas the table, the manipulator, and the background are all achromatic;
converting each pixel to its colour saturation therefore separates the cube from the scene by a simple
threshold. To be robust to isolated coloured pixels and to any second coloured object that might enter
the frame, the detector retains only the largest connected component of the saturated mask and returns
its pixel centroid together with its area. The area additionally serves as a coarse proxy for range,
since a nearer object subtends more pixels; this proxy is used later as a diagnostic of unwanted
approach motion.

## 4. Self-measured image Jacobian

The image Jacobian `J` relates a small motion of the camera in its own image plane to the resulting
shift of the feature centroid, `ds = J·dc`, where `dc` is the two-component camera-plane displacement
and `ds` the corresponding pixel displacement. Rather than assume analytic intrinsics and a camera
convention — both of which proved error-prone in preliminary work — the controller estimates `J`
directly by finite differences at the start pose. It resets the arm to the start configuration,
commands a small displacement along each of the two camera-plane axes in turn, and for each measures
the pixel shift of the centroid together with the *actual* camera displacement. The latter is computed
from the wrist link's articulation state and the fixed mount offset, because the camera sensor's own
world-pose buffer was found to lag during rapid motion and to report near-zero displacement, which had
corrupted an earlier estimate. Stacking the two measured pairs and solving the resulting 2×2 system
yields `J`; because the estimate uses the measured rather than the commanded displacement, it tolerates
the arm not moving exactly along the commanded axis. The measured Jacobian is consistently
well-conditioned, with a determinant of order 2×10⁶, and it is re-measured periodically during
servoing so that it tracks the slowly changing viewpoint.

## 5. Servo law and mapping to joint motion

The control objective is to bring the measured centroid `s` to the image centre `s*`. A proportional
image-plane command is formed by inverting the measured Jacobian,

    dc = −λ · J⁻¹ · (s − s*),

with a small gain λ and the step bounded so that each correction remains in the linear regime in which
`J` was measured. The image-plane command is realised on the six-degree-of-freedom arm by mapping it
to a Cartesian velocity of the wrist and solving for joint velocities through the arm's geometric
Jacobian. To keep the eye-in-hand view stable the command is issued as a full spatial twist whose
linear part is the desired camera translation and whose angular part is zero, so that the wrist
translates without rotating, and whose vertical component is suppressed so that the camera does not
change height; the joint velocities are obtained by damped least squares, which bounds the response in
any ill-conditioned direction, and are capped per step. The per-step pixel error is logged, and a
guard halts the loop if the feature nears the frame edge or its apparent area grows sharply, the latter
indicating unwanted approach.

## 6. Experimental configuration

For a repeatable baseline the environment's per-reset object randomisation is frozen and the cube is
spawned at a fixed position, `(0.56, 0.16, 0.055)` m, chosen so that it is framed centrally in the
wrist camera at the arm's ready pose; every run therefore begins from an identical, well-framed state
with the centroid offset from the image centre by a controlled amount. The arm is held at its ready
configuration during servoing. Each run records the start centroid and error, the measured image
Jacobian, the arm-Jacobian condition number at the servo pose, the per-step error trajectory, and
annotated frames of the initial and final views for inspection.

## 7. Results

The pipeline functions end to end. The eye-in-hand camera renders and the appearance detector locates
the cube robustly once the mount is correctly placed; the image Jacobian is measured successfully and
is well-conditioned. The proportional servo **reduces the centroid error reproducibly from
approximately 43 pixels at the start to approximately 20 pixels — a reduction of about one half — on
every run**, demonstrating that the closed image-plane loop moves the arm in the correct sense. The
servo does not, however, drive the error to zero: after roughly ten to thirty control steps the view
destabilises and the feature is lost.

The cause was localised rather than left as a tuning failure. The arm-Jacobian condition number at the
servo pose is approximately nine, so the configuration is far from singular and the arm is physically
capable of the required translation. Logging the orientation of the optical axis during servoing shows
it drifting steadily — the world-vertical component of the camera's viewing axis moving from about
−0.949 to −0.808 over the run — which corresponds to the camera slowly pitching toward the table; this
tilt increases the cube's apparent size and ultimately carries the feature out of the usable frame.
The same behaviour was observed under three distinct servo laws (Jacobian pseudo-inverse, damped least
squares, and Jacobian transpose), which establishes that the instability arises in the arm-motion
layer rather than in the image controller.

## 8. Discussion and link to the RL-tuned extension

The residual limitation is therefore a control-implementation issue: holding the wrist orientation
exactly while translating it through incremental joint-position targets, with a least-squares mapping
that mixes translational and rotational residuals, is not orientation-tight, and the small leaked
rotation accumulates into the observed pitch. Removing it requires a resolved-rate or operational-space
velocity controller that enforces the orientation constraint strictly, or an explicit re-levelling of
the wrist at each step; this is a controller-design task rather than a matter of gain selection, and it
is identified here as the concrete next step for full convergence. An alternative that avoids the
problematic configuration altogether would select the servo pose by an image-motion manipulability
criterion.

This limitation does not undermine the layer's purpose. The classical baseline is intended to
establish the achievable behaviour of a fixed, analytically-motivated image Jacobian, and it does so:
a well-conditioned but imperfect controller that halves the feature error before model and control
imperfections dominate. The RL-tuned image Jacobian of the following chapter — a learned correction
blended with the classical controller through fuzzy state coding and a mixture parameter — is precisely
the mechanism intended to absorb such unmodelled coupling and the unknown feature depth, so the
baseline's shortfall defines exactly the gap the learned component is asked to close.
