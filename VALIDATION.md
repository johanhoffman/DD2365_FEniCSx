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

#### QoIs at T=2

| Quantity | FEniCSx port | Legacy FEniCS | diff |
|---|---|---|---|
| ‖u1‖ | 5.069609 | 5.059144 | +0.21% |
| ‖p1‖ | 0.759397 | 0.709063 | +7.1% |
| cells | 11348 | — | — |
| dt | 0.024364 | — | — |
| steps | 82 | — | — |
| full-T=10 wall | 77.5 s (serial, M5) | — | — |

Velocity agrees to 0.21% of legacy. Pressure differs ~7% from legacy at T=2; dt ruled out (legacy-dt run: ||p1||=0.758601, 0.1% change); mesh sensitivity demonstrated (scratch tests below).

#### Mesh sensitivity scratch tests (report only, T=2)

| run | segments | resolution | ‖u1‖ | ‖p1‖ | cells | dt | Δ‖p1‖ vs default |
|---|---|---|---|---|---|---|---|
| default | 32 | 64 | 5.069609 | 0.759397 | 11348 | 0.024364 | — |
| (a) mshr segs | 19 | 64 | 5.068824 | 0.752327 | 11265 | 0.025679 | −0.9% |
| (b) res=90 | 32 | 90 | 5.064803 | 0.734759 | 22278 | 0.016498 | −3.2% |
| legacy (ref) | ~19 (mshr) | ~64 | 5.059144 | 0.709063 | — | — | — |

(a) mshr segments=19 vs default 32: pressure changes only 0.9% → polygon approximation is not the main factor.  
(b) resolution=90 vs default 64: pressure changes 3.2% — mesh sensitivity demonstrated at this resolution range. The additional ~4% gap between (b) and legacy is consistent with the different mesh generators (gmsh graded vs mshr Delaunay) producing different effective near-cylinder refinement.

---

### Shallow-Water-Equations

Legacy: `DD2365/Shallow-Water-Equations.ipynb` (FEniCS 2019.1, mshr)  
Port: `DD2365_FEniCSx/Shallow-Water-Equations.ipynb` (dolfinx 0.11.0, gmsh)

#### Diff table

| Feature | Legacy FEniCS | FEniCSx port |
|---|---|---|
| Mesh API | `mshr.generate_mesh` | `gmsh_rect_minus_circles v6` |
| BC API | `DirichletBC(V.sub(i), val, subdomain)` | `locate_dofs_topological + dirichletbc` |
| BC: u_x=1 inlet | `DirichletBC(V.sub(0), 1.0, dbc_left)` | `_bc(V.sub(0), 1.0, tag=1)` |
| BC: u_y=0 inlet | `DirichletBC(V.sub(1), 0.0, dbc_left)` | `_bc(V.sub(1), 0.0, tag=1)` |
| BC: u_y=0 upper/lower | slip | slip |
| BC: no-slip cylinder | `DirichletBC` | `_bc(V.sub(i), 0.0, tag=5)` |
| BC: w inlet | `DirichletBC(Q, \|sin(t)\|, dbc_left)` | `Constant w_in` updated each step |
| d1 | `2/sqrt(1/dt²+\|u\|²/h²)` | same (UFL) |
| Force | volume form, psi on cyl dofs (V.sub(1) only in legacy) | psi on both components V.sub(0) and V.sub(1) |
| Force sign | `−g·inner(grad(wm1),psi)·dx` (bug) | `+g·inner(grad(wm1),psi)·dx` (corrected) |
| Force sampling | inside nonlinear loop | once per step after nonlinear convergence (authorized deviation) |

#### Scratch check: force sign (T=2, phi=(1,0) drag)

With phi=(1,0) and corrected +g sign: normalized drag at T=2 = **+0.016764** > 0 ✓  
(legacy −g sign would give −0.016764, i.e., negative drag — physically wrong)

#### QoIs at T=2

| Quantity | FEniCSx port | Legacy | diff |
|---|---|---|---|
| ‖u1‖ | 2.287703 | — | — |
| ‖w1‖ | 1.599269 | — | — |
| cells | 2492 | — | — |
| dt | 0.019603 | — | — |
| steps | 102 | — | — |

#### QoIs at T=30

| Quantity | FEniCSx port |
|---|---|
| ‖u1‖ | 2.656588 |
| ‖w1‖ | 2.039469 |
| steps | 1530 |
| wall (serial, M5) | 32.4 s |

---

### template-report-Navier-Stokes-ALE

Legacy: `DD2365/template-report-Navier-Stokes-ALE.ipynb` (FEniCS 2019.1, mshr)  
Port v1 (PR \#19): `DD2365_FEniCSx/template-report-Navier-Stokes-ALE.ipynb` (dolfinx 0.11.0, gmsh)  
Port v2 (ale-elasticity): physics fixes + VTKFile output (see below)

#### Authorized deviation

Legacy prescribes absolute mesh displacement `w(x,t)` and calls `ALE.move(mesh,w)`.  
Port prescribes mesh velocity `beta(x,t)` directly and moves the mesh incrementally by `dt*beta` each step.  
Equivalence: `V_y = amp_y / legacy_dt = 0.01 / 0.032855 ≈ 0.30`.

#### Diff table (v2 — ale-elasticity)

| Feature | Legacy FEniCS | FEniCSx port v2 |
|---|---|---|
| Mesh API | `mshr.generate_mesh` | `gmsh_rect_minus_circles v6` |
| BC API | `DirichletBC` | `locate_dofs_topological + dirichletbc` |
| BC: u_x=1 inlet | `DirichletBC(V.sub(0), 1.0, ...)` | `_bc_vel(uin, 0, V0, left_f)` |
| BC: u_y=0 upper/lower | `DirichletBC(V.sub(i), 0.0, ...)` | slip (u_y=0) |
| BC: p=0 outlet | `DirichletBC(Q, 0.0, dbc_right)` | same |
| BC: cylinder | `DirichletBC(V.sub(i), beta_i, ...)` (split) | `dirichletbc(beta_u, locate_dofs_topological(V,fdim,obj_f))` (one vector BC, authorized) |
| Mesh motion | absolute displacement `w`, `ALE.move(mesh,w)` | mesh velocity `beta`, incremental `dt*beta` (authorized) |
| ALE form convection | `(um1 - w/dt)` | `(um1 - beta_u)` (consistent with Fu) |
| Force convection | absolute fluid velocity (not ALE-relative) | `(um1 - beta_u)` (authorized, ALE-consistent) |
| Force psi | Expression on cyl dofs | psi on both V.sub(0) and V.sub(1) via collapse |
| d1 | `1/sqrt(1/dt²+\|u\|²/h²)` | same (UFL) |
| XDMF output | `XDMFFile` | `dolfinx.io.VTKFile` (PVD per function; captures moving geometry) |
| Min cell vol | not checked | checked each plot step; min > 0 enforced |

#### VTK geometry verification

Scratch run (T=2): max geometry diff between write 1 (t=0.0196) and write 2 (t=0.0392) = **0.00587922 > 0** ✓ — mesh motion is captured in PVD output.

#### QoIs at T=2

| Quantity | v1 (PR \#19) | v2 (ale-elasticity) | notes |
|---|---|---|---|
| ‖u1‖ | 2.963259 | 2.947439 | −0.5% from force/BC physics fix |
| ‖p1‖ | 0.425732 | 0.440773 | +3.5% |
| cells | 2492 | 2492 | — |
| dt | 0.019603 | 0.019603 | — |
| steps | 102 | 102 | — |
| min cell vol | 4.58e−4 | 4.58e−4 | > 0 throughout ✓ |

#### QoIs at T=30 (v2)

| Quantity | FEniCSx port v2 |
|---|---|
| ‖u1‖ | 3.025436 |
| ‖p1‖ | 0.590812 |
| steps | 1530 |
| min cell vol (run min) | 4.46e−4 |
| wall (serial, M5) | 54.6 s |
| force range t∈[15,30] | min=1.465754, max=2.130500 |

---

### template-report-Elasticity

New notebook (no legacy FEniCS counterpart — first port).  
Port: `DD2365_FEniCSx/template-report-Elasticity.ipynb` (dolfinx 0.11.0, gmsh)

**Canonical blocks:** bootstrap v1, gmsh_rect_minus_circles v6, refine_cells v1, tag_boundaries v1, plot_helpers v3  
**Domain:** L=4, H=2, three circles: (1.5, 0.5, 0.2), (0.5, 1.0, 0.2), (2.0, 1.5, 0.2), resolution=32, no_levels=0  
**Spaces:** P1 vector (Lagrange deg=1, shape=(2,)) for displacement `d`  
**Material:** E=1e10, ν=0.3, μ=E·0.5/(1+ν), λ=ν·E/((1+ν)(1−2ν))  
**BCs:** outer walls (tags 1–4): u=0; objects (tag 5): u_x=0.5, u_y=0  
**Solver:** CG + BoomerAMG (SPD system; legacy: bicgstab/default)  
**Mesh move:** displacement d applied to geometry via dofmap→geometry mapping (same as NS-ALE)

#### Diff table

| Feature | Legacy (no counterpart) | FEniCSx port |
|---|---|---|
| Library | n/a | dolfinx 0.11.0 |
| Mesh | n/a | `gmsh_rect_minus_circles v6`, res=32 |
| Spaces | n/a | P1 vector `basix.ufl.element("Lagrange",...,shape=(2,))` |
| KSP | n/a | CG + BoomerAMG (SPD) |
| Mesh move | n/a | dof→geometry map (same as NS-ALE `move_mesh`) |

#### QoIs

| Quantity | FEniCSx port |
|---|---|
| ‖d‖ | 0.657501 |
| cells | 2640 |
| min cell vol (deformed) | 1.57e−4 |

---

### PeriodicBC.ipynb

Legacy: `DD2365/PeriodicBC.ipynb` (FEniCS 2019.1, `constrained_domain`)  
Port: `DD2365_FEniCSx/PeriodicBC.ipynb` (dolfinx 0.11.0, algebraic restriction)

**Canonical blocks:** bootstrap v1, periodic_restriction v2, time_step v1, plot_helpers v3, xdmf_series v1  
**Domain:** L=2, H=1, structured rectangle `create_rectangle` 64×32 cells, `DiagonalType.right`  
**Spaces:** P1 vector (velocity) + P1 scalar (pressure), both periodic in x  
**BCs:** u=(−1,0) at y=0; u=(+1,0) at y=H; x-periodicity via restriction matrix  
**Solver:** bcgs+ILU (velocity), bcgs+BoomerAMG (pressure); reduced system via P^T A P (MatPtAP)  
**Pressure regularization:** d3 = 1e−4·hmin (mass term; no Dirichlet pressure BC)

#### Authorized deviation

Legacy uses `constrained_domain=PeriodicBoundary()` (FEniCS built-in). DOLFINx has no native periodic BC support. Port implements periodicity via hand-built restriction matrix P (n\_full × n\_red), which algebraically identifies right-boundary DOFs with left-boundary DOFs. The reduced system P^T A P x\_r = P^T b is assembled by `ptap` (PETSc MatPtAP) each nonlinear iteration and solved in the reduced space; full solution recovered by P x\_r.

#### Diff table

| Feature | Legacy FEniCS | FEniCSx port |
|---|---|---|
| Mesh | `RectangleMesh(Point(0,0),Point(L,H),64,32)` | `create_rectangle(...,DiagonalType.right)` |
| Spaces | `VectorFunctionSpace(...,constrained_domain=PB)` | `functionspace(msh,P1v)` + periodic restriction |
| Periodic BC | `PeriodicBoundary` + `constrained_domain` | restriction matrix P (n\_full × n\_red); `ptap` per iter |
| Dirichlet BCs | `DirichletBC(V,(−1,0),lower)` etc. | applied in reduced system via `zeroRowsColumns` |
| Assemble | `assemble(au); bc.apply(Au,bu)` | `assemble_matrix(A_u,...,bcs=[])`; `reduce_system`; `apply_dirichlet_reduced` |
| KSP | `solve(Au,u1,bu,"bicgstab","default")` | bcgs+ILU (vel), bcgs+BoomerAMG (press) |
| d1, d2 | constant then overridden by residual form | residual-based UFL (what is actually used) |
| d3 | `1e-4*mesh.hmin()` | `1e-4*hmin` (Constant) |
| XDMF output | `File("results-Euler/u.pvd")` | `xdmf_series v1` (authorized deviation) |

#### Scratch checks (serial, Apple Silicon M5)

Periodicity at T=2: max\|u(0,y)−u(L,y)\| = **0.00e+00** (exact, by construction) ✓  
Pressure periodicity: max\|p(0,y)−p(L,y)\| = **0.00e+00** ✓  
x-independence at T=2: max variation of u\_x along x-lines = **3.0e−6** (floating-point noise) ✓

#### QoIs at T=2

| Quantity | FEniCSx port | Legacy FEniCS | diff | Analytic (erfc) | diff |
|---|---|---|---|---|---|
| ‖u1‖ | 0.347487 | 0.3474876 | 0.001% | 0.3439 | +1.1% |
| ‖p1‖ | 0.000000 | — | — | 0 | ✓ |
| cells | 4096 | — | — | — | — |
| dt | 0.011049 | — | — | — | — |
| steps | 181 | — | — | — | — |
| wall (serial, M5) | 8.5 s | — | — | — | — |

The +1.1% deviation from the analytic erfc solution is consistent with ~3 cells per wall boundary layer at this resolution.

#### QoIs at T=80

| Quantity | FEniCSx port |
|---|---|
| ‖u1‖ | 0.795775 |
| ‖p1‖ | 0.000000 |
| steps | 7240 |
| wall (serial, M5) | 340.8 s |

At T=80 the flow is laminar (plane Couette flow is linearly stable; zero initial condition).
