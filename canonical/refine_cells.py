import numpy as np
import dolfinx.mesh
from dolfinx.mesh import RefinementOption


def refine_cells(msh, predicate_or_mask):
    """Refine selected cells using the Plaza algorithm.

    Parameters
    ----------
    msh : dolfinx.mesh.Mesh
    predicate_or_mask : callable or array-like of bool
        Either a callable ``f(midpoints) -> bool array`` where
        ``midpoints`` has shape ``(ncells, gdim)``, or a boolean array
        of length ``num_local_cells`` that directly marks which cells
        to refine (useful when marks come from an existing DG0 field).

    Returns
    -------
    refined_msh : dolfinx.mesh.Mesh
    parent_cells : np.ndarray[np.int32]  shape (num_refined_cells,)
    parent_facets : np.ndarray[np.int8]  shape (num_refined_cells,)
        Local parent-facet index per refined cell, or -1 for interior.
    """
    tdim = msh.topology.dim
    num_cells = msh.topology.index_map(tdim).size_local

    if callable(predicate_or_mask):
        msh.topology.create_entities(1)
        msh.topology.create_connectivity(tdim, 0)
        midpoints = dolfinx.mesh.compute_midpoints(
            msh, tdim, np.arange(num_cells, dtype=np.int32)
        )
        marked = np.where(predicate_or_mask(midpoints))[0].astype(np.int32)
    else:
        mask = np.asarray(predicate_or_mask, dtype=bool)
        marked = np.where(mask[:num_cells])[0].astype(np.int32)

    if len(marked) == 0:
        n = msh.topology.index_map(tdim).size_local
        return msh, np.arange(n, dtype=np.int32), np.full(n, -1, dtype=np.int8)

    msh.topology.create_entities(1)
    msh.topology.create_connectivity(tdim, 1)
    edges = dolfinx.mesh.compute_incident_entities(msh.topology, marked, tdim, 1)
    edges = np.unique(edges).astype(np.int32)
    return dolfinx.mesh.refine(
        msh, edges, option=RefinementOption.parent_cell_and_facet
    )
