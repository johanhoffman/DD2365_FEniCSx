import numpy as np
import dolfinx.mesh


def refine_cells(msh, predicate):
    """Uniformly refine all cells whose midpoint satisfies predicate (Plaza).

    Parameters
    ----------
    msh : dolfinx.mesh.Mesh
    predicate : callable
        ``f(midpoints) -> bool array`` where ``midpoints`` has shape
        ``(ncells, gdim)``.

    Returns
    -------
    refined_msh : dolfinx.mesh.Mesh
    parent_cells : np.ndarray or None
    parent_facets : np.ndarray or None
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
        return msh, None, None
    msh.topology.create_connectivity(tdim, 1)
    edges = dolfinx.mesh.compute_incident_entities(msh.topology, marked, tdim, 1)
    edges = np.unique(edges).astype(np.int32)
    return dolfinx.mesh.refine(msh, edges)
