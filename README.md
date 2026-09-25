# DD2365 FEniCSx Notebooks

FEniCSx port of the DD2365 Advanced Computation in Fluid Mechanics course notebooks
(KTH Royal Institute of Technology). Original FEniCS versions:
[johanhoffman/DD2365](https://github.com/johanhoffman/DD2365).

---

## Running on Google Colab

Click the **Open in Colab** badge at the top of any notebook. The first cell
installs FEniCSx (dolfinx 0.11, FEM-on-Colab release-real) and gmsh automatically.
Select **Runtime → Run all**.

---

## Running locally

### Conda environment (recommended)

An `environment.yml` is provided at the repo root with all pinned dependencies. Create and activate with:

```bash
conda env create -f environment.yml   # or: mamba env create -f environment.yml
conda activate fenicsx-0.11
jupyter notebook
```

**Pinned versions:**

| Package    | Version     |
|------------|-------------|
| dolfinx    | 0.11.0      |
| basix      | 0.11.0      |
| ffcx       | 0.11.0      |
| ufl        | 2026.1.0    |
| petsc4py   | 3.25.2      |
| gmsh       | 4.15.2      |

> **Apple Silicon / MUMPS note:** The bootstrap block sets `OMP_NUM_THREADS=1`
> before petsc4py import. This is required to avoid MUMPS non-determinism on M-series Macs.

---

## Repository layout

```
Poisson_equation.ipynb       ← ported notebooks (flat at root)
canonical/
  bootstrap.py               ← source of truth for each canonical block
  gmsh_rect_minus_circles.py
  refine_cells.py
  plot_helpers.py
  export_xdmf.py
  tag_boundaries.py
tools/
  check_canonical.py         ← verify notebook blocks match canonical/*.py
  run_notebooks.py           ← headless execution with nbclient
```

---

## Canonical blocks

Each notebook embeds reusable code blocks delimited by:

```python
# --- canonical: <name> v1 ---
...
# --- end canonical: <name> ---
```

The source of truth is `canonical/<name>.py`.  Seven blocks are currently defined:
`bootstrap` (v1), `gmsh_rect_minus_circles` (v2), `refine_cells` (v2), `plot_helpers` (v2), `export_xdmf` (v2), `tag_boundaries` (v1), `xdmf_series` (v1).

`gmsh_rect_minus_circles v2` uses `lc = 0.65 * sqrt(L²+H²) / resolution`, calibrated to match
the legacy mshr/CGAL cell count (standard case: 2324 cells vs mshr 2319).

`refine_cells v2` accepts either a callable predicate `f(midpoints) -> bool array` or a boolean array over local cells (used by the DWR AMR loop).
`plot_helpers v2` adds `plot_scalar(f)` and `plot_vector(u)` for Stokes/NS fields.
`export_xdmf v2` auto-interpolates to P1 before writing (XDMF stores nodal data only).
`xdmf_series v1` is an `XDMFSeries` class for time-series XDMF output: open once, `write(funcs, t)` per step, `close()`.  Auto-interpolates to P1 and optionally tars+downloads on Colab.

**Facet tagging:** `gmsh_rect_minus_circles` returns only `(msh, cell_tags)`. Call
`tag_boundaries(msh, L, H)` on the final mesh (after any refinement) to get boundary
`MeshTags` with tags left=1, right=2, lower=3, upper=4, circle objects=5.

To check for drift:

```bash
python tools/check_canonical.py
```

To run all notebooks headlessly:

```bash
conda activate fenicsx-0.11
python tools/run_notebooks.py
```

### Git pre-commit hook (recommended)

Install once after cloning:

```bash
bash tools/install_hooks.sh
```

The hook runs automatically on `git commit` and:
1. Verifies all embedded canonical blocks match `canonical/*.py` — aborts if there is drift.
2. Strips cell outputs and execution counts from staged `*.ipynb` files via `nbstripout` — notebooks are stored clean (no outputs) in the repo.

> **Requirement:** `nbstripout` must be on `PATH` (it is installed in the `fenicsx-0.11` conda env).  To install in any other environment: `pip install nbstripout`.

---

## Porting status

| Notebook | Ported | Local run | Colab run | Validated vs legacy |
|----------|:------:|:---------:|:---------:|:-------------------:|
| Poisson_equation.ipynb | ✓ | ✓ | — | — |
| template-report-Stokes.ipynb | ✓ | ✓ | — | — |
| template-report-Stokes-AMR.ipynb | ✓ | ✓ | — | — |
| Navier-Stokes.ipynb | — | — | — | — |
| Navier-Stokes-ALE.ipynb | — | — | — | — |
| Elasticity.ipynb | — | — | — | — |
| Brinkman_NSE.ipynb | — | — | — | — |
| Convection-Diffusion-NSE.ipynb | ✓ | ✓ | — | — |
| Euler-equations-compressible-flow.ipynb | — | — | — | — |
| PeriodicBC.ipynb | — | — | — | — |
| Turbulence-Model.ipynb | — | — | — | — |
| Shallow-Water-Equations.ipynb | — | — | — | — |

> **PeriodicBC:** `dolfinx_mpc` is not available in the FEM-on-Colab 0.11 environment.
> Decision on replacement approach pending.

---

## Notebook conventions

- **Branch from main:** always `git fetch` and branch from `origin/main` — never from a stale local copy.
- **Self-contained:** no shared helper module; all imports and function definitions are inside each notebook.
- **Cell structure:** Abstract / About the code / Set up environment / Introduction / Method / Results / Discussion — matching the legacy notebooks.
- **Colab badge** links to `main` branch.
- **License:** MIT. Copyright (C) 2020–2026 Johan Hoffman (jhoffman@kth.se).
