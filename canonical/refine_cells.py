import numpy as np
import dolfinx.mesh
from dolfinx.mesh import RefinementOption


def refine_cells(msh, predicate):
    """Refine all cells whose midpoint satisfies predicate (Plaza algorithm).

    Parameters
    ----------
    msh : dolfinx.mesh.Mesh
    predicate : callable
        ``f(midpoints) -> bool array`` where ``midpoints`` has shape
        ``(ncells, gdim)``.

    Returns
    -------
    refined_msh : dolfinx.mesh.Mesh
        The refined mesh.
    parent_cells : np.ndarray[np.int32]
        For each refined cell: index of its parent cell in ``msh``.
        Shape ``(num_refined_cells,)``.
    parent_facets : np.ndarray[np.int8]
        For each refined cell: local index (0–3) of the parent facet it
        inherits, or -1 if interior.  Shape ``(num_refined_cells,)``.
        dolfinx 0.11: ``RefinementOption.parent_cell_and_facet``.
    """
    tdim = msh.topology.dim
    num_cells = msh.topology.index_map(tdim).size_local
    msh.topology.create_entities(1)
    msh.topology.create_connectivity(tdim, 0)
    midpoints = dolfinx.mesh.compute_midpoints(
        msh, tdim, np.arange(num_cells, dtype=np.int32)
    )
    marked = np.where(predicate(midpoints))[0].astype(np.int32)
    if len(marked) == 0:
        # No cells marked: return identity — parent_cells is trivial range,
        # parent_facets is all-(-1).
        n = msh.topology.index_map(tdim).size_local
        return msh, np.arange(n, dtype=np.int32), np.full(n, -1, dtype=np.int8)
    msh.topology.create_connectivity(tdim, 1)
    edges = dolfinx.mesh.compute_incident_entities(msh.topology, marked, tdim, 1)
    edges = np.unique(edges).astype(np.int32)
    return dolfinx.mesh.refine(
        msh, edges, option=RefinementOption.parent_cell_and_facet
    )
