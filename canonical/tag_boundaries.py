import numpy as np
from dolfinx.mesh import locate_entities_boundary, meshtags


def tag_boundaries(msh, L, H, eps=None):
    """Tag exterior boundary facets of a [0,L]×[0,H] rectangle with holes.

    Assigns integer tags to all exterior boundary facets:

        left=1  (x ≈ 0),   right=2 (x ≈ L),
        lower=3 (y ≈ 0),   upper=4 (y ≈ H),
        objects=5 (remaining exterior facets — circle boundaries).

    Corners are unambiguous: boundary facets are edges, not vertices, so a
    corner vertex is shared by one vertical and one horizontal edge — each
    edge belongs to exactly one group and no facet is tagged twice.

    Parameters
    ----------
    msh : dolfinx.mesh.Mesh
    L, H : float
        Rectangle dimensions.
    eps : float, optional
        Coordinate tolerance.  Default ``1e-6 * max(L, H)``.

    Returns
    -------
    dolfinx.mesh.MeshTags
        Must be recomputed whenever the mesh changes (e.g. after refinement).
    """
    if eps is None:
        eps = 1e-6 * max(L, H)

    fdim = msh.topology.dim - 1
    msh.topology.create_entities(fdim)
    msh.topology.create_connectivity(fdim, msh.topology.dim)

    left  = locate_entities_boundary(msh, fdim, lambda x: x[0] <= eps)
    right = locate_entities_boundary(msh, fdim, lambda x: x[0] >= L - eps)
    lower = locate_entities_boundary(msh, fdim, lambda x: x[1] <= eps)
    upper = locate_entities_boundary(msh, fdim, lambda x: x[1] >= H - eps)

    known = np.unique(np.concatenate([left, right, lower, upper]))
    all_bdry = locate_entities_boundary(
        msh, fdim, lambda x: np.ones(x.shape[1], dtype=bool)
    )
    objects = np.setdiff1d(all_bdry, known)

    indices = np.concatenate([left, right, lower, upper, objects]).astype(np.int32)
    values  = np.concatenate([
        np.full(len(left),    1, dtype=np.int32),
        np.full(len(right),   2, dtype=np.int32),
        np.full(len(lower),   3, dtype=np.int32),
        np.full(len(upper),   4, dtype=np.int32),
        np.full(len(objects), 5, dtype=np.int32),
    ])
    order = np.argsort(indices)
    return meshtags(msh, fdim, indices[order], values[order])
