# DD2365 FEniCSx Notebooks

FEniCSx port of the [DD2365 Advanced Computation in Fluid Mechanics](https://www.kth.se/student/kurser/kurs/DD2365) course notebooks (KTH Royal Institute of Technology).

Original FEniCS versions: [johanhoffman/DD2365](https://github.com/johanhoffman/DD2365).

[![CI](https://github.com/johanhoffman/DD2365_FEniCSx/actions/workflows/ci.yml/badge.svg)](https://github.com/johanhoffman/DD2365_FEniCSx/actions/workflows/ci.yml)

---

## Notebooks

| Notebook | Open in Colab |
|---|:---:|
| `Poisson_equation.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/johanhoffman/DD2365_FEniCSx/blob/main/Poisson_equation.ipynb) |
| `template-report-Stokes.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/johanhoffman/DD2365_FEniCSx/blob/main/template-report-Stokes.ipynb) |
| `template-report-Stokes-AMR.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/johanhoffman/DD2365_FEniCSx/blob/main/template-report-Stokes-AMR.ipynb) |
| `template-report-Navier-Stokes.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/johanhoffman/DD2365_FEniCSx/blob/main/template-report-Navier-Stokes.ipynb) |
| `template-report-Navier-Stokes-ALE.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/johanhoffman/DD2365_FEniCSx/blob/main/template-report-Navier-Stokes-ALE.ipynb) |
| `template-report-Elasticity.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/johanhoffman/DD2365_FEniCSx/blob/main/template-report-Elasticity.ipynb) |
| `Brinkman_NSE.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/johanhoffman/DD2365_FEniCSx/blob/main/Brinkman_NSE.ipynb) |
| `Convection-Diffusion-NSE.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/johanhoffman/DD2365_FEniCSx/blob/main/Convection-Diffusion-NSE.ipynb) |
| `Euler-equations-compressible-flow.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/johanhoffman/DD2365_FEniCSx/blob/main/Euler-equations-compressible-flow.ipynb) |
| `PeriodicBC.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/johanhoffman/DD2365_FEniCSx/blob/main/PeriodicBC.ipynb) |
| `Turbulence-Model.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/johanhoffman/DD2365_FEniCSx/blob/main/Turbulence-Model.ipynb) |
| `Shallow-Water-Equations.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/johanhoffman/DD2365_FEniCSx/blob/main/Shallow-Water-Equations.ipynb) |

All 12 notebooks run in CI (FAST mode, `DD2365_FAST=1`).

---

## Setup

### Google Colab (zero-install)

Click an **Open in Colab** badge above.
The first cell installs FEniCSx (dolfinx 0.11, FEM-on-Colab release-real) and gmsh automatically.
Select **Runtime → Run all**.

### Local: conda environment (portable, recommended for other platforms)

```bash
conda env create -f environment.yml   # creates env named fenicsx-0.11
conda activate fenicsx-0.11
bash tools/install_hooks.sh           # installs pre-commit hook
jupyter notebook
```

### Local: exact reproduction (osx-arm64 only)

To reproduce results exactly on macOS Apple Silicon using the reference lockfile:

```bash
conda create -n fenicsx-0.11-py312 --file env-osx-arm64.lock
conda activate fenicsx-0.11-py312
bash tools/install_hooks.sh
jupyter notebook
```

`environment.yml` is the portable spec for CI and other platforms.
`env-osx-arm64.lock` pins every transitive dependency and reproduces the exact environment used to generate the results in `VALIDATION.md`.

**Pinned versions:**

| Package | Version |
|---|---|
| dolfinx | 0.11.0 |
| basix | 0.11.0 |
| ffcx | 0.11.0 |
| ufl | 2026.1.0 |
| petsc4py | 3.25.2 |
| gmsh | 4.15.2 |
| python | 3.12 |

> **Apple Silicon / MUMPS note:** The bootstrap block in every notebook sets `OMP_NUM_THREADS=1`
> before petsc4py import. This is required to avoid MUMPS non-determinism on M-series Macs.

---

## Verification

Quantitative QoI records, convergence tables, and legacy smoke tests are in [`VALIDATION.md`](VALIDATION.md).

Verification notebooks are in [`verification/`](verification/):

| Notebook | Benchmark | Status |
|---|---|---|
| `verification/schafer-turek-2d1.ipynb` | Schäfer-Turek 2D-1 (steady Re=20) | Validated — see VALIDATION.md |
| `verification/schafer-turek-2d2.ipynb` | Schäfer-Turek 2D-2 (unsteady Re=100) | Validated — see VALIDATION.md |
| `verification/mms-poisson.ipynb` | MMS Poisson h-refinement | Validated — see VALIDATION.md |
| `verification/mms-stokes.ipynb` | MMS Stokes h-refinement | Validated — see VALIDATION.md |

---

## Repository layout

```
*.ipynb                    ← 12 course notebooks (flat at root)
canonical/                 ← source of truth for each canonical code block
  bootstrap.py
  gmsh_rect_minus_circles.py
  refine_cells.py
  plot_helpers.py
  tag_boundaries.py
  xdmf_series.py
  time_step.py
tools/
  check_canonical.py       ← verify notebook blocks match canonical/*.py
  check_badges.py          ← verify Colab badge URLs
  run_notebooks.py         ← headless execution (nbclient)
  snapshot_qoi.py          ← QoI snapshot and regression guard
  regression_qoi.py        ← env-to-env comparison
  install_hooks.sh         ← pre-commit hook installer
verification/              ← verification notebooks (ST benchmarks, MMS)
env-osx-arm64.lock         ← exact osx-arm64 lockfile (fenicsx-0.11-py312)
environment.yml            ← portable env spec (Python 3.12, dolfinx 0.11)
VALIDATION.md              ← quantitative QoI records
```

---

## Canonical blocks

Each notebook embeds reusable code blocks delimited by:

```python
# --- canonical: <name> v<N> ---
...
# --- end canonical: <name> ---
```

The source of truth is `canonical/<name>.py`. Eight blocks are currently defined:
`bootstrap` (v2), `gmsh_rect_minus_circles` (v6), `refine_cells` (v2), `plot_helpers` (v3),
`export_xdmf` (v2), `tag_boundaries` (v1), `xdmf_series` (v1), `time_step` (v1).

To check for canonical block drift:

```bash
python tools/check_canonical.py
```

---

## Git hooks (recommended)

Install once after cloning:

```bash
bash tools/install_hooks.sh
```

The hook runs on `git commit` and:
1. Checks that all embedded canonical blocks match `canonical/*.py` — aborts on drift.
2. Checks that all Colab badge URLs point to `blob/main/<file>.ipynb`.
3. Strips cell outputs and execution counts from staged `*.ipynb` via `nbstripout`.

> `nbstripout` is installed in both `fenicsx-0.11` and `fenicsx-0.11-py312` conda envs.

---

## Authorized deviations from the legacy FEniCS notebooks

| Item | Description | Authorized by | Date |
|---|---|---|---|
| Nitsche BCs (Poisson, Stokes) | Symmetric Nitsche replaces pure-penalty Dirichlet BCs (C=1e3 → C=10/20); optimal convergence for all C above the inverse-estimate threshold | Johan | 2026-10-03 |
| NS-ALE mesh velocity | Mesh velocity `beta_u` prescribed directly (incremental mesh move by `dt·beta`); consistent with future ALE-FSI formulation | Johan | 2026-10-XX |
| Triple decomposition dtype (NS) | `new_grad = np.zeros((3,3))` (float64); legacy used integer zeros causing truncation | Johan | 2026-10-01 |
| SWE force sign (Shallow-Water) | `+g·inner(grad(w),psi)·dx`; legacy sign was wrong (gave negative drag) | Johan | 2026-10-XX |
| Euler pressure-force | `normalization_cd_p = −normalization_cd` for correct positive drag sign | Johan | 2026-10-XX |

---

## License

MIT. Copyright (C) 2020–2026 Johan Hoffman (johanhoffman@kth.se).

---

## Contributors

- **Johan Hoffman** (johanhoffman@kth.se) — course author, FEniCSx port

---

## Maintenance

### Branching

Always branch from freshly fetched `origin/main`:

```bash
git fetch origin && git checkout -b <branch> origin/main
```

Never branch from a stale local copy — canonical blocks in `main` may have been updated.

### CI

GitHub Actions runs on every push and PR:
1. `check_canonical.py` — canonical block sync
2. `check_badges.py` — Colab badge URLs
3. `nbstripout --verify` — no outputs committed
4. `run_notebooks.py` — all 12 notebooks in FAST mode (`DD2365_FAST=1`)
5. `snapshot_qoi.py` — regression guard: FAST mode snapshot compared against `tools/baseline_fast_ci.json` with `--rtol 1e-6`

Any PR that changes numerical results must update `tools/baseline_fast_ci.json` in the same PR (numerical-results tier).

### Environment upgrades

Environment upgrades (dolfinx version, dependency bumps) require a dedicated PR containing:
1. Updated `environment.yml` and `env-osx-arm64.lock`
2. A regression table (old env vs new env) produced by `tools/regression_qoi.py`
3. All QoI diffs documented in `VALIDATION.md` before merge
4. CI green on the new env

Merges are merge-commit only (no squash/rebase).
`numerical-results` PRs require human review before merge.
