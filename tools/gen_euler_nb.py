#!/usr/bin/env python3
"""Generate Euler-equations-compressible-flow.ipynb."""
import json, pathlib

REPO      = pathlib.Path(__file__).parent.parent
CANONICAL = REPO / "canonical"

def read_can(name):
    return (CANONICAL / f"{name}.py").read_text()

def cc(src, tags=None):
    meta = {"tags": tags} if tags else {}
    return {"cell_type": "code", "execution_count": None,
            "metadata": meta, "outputs": [],
            "source": src.splitlines(keepends=True)}

def mc(src):
    return {"cell_type": "markdown", "metadata": {},
            "source": src.splitlines(keepends=True)}

def can_cell(name, ver):
    c   = read_can(name)
    src = f"# --- canonical: {name} v{ver} ---\n{c}# --- end canonical: {name} ---"
    return cc(src)

NB = "Euler-equations-compressible-flow.ipynb"
cells = []

# 0 – Colab badge
cells.append(mc(
    f'<a href="https://colab.research.google.com/github/johanhoffman/DD2365_FEniCSx'
    f'/blob/main/{NB}" target="_parent">'
    '<img src="https://colab.research.google.com/assets/colab-badge.svg" '
    'alt="Open In Colab"/></a>'
))

# 1 – About the code
cells.append(mc("# **The Euler equations for compressible flow** **Johan Hoffman**"))

# 2 – Abstract
cells.append(mc(
    "# **Abstract**\n\n"
    "This short report shows an example on how to use FEniCSx to solve the Euler equations "
    "for compressible flow. A stabilized finite element method with shock-capturing diffusion "
    "is applied to simulate supersonic flow past a circular cylinder."
))

# 3 – Copyright
cells.append(cc(
    "# Copyright (C) 2019-2026 Johan Hoffman (jhoffman@kth.se)\n"
    "#\n"
    "# This file is part of the course DD2365 Advanced Computation in Fluid Mechanics\n"
    "# KTH Royal Institute of Technology, Stockholm, Sweden\n"
    "#\n"
    "# This is free software: you can redistribute it and/or modify\n"
    "# it under the terms of the GNU Lesser General Public License as published by\n"
    "# the Free Software Foundation, either version 3 of the License, or\n"
    "# (at your option) any later version.\n"
    "#\n"
    "# This template is maintained by Johan Hoffman\n"
    "# Please report problems to jhoffman@kth.se"
))

# 4 – Setup environment header
cells.append(mc("# Setup environment"))

# 5-11 – Canonical blocks
cells.append(can_cell("bootstrap", 1))
cells.append(can_cell("gmsh_rect_minus_circles", 6))
cells.append(can_cell("refine_cells", 1))
cells.append(can_cell("tag_boundaries", 1))
cells.append(can_cell("plot_helpers", 3))
cells.append(can_cell("xdmf_series", 1))
cells.append(can_cell("time_step", 1))

# 12 – Imports
cells.append(cc(
    "import numpy as np\n"
    "import time\n"
    "import math\n"
    "from mpi4py import MPI\n"
    "from dolfinx.fem import (\n"
    "    functionspace, Function, Constant, form,\n"
    "    assemble_scalar, locate_dofs_topological, dirichletbc,\n"
    "    Expression,\n"
    ")\n"
    "from dolfinx.fem.petsc import (\n"
    "    assemble_matrix, assemble_vector, apply_lifting, set_bc,\n"
    "    create_matrix, create_vector,\n"
    ")\n"
    "from petsc4py import PETSc\n"
    "import ufl\n"
    "import basix.ufl as bufl\n"
    "import matplotlib.pyplot as plt"
))

# 13 – Introduction heading
cells.append(mc("# **Introduction**"))

# 14 – Introduction text
cells.append(mc(
    "For density $\\rho$, momentum $m$, and total energy $E$, "
    "the Euler equations take the form\n\n"
    "$$\\frac{\\partial \\rho}{\\partial t} + \\nabla \\cdot (\\rho u) = 0$$\n\n"
    "$$\\frac{\\partial m}{\\partial t} + \\nabla \\cdot (m \\otimes u) + \\nabla p = 0$$\n\n"
    "$$\\frac{\\partial E}{\\partial t} + \\nabla \\cdot (Eu + pu) = 0$$\n\n"
    "where $u = m/\\rho$ is the velocity and "
    "$p = (\\gamma-1)\\bigl(E - \\tfrac{1}{2}|m|^2/\\rho\\bigr)$ is the pressure."
))

# 15 – Method heading
cells.append(mc("# **Method**"))

# 16 – Domain markdown
cells.append(mc("**Define domain and mesh**"))

# 17 – Domain code
cells.append(cc(
    "# Define length scale\n"
    "L_ref = 1.0\n"
    "\n"
    "# Define rectangular domain\n"
    "L = 5.0\n"
    "H = 4.0\n"
    "\n"
    "# Model diameter\n"
    "MD = 0.4\n"
    "\n"
    "# Define circle\n"
    "xc = 1.5\n"
    "yc = 0.5*H\n"
    "rc = 0.5*MD\n"
    "\n"
    "# Generate mesh\n"
    "resolution = 64\n"
    "msh, _ = gmsh_rect_minus_circles(L, H, [(xc, yc, rc)], resolution)\n"
    "facet_tags = tag_boundaries(msh, L, H)\n"
    "\n"
    "# Local mesh refinement (no_levels=0; increase for finer boundary layers)\n"
    "no_levels = 0\n"
    "for _ in range(no_levels):\n"
    "    msh, _, _ = refine_cells(\n"
    "        msh,\n"
    "        lambda midpoints: (np.hypot(midpoints[:, 0] - xc, midpoints[:, 1] - yc) < 1.0),\n"
    "    )\n"
    "    facet_tags = tag_boundaries(msh, L, H)\n"
    "\n"
    "tdim   = msh.topology.dim\n"
    "fdim   = tdim - 1\n"
    "n_cells = msh.topology.index_map(tdim).size_local\n"
    "\n"
    "plot_mesh(msh)"
))

# 18 – Physics markdown
cells.append(mc("**Define physics model**"))

# 19 – Physics code
cells.append(cc(
    "# Adiabatic index gamma = cp/cv (gamma = 1.4 for air)\n"
    "gamma = 1.4\n"
    "\n"
    "# Specific gas constant [J/(kg*K)]\n"
    "R_constant = 287\n"
    "\n"
    "# Specific heat at constant volume [J/(kg*K)]\n"
    "cv = R_constant / (gamma - 1.0)\n"
    "\n"
    "# Free stream flow data (used as boundary data)\n"
    "r_fs    = 1.225  # [kg/m3]\n"
    "Temp_fs = 290    # [K]\n"
    "u_fs    = 500    # [m/s]\n"
    "print('Free stream density [kg/m3]:', r_fs)\n"
    "print('Free stream temperature [K]:', Temp_fs)\n"
    "print('Free stream velocity [m/s]:', u_fs)\n"
    "\n"
    "m_fs = u_fs * r_fs\n"
    "c_fs = math.sqrt(gamma * R_constant * Temp_fs)\n"
    "M_fs = u_fs / c_fs\n"
    "print('Mach number (free stream):', M_fs)\n"
    "\n"
    "e_fs = cv * Temp_fs\n"
    "E_fs = r_fs * (e_fs + 0.5 * u_fs * u_fs)\n"
    "\n"
    "# Canonical nondimensional form – reference normalizations\n"
    "r_ref = 1.225   # [kg/m3] – sea-level density\n"
    "u_ref = 340.3   # [m/s]  – sea-level speed of sound\n"
    "m_ref = r_ref * u_ref\n"
    "E_ref = r_ref * u_ref * u_ref\n"
    "p_ref = r_ref * u_ref * u_ref\n"
    "\n"
    "p_fs = r_fs * Temp_fs * R_constant\n"
    "print('Free stream pressure [Pa]:', p_fs)\n"
    "print('Free stream pressure (nondimensional):', p_fs / p_ref)\n"
    "\n"
    "T_ref = L_ref / u_ref\n"
    "print('Reference time [s]:', T_ref)"
))

# 20 – FE spaces markdown
cells.append(mc("**Define finite element approximation spaces**"))

# 21 – FE spaces code
cells.append(cc(
    "# Generate finite element spaces (for density, momentum, total energy)\n"
    "P1s = bufl.element('Lagrange', msh.basix_cell(), 1)\n"
    "P1v = bufl.element('Lagrange', msh.basix_cell(), 1, shape=(2,))\n"
    "\n"
    "R = functionspace(msh, P1s)   # density\n"
    "V = functionspace(msh, P1v)   # momentum\n"
    "Q = functionspace(msh, P1s)   # total energy\n"
    "\n"
    "# Define trial and test functions\n"
    "r = ufl.TrialFunction(R)\n"
    "m = ufl.TrialFunction(V)\n"
    "E = ufl.TrialFunction(Q)\n"
    "d = ufl.TestFunction(R)\n"
    "v = ufl.TestFunction(V)\n"
    "q = ufl.TestFunction(Q)"
))

# 22 – BCs markdown
cells.append(mc("**Define boundary conditions**"))

# 23 – BCs code
cells.append(cc(
    "# Nondimensional inflow values\n"
    "r_in     = r_fs / r_ref\n"
    "m_in     = m_fs / m_ref\n"
    "E_in     = E_fs / E_ref\n"
    "m_in_vec = ufl.as_vector([m_in, 0.0])\n"
    "\n"
    "def _bc(space, value, tag):\n"
    "    dofs = locate_dofs_topological(space, fdim, facet_tags.find(tag))\n"
    "    return dirichletbc(PETSc.ScalarType(value), dofs, space)\n"
    "\n"
    "bcm_in0  = _bc(V.sub(0), m_in, 1)   # m_x = m_in at inflow\n"
    "bcm_in1  = _bc(V.sub(1), 0.0,  1)   # m_y = 0    at inflow\n"
    "bcm_upp1 = _bc(V.sub(1), 0.0,  4)   # m_y = 0    at upper wall (slip)\n"
    "bcm_low1 = _bc(V.sub(1), 0.0,  3)   # m_y = 0    at lower wall (slip)\n"
    "#bcm_obj0 = _bc(V.sub(0), 0.0, 5)   # cylinder no-slip (commented as in legacy)\n"
    "#bcm_obj1 = _bc(V.sub(1), 0.0, 5)\n"
    "\n"
    "# Slip boundary condition (commented out as in legacy):\n"
    "#V_slip = FunctionSpace(mesh, 'CG', 1)\n"
    "#bcm_slip_0 = Function(V_slip); bcm_slip_1 = Function(V_slip)\n"
    "\n"
    "# Inflow BC based on characteristics: supersonic -> all components fixed\n"
    "if M_fs > 1.0:\n"
    "    bcm = [bcm_in0, bcm_in1, bcm_upp1, bcm_low1]\n"
    "else:\n"
    "    bcm = [bcm_in0, bcm_upp1, bcm_low1]\n"
    "\n"
    "bcr = [_bc(R, r_in, 1)]\n"
    "bcE = [_bc(Q, E_in, 1)]\n"
    "\n"
    "# Approximate facet normal (commented out as in legacy):\n"
    "#n = ufl.FacetNormal(msh)\n"
    "#V_normal = functionspace(msh, P1v)\n"
    "\n"
    "# Boundary measure\n"
    "ds_m = ufl.Measure('ds', domain=msh, subdomain_data=facet_tags)"
))

# 24 – Results heading
cells.append(mc("# **Results**"))

# 25 – Parameters heading
cells.append(mc("**Define flow parameters**"))

# 26 – Parameters code (tagged)
cells.append(cc(
    "# Length of time interval [nondimensional]\n"
    "T = 10.0\n"
    "plot_freq = 20",
    tags=["parameters"]
))

# 27 – Method parameters markdown
cells.append(mc("**Define method parameters**"))

# 28 – Method parameters code
cells.append(cc(
    "# Define iteration functions\n"
    "# *0 solution from previous time step\n"
    "# *1 linearized solution at present time step\n"
    "r0 = Function(R, name='r0'); r1 = Function(R, name='r1')\n"
    "m0 = Function(V, name='m0'); m1 = Function(V, name='m1')\n"
    "E0 = Function(Q, name='E0'); E1 = Function(Q, name='E1')\n"
    "\n"
    "# Lower threshold for density (cavitation fix)\n"
    "eps_cav = 1.0e-6\n"
    "\n"
    "# Set parameters for nonlinear and linear solvers\n"
    "num_nnlin_iter = 5\n"
    "\n"
    "# Time step length (CFL-based): dt = hmin / (u_in + c_in)\n"
    "u_in = m_in / r_in\n"
    "c_in = math.sqrt(gamma * (gamma - 1.0) * (E_in / r_in - 0.5 * u_in * u_in))\n"
    "dt   = time_step(msh, u_in + c_in, C_CFL=1.0)\n"
    "dt_c = Constant(msh, PETSc.ScalarType(dt))\n"
    "\n"
    "print(f'u_in = {u_in:.4f}  c_in = {c_in:.4f}  dt = {dt:.6f}')\n"
    "print(f'Time interval: {T:.2f}  ({T * T_ref:.4f} s physical)')"
))

# 29 – Variational problem markdown
cells.append(mc("**Define variational problem**"))

# 30 – Forms code
cells.append(cc(
    "# Mean velocities for alpha-method time stepping\n"
    "# alpha_dt = 0.0: explicit Euler, 0.5: trapezoidal, 1.0: implicit Euler\n"
    "alpha_dt = 0.7\n"
    "\n"
    "rm  = alpha_dt*r  + (1.0 - alpha_dt)*r0\n"
    "mm  = alpha_dt*m  + (1.0 - alpha_dt)*m0\n"
    "Em  = alpha_dt*E  + (1.0 - alpha_dt)*E0\n"
    "\n"
    "rm1 = alpha_dt*r1 + (1.0 - alpha_dt)*r0\n"
    "mm1 = alpha_dt*m1 + (1.0 - alpha_dt)*m0\n"
    "Em1 = alpha_dt*E1 + (1.0 - alpha_dt)*E0\n"
    "\n"
    "u0_ufl = m0 / (r0 + eps_cav)\n"
    "u1     = m1 / (r1 + eps_cav)\n"
    "um1    = alpha_dt*u1 + (1.0 - alpha_dt)*u0_ufl\n"
    "\n"
    "# Pressure [nondimensional]\n"
    "p1 = (gamma - 1.0)*(E1 - 0.5*ufl.inner(m1, m1)/(r1 + eps_cav))\n"
    "\n"
    "# Speed of sound [nondimensional]\n"
    "c = ufl.sqrt(gamma*(gamma - 1.0)*(E1/r1 - 0.5*ufl.inner(u1, u1)))\n"
    "\n"
    "# Mach number [nondimensional]\n"
    "Mach = ufl.sqrt(ufl.inner(u1, u1)) / c\n"
    "\n"
    "# Outflow pressure: p_fs/p_ref if subsonic, 0 if supersonic\n"
    "p_out = ufl.conditional(\n"
    "    ufl.lt(Mach, Constant(msh, PETSc.ScalarType(1.0))),\n"
    "    Constant(msh, PETSc.ScalarType(float(p_fs / p_ref))),\n"
    "    Constant(msh, PETSc.ScalarType(0.0)),\n"
    ")\n"
    "\n"
    "# Facet normal and local mesh size\n"
    "normal = ufl.FacetNormal(msh)\n"
    "h      = ufl.CellDiameter(msh)\n"
    "\n"
    "# Stabilization parameter (d1 terms commented out as in legacy)\n"
    "C1    = 1.0\n"
    "u_mag = ufl.sqrt(ufl.dot(u1, u1))\n"
    "d1    = C1 / ufl.sqrt((1.0/dt_c)**2 + (u_mag/h)**2)\n"
    "\n"
    "# Parameters for penalty boundary condition on cylinder\n"
    "C_alpha       = 1.0e2\n"
    "alpha_penalty = C_alpha / h\n"
    "\n"
    "# Residuals for shock-capturing stabilization\n"
    "res_r = (r1 - r0)/dt_c + ufl.div(u1)*r1 + ufl.inner(ufl.grad(r1), u1)\n"
    "res_m = (m1 - m0)/dt_c + ufl.div(u1)*m1 + ufl.grad(m1)*u1 + ufl.grad(p1)\n"
    "res_E = ((E1 - E0)/dt_c + ufl.div(u1)*E1 + ufl.inner(ufl.grad(E1), u1)\n"
    "         + ufl.div(u1)*p1 + ufl.inner(ufl.grad(p1), u1))\n"
    "\n"
    "# Smagorinsky model (commented out as in legacy):\n"
    "#C_t    = 1.0e-2\n"
    "#nu_turb = C_t*h*h*ufl.sqrt(ufl.inner(ufl.grad(um1), ufl.grad(um1)))\n"
    "\n"
    "# Shock-capturing stabilization coefficients\n"
    "C_stab = 1.0\n"
    "nu_r   = C_stab * h*h * ufl.sqrt(res_r*res_r) / r_in\n"
    "nu_m   = C_stab * h*h * ufl.sqrt(ufl.inner(res_m, res_m)) / m_in\n"
    "nu_E   = C_stab * h*h * ufl.sqrt(res_E*res_E) / E_in\n"
    "\n"
    "# Density variational form\n"
    "Fr = (ufl.inner((r - r0)/dt_c, d)*ufl.dx\n"
    "    - ufl.inner(rm*um1, ufl.grad(d))*ufl.dx\n"
    "    + nu_r * ufl.inner(ufl.grad(rm), ufl.grad(d))*ufl.dx\n"
    "    + ufl.inner(ufl.dot(um1, normal)*r_in, d)*ds_m(1)\n"
    "    + ufl.inner(ufl.dot(um1, normal)*rm, d)*ds_m(2))\n"
    "    #+ d1*inner((r-r0)/dt+div(u1)*rm+inner(grad(rm),u1), dot(grad(d),u1))*dx\n"
    "\n"
    "# Momentum variational form\n"
    "#Fm = inner((m-m0)/dt,v)*dx + inner(grad(mm)*um1,v)*dx + inner(div(um1)*mm,v)*dx - p1*div(v)*dx + ...\n"
    "Fm = (ufl.inner((m - m0)/dt_c, v)*ufl.dx\n"
    "    - ufl.inner(ufl.outer(mm, um1), ufl.grad(v))*ufl.dx\n"
    "    - p1*ufl.div(v)*ufl.dx\n"
    "    + nu_m * ufl.inner(ufl.grad(mm), ufl.grad(v))*ufl.dx\n"
    "    + alpha_penalty*(ufl.inner(ufl.dot(mm, normal), ufl.dot(v, normal)))*ds_m(5)\n"
    "    + ufl.dot(u1, normal)*ufl.inner(m_in_vec, v)*ds_m(1)\n"
    "    + p_out*ufl.dot(normal, v)*ds_m(2)\n"
    "    + ufl.dot(u1, normal)*ufl.inner(mm, v)*ds_m(2))\n"
    "    #+ d1*inner((m-m0)/dt+div(u1)*mm+grad(mm)*u1+grad(p1),grad(v)*u1)*dx\n"
    "\n"
    "# Energy variational form\n"
    "FE = (ufl.inner((E - E0)/dt_c, q)*ufl.dx\n"
    "    - ufl.inner(Em*um1, ufl.grad(q))*ufl.dx\n"
    "    - ufl.inner(p1*um1, ufl.grad(q))*ufl.dx\n"
    "    + nu_E * ufl.inner(ufl.grad(Em), ufl.grad(q))*ufl.dx\n"
    "    + ufl.inner(ufl.dot(um1, normal)*E_in, q)*ds_m(1)\n"
    "    + ufl.inner(ufl.dot(um1, normal)*Em, q)*ds_m(2)\n"
    "    + ufl.inner(ufl.dot(um1, normal)*p1, q)*ds_m(1)\n"
    "    + ufl.inner(ufl.dot(um1, normal)*p1, q)*ds_m(2))\n"
    "    #+ d1*inner((E-E0)/dt+div(u1)*Em+inner(grad(Em),u1)+div(u1)*p1+inner(grad(p1),u1),dot(grad(q),u1))*dx\n"
    "\n"
    "a_r = form(ufl.lhs(Fr));  L_r = form(ufl.rhs(Fr))\n"
    "a_m = form(ufl.lhs(Fm));  L_m = form(ufl.rhs(Fm))\n"
    "a_E = form(ufl.lhs(FE));  L_E = form(ufl.rhs(FE))"
))

# 31 – Force markdown
cells.append(mc("**Compute force on boundary**"))

# 32 – Force code
cells.append(cc(
    "# Define the direction of the force to be computed\n"
    "psi_x = 1.0\n"
    "psi_y = 0.0\n"
    "\n"
    "# Build psi: indicator function on cylinder dofs (tag 5), both components\n"
    "psi    = Function(V, name='psi')\n"
    "V0c, map_to_V_0 = V.sub(0).collapse()\n"
    "V1c, map_to_V_1 = V.sub(1).collapse()\n"
    "psi_0c = Function(V0c); psi_1c = Function(V1c)\n"
    "cyl_dofs_0 = locate_dofs_topological(V0c, fdim, facet_tags.find(5))\n"
    "cyl_dofs_1 = locate_dofs_topological(V1c, fdim, facet_tags.find(5))\n"
    "psi_0c.x.array[cyl_dofs_0] = psi_x\n"
    "psi_1c.x.array[cyl_dofs_1] = psi_y\n"
    "psi.x.array[map_to_V_0] = psi_0c.x.array\n"
    "psi.x.array[map_to_V_1] = psi_1c.x.array\n"
    "psi.x.scatter_forward()\n"
    "\n"
    "# Velocity [nondimensional]\n"
    "u1_psi = m1 / (r1 + eps_cav)\n"
    "\n"
    "# Pressure [nondimensional]\n"
    "p1_psi = (gamma - 1.0)*(E1 - 0.5*ufl.inner(m1, m1)/(r1 + eps_cav))\n"
    "\n"
    "# Compute force through divergence theorem and volume integral\n"
    "Force_form = form(\n"
    "    ufl.inner(\n"
    "        (m1 - m0)/dt_c + ufl.div(u1_psi)*m1 + ufl.grad(m1)*u1_psi,\n"
    "        psi\n"
    "    )*ufl.dx\n"
    "    - p1_psi*ufl.div(psi)*ufl.dx\n"
    ")\n"
    "\n"
    "# Compute force through surface integral of pressure\n"
    "force_normal      = ufl.FacetNormal(msh)\n"
    "Force_pressure_form = form(ufl.inner(force_normal, psi)*p1_psi*ds_m(5))\n"
    "\n"
    "# Force normalization to get non-dimensional force coefficient\n"
    "normalization_cd  = -2.0 / (MD * m_in * u_in)\n"
    "normalization_dim = (MD * L_ref * r_fs * u_fs * u_fs) * 0.5"
))

# 33 – Plotting setup markdown
cells.append(mc("**Set plotting variables and open export files**"))

# 34 – Plotting setup code
cells.append(cc(
    "# Matrices and KSP solvers\n"
    "A_r = create_matrix(a_r); b_r = create_vector(R)\n"
    "A_m = create_matrix(a_m); b_m = create_vector(V)\n"
    "A_E = create_matrix(a_E); b_E = create_vector(Q)\n"
    "\n"
    "def _ksp(A):\n"
    "    k = PETSc.KSP().create(msh.comm)\n"
    "    k.setOperators(A); k.setType('bcgs')\n"
    "    k.getPC().setType('ilu')\n"
    "    k.setTolerances(rtol=1e-6, atol=1e-14, max_it=500)\n"
    "    k.setFromOptions()\n"
    "    return k\n"
    "\n"
    "ksp_r = _ksp(A_r); ksp_m = _ksp(A_m); ksp_E = _ksp(A_E)\n"
    "\n"
    "# Initial conditions\n"
    "r0.interpolate(lambda x: np.full(x.shape[1], r_in))\n"
    "m0.interpolate(lambda x: np.vstack([np.full(x.shape[1], m_in), np.zeros(x.shape[1])]))\n"
    "E0.interpolate(lambda x: np.full(x.shape[1], E_in))\n"
    "set_bc(r0.x.petsc_vec, bcr); r0.x.scatter_forward()\n"
    "set_bc(m0.x.petsc_vec, bcm); m0.x.scatter_forward()\n"
    "set_bc(E0.x.petsc_vec, bcE); E0.x.scatter_forward()\n"
    "r1.x.array[:] = r0.x.array; r1.x.scatter_forward()\n"
    "m1.x.array[:] = m0.x.array; m1.x.scatter_forward()\n"
    "E1.x.array[:] = E0.x.array; E1.x.scatter_forward()\n"
    "\n"
    "# Open export file\n"
    "xdmf = XDMFSeries('results-Euler/solution.xdmf')\n"
    "\n"
    "# Plot frequency and force sampling setup\n"
    "plot_time            = 0.0\n"
    "force_array          = []\n"
    "force_array_pressure = []\n"
    "time_array           = []\n"
    "start_sample_time    = 1.0\n"
    "\n"
    "# Plot initial conditions\n"
    "plot_scalar(r0, title='Density [nondimensional]')\n"
    "plot_vector(m0, title='Momentum [nondimensional]')\n"
    "plot_scalar(E0, title='Total energy [nondimensional]')"
))

# 35 – Time stepping markdown
cells.append(mc("**Time stepping algorithm**"))

# 36 – Time loop code
cells.append(cc(
    "t_wall0 = time.time()\n"
    "t    = dt\n"
    "step = 0\n"
    "while t < T + 1e-10:\n"
    "\n"
    "    # Solve non-linear problem\n"
    "    k = 0\n"
    "    while k < num_nnlin_iter:\n"
    "\n"
    "        # Assemble and solve density\n"
    "        A_r.zeroEntries()\n"
    "        assemble_matrix(A_r, a_r, bcs=bcr); A_r.assemble()\n"
    "        with b_r.localForm() as loc: loc.set(0.0)\n"
    "        assemble_vector(b_r, L_r)\n"
    "        apply_lifting(b_r, [a_r], bcs=[bcr])\n"
    "        b_r.ghostUpdate(addv=PETSc.InsertMode.ADD, mode=PETSc.ScatterMode.REVERSE)\n"
    "        set_bc(b_r, bcr)\n"
    "        ksp_r.setOperators(A_r, A_r); ksp_r.solve(b_r, r1.x.petsc_vec)\n"
    "        r1.x.scatter_forward()\n"
    "        set_bc(r1.x.petsc_vec, bcr); r1.x.scatter_forward()\n"
    "\n"
    "        # Assemble and solve momentum\n"
    "        A_m.zeroEntries()\n"
    "        assemble_matrix(A_m, a_m, bcs=bcm); A_m.assemble()\n"
    "        with b_m.localForm() as loc: loc.set(0.0)\n"
    "        assemble_vector(b_m, L_m)\n"
    "        apply_lifting(b_m, [a_m], bcs=[bcm])\n"
    "        b_m.ghostUpdate(addv=PETSc.InsertMode.ADD, mode=PETSc.ScatterMode.REVERSE)\n"
    "        set_bc(b_m, bcm)\n"
    "        ksp_m.setOperators(A_m, A_m); ksp_m.solve(b_m, m1.x.petsc_vec)\n"
    "        m1.x.scatter_forward()\n"
    "        set_bc(m1.x.petsc_vec, bcm); m1.x.scatter_forward()\n"
    "\n"
    "        # Slip boundary condition (commented out as in legacy):\n"
    "        #bcm_slip_0 = m1[0] - dot(m1, node_normal)*node_normal[0]\n"
    "        #bcm_slip_1 = m1[1] - dot(m1, node_normal)*node_normal[1]\n"
    "        #[bc.apply(m1.vector()) for bc in bcm_slip]\n"
    "\n"
    "        # Assemble and solve total energy\n"
    "        A_E.zeroEntries()\n"
    "        assemble_matrix(A_E, a_E, bcs=bcE); A_E.assemble()\n"
    "        with b_E.localForm() as loc: loc.set(0.0)\n"
    "        assemble_vector(b_E, L_E)\n"
    "        apply_lifting(b_E, [a_E], bcs=[bcE])\n"
    "        b_E.ghostUpdate(addv=PETSc.InsertMode.ADD, mode=PETSc.ScatterMode.REVERSE)\n"
    "        set_bc(b_E, bcE)\n"
    "        ksp_E.setOperators(A_E, A_E); ksp_E.solve(b_E, E1.x.petsc_vec)\n"
    "        E1.x.scatter_forward()\n"
    "        set_bc(E1.x.petsc_vec, bcE); E1.x.scatter_forward()\n"
    "\n"
    "        k += 1\n"
    "\n"
    "    # Force (sampled once per step after nonlinear convergence)\n"
    "    F_vol = float(msh.comm.allreduce(assemble_scalar(Force_form), op=MPI.SUM))\n"
    "    F_prs = float(msh.comm.allreduce(assemble_scalar(Force_pressure_form), op=MPI.SUM))\n"
    "    if t > start_sample_time:\n"
    "        force_array.append(normalization_cd * F_vol)\n"
    "        force_array_pressure.append(normalization_cd * F_prs)\n"
    "        time_array.append(t)\n"
    "\n"
    "    if t > plot_time:\n"
    "        print(f'Time [nondimensional] t = {t:.4f}')\n"
    "        print(f'Time [seconds] t = {t * T_ref:.4f}')\n"
    "\n"
    "        xdmf.write([r1, m1, E1], t)\n"
    "\n"
    "        # Derived quantities for plotting\n"
    "        u1_fn = Function(V, name='Velocity')\n"
    "        u1_fn.interpolate(Expression(\n"
    "            m1 / (r1 + eps_cav), V.element.interpolation_points\n"
    "        ))\n"
    "        p1_fn = Function(Q, name='Pressure')\n"
    "        p1_fn.interpolate(Expression(\n"
    "            (gamma - 1.0)*(E1 - 0.5*ufl.inner(m1, m1)/(r1 + eps_cav)),\n"
    "            Q.element.interpolation_points\n"
    "        ))\n"
    "        e_int = E1/(r1 + eps_cav) - 0.5*ufl.inner(m1/(r1+eps_cav), m1/(r1+eps_cav))\n"
    "        c_sq  = gamma*(gamma - 1.0)*ufl.max_value(\n"
    "            e_int, Constant(msh, PETSc.ScalarType(eps_cav))\n"
    "        )\n"
    "        Mach_fn = Function(Q, name='Mach')\n"
    "        Mach_fn.interpolate(Expression(\n"
    "            ufl.sqrt(ufl.inner(m1/(r1+eps_cav), m1/(r1+eps_cav)))\n"
    "            / (ufl.sqrt(c_sq) + eps_cav),\n"
    "            Q.element.interpolation_points\n"
    "        ))\n"
    "\n"
    "        plot_scalar(r1,    title='Density [nondimensional]')\n"
    "        r1_dim = Function(R, name='Density_dim')\n"
    "        r1_dim.x.array[:] = r1.x.array * r_ref\n"
    "        plot_scalar(r1_dim, title='Density [kg/m3]')\n"
    "        plot_vector(m1,    title='Momentum [nondimensional]')\n"
    "        plot_scalar(E1,    title='Total energy [nondimensional]')\n"
    "        plot_vector(u1_fn, title='Velocity [nondimensional]')\n"
    "        plot_scalar(p1_fn, title='Pressure [nondimensional]')\n"
    "        plot_scalar(Mach_fn, title='Mach number [nondimensional]')\n"
    "\n"
    "        if time_array:\n"
    "            plt.figure()\n"
    "            plt.title(\n"
    "                f'Force coefficient [nondimensional] '\n"
    "                f'– scale {normalization_dim:.2f} N/m '\n"
    "                f'– time scale {T_ref:.4f} s'\n"
    "            )\n"
    "            plt.plot(time_array, force_array)\n"
    "            plt.show()\n"
    "\n"
    "            plt.figure()\n"
    "            plt.title(\n"
    "                f'Pressure force coefficient [nondimensional] '\n"
    "                f'– scale {normalization_dim:.2f} N/m'\n"
    "            )\n"
    "            plt.plot(time_array, force_array_pressure)\n"
    "            plt.show()\n"
    "\n"
    "        plot_time += T / plot_freq\n"
    "\n"
    "    # Update solution\n"
    "    r0.x.array[:] = r1.x.array; r0.x.scatter_forward()\n"
    "    m0.x.array[:] = m1.x.array; m0.x.scatter_forward()\n"
    "    E0.x.array[:] = E1.x.array; E0.x.scatter_forward()\n"
    "    t    += dt\n"
    "    step += 1\n"
    "\n"
    "xdmf.close()\n"
    "t_wall = time.time() - t_wall0\n"
    "print(f'Wall time: {t_wall:.1f} s')"
))

# 37 – QoI code
cells.append(cc(
    "norm_r1 = float(msh.comm.allreduce(\n"
    "    assemble_scalar(form(r1*r1*ufl.dx)), op=MPI.SUM))**0.5\n"
    "norm_m1 = float(msh.comm.allreduce(\n"
    "    assemble_scalar(form(ufl.inner(m1, m1)*ufl.dx)), op=MPI.SUM))**0.5\n"
    "norm_E1 = float(msh.comm.allreduce(\n"
    "    assemble_scalar(form(E1*E1*ufl.dx)), op=MPI.SUM))**0.5\n"
    "min_r1  = float(msh.comm.allreduce(r1.x.array.min(), op=MPI.MIN))\n"
    "print(f'||r1|| = {norm_r1:.6f}')\n"
    "print(f'||m1|| = {norm_m1:.6f}')\n"
    "print(f'||E1|| = {norm_E1:.6f}')\n"
    "print(f'min r1 = {min_r1:.6f}')\n"
    "print(f'cells  = {n_cells}')\n"
    "print(f'dt     = {dt:.6f}')\n"
    "print(f'steps  = {step}')"
))

# 38 – Discussion heading
cells.append(mc("# **Discussion**"))

# 39 – Discussion text
cells.append(mc(
    "A stabilized finite element method was implemented in FEniCSx to solve the Euler equations "
    "for compressible flow. "
    "The shock-capturing GLS stabilization with coefficients $\\nu_r$, $\\nu_m$, $\\nu_E$ provides "
    "dissipation proportional to the local residual, localizing artificial diffusion to regions of "
    "strong gradients (shocks, contact discontinuities). "
    "The $\\alpha$-method time stepping ($\\alpha = 0.7$) gives an implicitly-biased scheme that "
    "improves stability for supersonic flows. "
    "The penalty term $\\alpha_{\\text{penalty}} = C_\\alpha/h$ on the cylinder boundary enforces "
    "the normal momentum condition in a weak sense."
))

for i, cell in enumerate(cells):
    cell["id"] = str(i)

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.12.0",
        },
    },
    "cells": cells,
}

out = REPO / NB
with open(out, "w") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print(f"Written: {out}")
print(f"Total cells: {len(cells)}")
