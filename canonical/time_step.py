import numpy as np


def time_step(msh, U_ref, C_CFL=0.5):
    """Return C_CFL * h_min / U_ref (CFL-based time step)."""
    tdim = msh.topology.dim
    n_cells = msh.topology.index_map(tdim).size_local
    h_min = float(msh.h(tdim, np.arange(n_cells, dtype=np.int32)).min())
    return C_CFL * h_min / U_ref
