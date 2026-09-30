# VALIDATION — DD2365_FEniCSx

Records of legacy smoke tests (FEniCSx port vs legacy FEniCS/mshr) and numerical verification.
All runs: fenicsx-0.11 conda env (python=3.12, dolfinx=0.11.0), serial, Apple Silicon M5.

---

## Legacy smoke tests

Each entry lists the canonical block versions active at the time of the comparison run.
"Legacy" refers to the original FEniCS/mshr implementation in `johanhoffman/DD2365`.

### Poisson_equation.ipynb

**Canonical blocks (current):** bootstrap v1, gmsh_rect_minus_circles v5, refine_cells v2,
plot_helpers v3, export_xdmf v2, tag_boundaries v1  
**CI validated:** 2026-09-30 (PR \#12)  
No numeric QoI comparison records.

---

### template-report-Stokes.ipynb

**Canonical blocks (current):** bootstrap v1, gmsh_rect_minus_circles v5, refine_cells v2,
plot_helpers v3, export_xdmf v2, tag_boundaries v1  
**Test date:** 2026-09-24 (initial port)

Poiseuille verification (no holes, L=4, H=2, ν=1):

| Quantity | FEniCSx (P2/P1, MUMPS) | Analytic (8νL/H²) |
|---|---|---|
| Δp | 7.97 | 8.0 |
| error | 0.4% | — |

---

### template-report-Stokes-AMR.ipynb

**Canonical blocks at test time:** bootstrap v1, gmsh_rect_minus_circles v2,
refine_cells v2, plot_helpers v2, export_xdmf v2, tag_boundaries v1  
**Test date:** 2026-09-24 (initial port); CI re-validated at v5 2026-09-30 (PR \#12)  
**Domain:** L=H=4, circle (0.5, 2.0, r=0.2), resolution=32  
**QoI:** drag on circle (primal P2/P1, MUMPS; adjoint P3/P2)

| | FEniCSx (gmsh v2) | Legacy (mshr, FEniCS) |
|---|---|---|
| Init cells | 2905 | 3112 |
| ‖u‖ | 2.950 | 2.947 |
| ‖p‖ | 12.567 | 12.374 |
| ‖φ‖ (adjoint vel) | 0.752 | 0.744 |
| ‖θ‖ (adjoint p) | 10.076 | 9.860 |
| Cells marked | 309 | 315 |
| Cells after refinement | 3945 | 4164 |

Velocity and pressure norms agree within ≈2%. `tot_err` (scalar residual integral) differs
in sign and magnitude between implementations due to mesh and solver differences (legacy uses
default FEniCS Krylov; FEniCSx uses MUMPS); it is not a reliable cross-implementation comparison metric.

Note: at v5 (segments=32) the circle polygon has 32 sides vs ≈8 at v2 (mshr auto-rule for L=H=4).
Velocity norms change by ≤1.6% on v5 migration; CI validates all notebooks pass at v5.

---

### Convection-Diffusion-NSE.ipynb

**Canonical blocks at test time:** bootstrap v1, gmsh_rect_minus_circles v2,
refine_cells v2, plot_helpers v2, tag_boundaries v1, xdmf_series v1  
**Test date:** 2026-09-24 (initial port); CI re-validated at v5 2026-09-30 (PR \#12)  
**Domain:** L=4, H=2, circle (1.0, 1.0, r=0.2), resolution=32, ν=4e-3, ε=1e-2, U_in=1

| t | cells | dt | steps | ‖u‖ | ‖p‖ | ‖w‖ | ∫w |
|---|---|---|---|---|---|---|---|
| 2.0 | 2392 | 0.035 | 57 | 3.009 | 0.649 | 0.386 | 0.398 |
| 30.0 | — | — | 869 | — | — | — | — |

Note: pressure norms change by ≤16% on v5 migration (expected: 10→32 polygon sides
changes near-wake dynamics at this resolution).

---

### template-report-Navier-Stokes.ipynb

**Canonical blocks (current):** bootstrap v1, gmsh_rect_minus_circles v5, refine_cells v2,
plot_helpers v3, tag_boundaries v1, xdmf_series v1  
**CI validated:** 2026-09-30 (PR \#12)  
No numeric QoI comparison records.

---

## Verification — Schäfer-Turek 2D-1

**Notebook:** `verification/schafer-turek-2d1.ipynb`  
**Run date:** 2026-09-30  
**Canonical blocks:** bootstrap v1, gmsh_rect_minus_circles v5, tag_boundaries v1, plot_helpers v3  
**Reference:** Schäfer & Turek (1996), 2D-1 steady: C_D = 5.57953523384, C_L = 0.010618948146, Δp = 0.11752016697  
**Steady-state criterion:** ‖u1−u0‖/dt/‖u1‖ < 1e−6 (coefficient-vector Euclidean norm)  
**Scheme:** GLS stabilized P1/P1 NS, fractional step, dt = 0.5·h_min  
**Domain:** [0, 2.2]×[0, 0.41], cylinder (0.2, 0.2, r=0.05), ν=1e-3, U_m=0.3

| lvl | res | segs | cells | h_min | dt | steps | t_stop | C_D | C_D err | C_L | C_L err | Δp | Δp err | wall |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 32 | 32 | 1236 | 0.01197 | 0.00599 | 3265 | 19.54 | 6.113137 | 9.6% | 0.34555 | 3154% | 0.12212 | 3.9% | 54 s |
| 2 | 64 | 64 | 4652 | 0.00515 | 0.00258 | 7873 | 20.29 | 5.725066 | 2.6% | −0.03532 | 433% | 0.11989 | 2.0% | 508 s |
| 3 | 128 | 128 | 18504 | 0.00245 | 0.00123 | — | — | — | — | — | — | — | — | stopped† |

† Level 3 stopped after 5 steps: wall-time projection of 116 min exceeded the 1-hour limit.

**Notes:**
- C_D and Δp converge toward the reference values (9.6% → 2.6% and 3.9% → 2.0%), consistent with
  first-order accuracy of P1 elements under mesh halving.
- C_L has large relative errors because the reference C_L = 0.0106 is nearly zero: the cylinder is
  offset by only 0.005 from the channel centreline (y=0.2 vs centreline y=0.205), making C_L a
  near-cancellation quantity at P1 resolution. This is an expected property, not a formula error.
- Steady-state criterion converges at t ≈ 20 for both levels (≈1.8 convective time units post-transient).
