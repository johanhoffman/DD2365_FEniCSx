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

### Brinkman_NSE.ipynb

**Canonical blocks:** bootstrap v1, refine_cells v1, tag_boundaries v1, plot_helpers v3, xdmf_series v1, time_step v1  
**Port date:** 2026-10-01 (PR \#16); time_step v1 added 2026-10-02 (PR \#17)  
**CI validated:** 2026-10-02  
**Domain:** L=4, H=1, rectangular mesh (no holes), resolution=16, ν=1e-2, ν_eff=1e-2  
**Scheme:** GLS P1/P1, fractional step, dt=time_step(msh,1.0)=0.5·hmin

| Quantity | FEniCSx port | Legacy FEniCS | diff |
|---|---|---|---|
| ‖u1‖ at T=2 | 1.917224 | 1.917183 | +0.002% |
| ‖p1‖ at T=2 | 3.358306 | 3.356012 | +0.068% |
| cells | 2048 | — | — |
| dt | 0.044194 | — | — |
| steps | 45 | — | — |

---

## Verification — Schäfer-Turek 2D-1

**Notebook:** `verification/schafer-turek-2d1.ipynb`  
**Run date:** 2026-10-01  
**Canonical blocks:** bootstrap v1, gmsh_rect_minus_circles v6, tag_boundaries v1, plot_helpers v3  
**Reference:** Schäfer & Turek (1996), 2D-1 steady: C_D = 5.57953523384, C_L = 0.010618948146, Δp = 0.11752016697  
**ST96 intervals:** C_D ∈ [5.57, 5.59], C_L ∈ [0.0104, 0.0110], Δp ∈ [0.1172, 0.1176]  
**Steady-state criterion:** ‖u1−u0‖/dt/‖u1‖ < 1e−6 (coefficient-vector Euclidean norm)  
**Scheme:** GLS stabilized P1/P1 NS, fractional step, dt = 0.5·h_cyl (min cell size at cylinder)  
**Mesh:** graded (v6): dist_min=0.5D=0.05 m, dist_max=3D=0.30 m  
**Domain:** [0, 2.2]×[0, 0.41], cylinder (0.2, 0.2, r=0.05), ν=1e-3, U_m=0.3  
**Force (primary):** volume form (Green's formula, ψ=e_D on cylinder dofs)  
**Force (secondary):** surface stress ∫(σ·n)·e dS (this notebook only)

### Volume-form results

| lvl | res | segs | cells | h_cyl | h_D | dt | steps | t_stop | C_D | \|ΔC_D\| | ✓ | C_L | f-sc | ✓ | Δp | \|ΔΔp\| | ✓ | wall |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 32 | 32 | 2751 | 0.00980 | 0.01120 | 0.00490 | 3876 | 18.996 | 5.60199 | 0.02245 | ✗ | −0.00743 | 0.00324 | ✗ | 0.11811 | 0.00059 | ✗ | 142 s |
| 2 | 64 | 64 | 10716 | 0.00491 | 0.00550 | 0.00245 | 7910 | 19.406 | 5.59079 | 0.01125 | ✗† | 0.01077 | 0.00003 | ✓ | 0.11653 | 0.00099 | ✗ | 7168 s |
| 3 | 128 | 128 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | running‡ |

f-sc = \|ΔC_L\| / C_D_ref (force-vector scale)  
† C_D = 5.5908, 0.079‰ above ST96 upper bound 5.59  
‡ L3 started 2026-10-01, expected ~8 h; table will be updated when complete

**Convergence rates L1→L2 (log₂ |e_coarse/e_fine|):**

| QoI | rate | note |
|---|---|---|
| C_D | +1.00 | first-order ✓ |
| C_L (f-sc) | n/a | sign change L1→L2; monotone regime begins at L2 |
| Δp | −0.75 | non-monotone; L1 overshoots, L2 undershoots |

### Surface stress results (secondary)

| lvl | C_D_surf | \|ΔC_D\| | C_L_surf | f-sc |
|---|---|---|---|---|
| 1 | 5.39269 | 0.18685 | −0.08149 | 0.01651 |
| 2 | 5.47386 | 0.10568 | 0.00199 | 0.00155 |

### Notes

- **C_D** converges at rate ≈ 1.0, consistent with first-order P1 elements. L2 value is 0.079‰ above the ST96 upper bound; L3 expected to enter the interval.
- **C_L** at L1 is negative due to insufficient wake resolution on the graded coarse mesh; the graded fine zone (dist_max=3D) is necessary but not sufficient at res=32. At L2 the wake is resolved and C_L ∈ [0.0104, 0.0110] ✓. The sign change between L1 and L2 makes the L1→L2 rate meaningless.
- **Δp** shows non-monotone convergence (L1 overshoots, L2 undershoots). Characteristic of GLS P1/P1 stabilization on coarse meshes; pressure convergence expected to become monotone at L3.
- **Surface stress** is less accurate than the volume form at both levels, as expected for P1 elements (differentiating the velocity amplifies traction errors). The volume form is the authoritative estimate.
- L2 wall time: 7168 s (≈ 2 h) on MacBook M5 Pro. The graded fine zone (dist_max=3D) increases cell count to 10716 vs 4652 for the ungraded mesh.

### Diagnosis variants (CANDIDATE — not adopted)

The following variants were tested during diagnosis (branch `st-2d1-diagnosis`) but rejected:

| CANDIDATE | description | outcome |
|---|---|---|
| dt×2 | dt = h_cyl (instead of 0.5·h_cyl) | no meaningful improvement in C_L; rejected |
| steady-d1 | d1 = h/\|u\| (instead of standard) | unstable at L2; rejected |

---

### Turbulence-Model.ipynb

**Canonical blocks:** bootstrap v1, gmsh_rect_minus_circles v6, refine_cells v1, tag_boundaries v1, plot_helpers v3, xdmf_series v1, time_step v1  
**Port date:** 2026-10-01 (PR \#17); projection + force-sampling corrections 2026-10-02  
**Domain:** L=6, H=4, cylinder (1.5, 2.0, r=0.3), resolution=64, no_levels=0, ν=4×10⁻³  
**Scheme:** GLS P1/P1, fractional step, 5 nonlinear iterations per step, dt=time_step(msh,1.0)=0.5·hmin  
**Stabilization:** d1=4/√(1/dt²+|u|²/h²), d2=2h|u|; Smagorinsky C_t=1e-2; skin friction α=C_α/h, C_α=100 on cylinder tag 5  
**Run environment:** fenicsx-0.11 conda env, serial, Apple Silicon M5

#### Legacy → FEniCSx diff table

| Item | Legacy (FEniCS/mshr) | FEniCSx 0.11 |
|---|---|---|
| Library | dolfin 2019 + mshr | dolfinx 0.11.0 |
| Mesh | `generate_mesh(Rectangle−Circle, 64)` | `gmsh_rect_minus_circles v6`, res=64 |
| Spaces | `VectorFunctionSpace("P",1)` / `FunctionSpace("P",1)` | `basix.ufl.element("Lagrange",...,shape=(2,))` |
| Assemble | `assemble()` + `solve(..., "bicgstab", "default")` | `assemble_matrix/vector`, PETSc KSP bicgs+ILU / bicgs+boomeramg |
| BC API | `DirichletBC(V.sub(i), val, subdomain)` | `locate_dofs_topological + dirichletbc` |
| BC: u_x=1 inlet | `DirichletBC(V.sub(0), 1.0, dbc_left)` | `_bc(V.sub(0), 1.0, tag=1)` |
| BC: u_y=0 inlet | `DirichletBC(V.sub(1), 0.0, dbc_left)` | `_bc(V.sub(1), 0.0, tag=1)` |
| BC: u_y=0 upper | `DirichletBC(V.sub(1), 0.0, dbc_upper)` | `_bc(V.sub(1), 0.0, tag=4)` |
| BC: u_y=0 lower | `DirichletBC(V.sub(1), 0.0, dbc_lower)` | `_bc(V.sub(1), 0.0, tag=3)` |
| BC: cylinder | none (skin friction penalty) | none (skin friction penalty) |
| BC: p=0 outlet | `DirichletBC(Q, 0.0, dbc_right)` | `_bc(Q, 0.0, tag=2)` |
| d1 | `4.0/sqrt(pow(1/dt,2)+pow(\|u\|/h,2))` | `4.0/ufl.sqrt((1/dt_c)²+(u_mag/h_c)²)` |
| d2 | `2.0*h*u_mag` | `2.0*h_c*u_mag` |
| Smagorinsky | `C_t*h²*sqrt(inner(grad um1,grad um1))*inner(grad um,grad v)*dx` | same (UFL) |
| Skin friction | `alpha*inner(dot(um,n),dot(v,n))*ds(5)` | same (UFL, `ds_m(5)`) |
| Force | volume form inside nonlinear loop (5× per step), psi on cyl dofs | volume form, psi on cyl dofs; sampled once per step after nonlinear convergence (authorized deviation, same as template-report-Navier-Stokes) |
| Triple decomp | `TensorFunctionSpace("P",1)` + `vertex_to_dof_map` | L2 projection via `_project_comp` (same as template-report-Navier-Stokes) |
| `new_grad` | `np.zeros((3,3))` float (fixed) | `np.zeros((3,3))` float |
| Plots | FEniCS built-in `plot()` | `plot_scalar / plot_vector` (plot_helpers v3) |
| XDMF output | `XDMFFile` write-per-step | `xdmf_series v1` |
| no_levels | 0 | 0 |

#### QoIs at T=2 (no legacy reference; FEniCS/mshr cannot run on current system)

| Quantity | FEniCSx (P1/P1, bicgs+ILU) |
|---|---|
| ‖u1‖ | 5.069609 |
| ‖p1‖ | 0.759397 |
| cells | 11348 |
| dt | 0.024364 |
| steps | 82 |
| full-T=10 wall | 77.5 s (serial, M5; concurrent with ST L3) |

