import numpy as np
import gmsh
from mpi4py import MPI
from dolfinx.io import gmsh as gmshio


def gmsh_rect_minus_circles(L, H, circles, resolution):
    """Rectangle [0,L]×[0,H] minus circular holes, meshed with gmsh OCC.

    Parameters
    ----------
    L, H : float
        Rectangle dimensions.
    circles : list of (cx, cy, r)
        Circle centres and radii to subtract.
    resolution : int
        Global mesh size target: lc = 1/resolution.  mshr's ``resolution``
        parameter has slightly different semantics (CGAL internal); here lc
        sets a uniform global target — cell count will differ slightly.

    Returns
    -------
    msh : dolfinx.mesh.Mesh
    cell_tags : dolfinx.mesh.MeshTags   (fluid domain tag = 10)
    facet_tags : dolfinx.mesh.MeshTags  (left=1, right=2, lower=3, upper=4, objects=5)
    """
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)

    rect = gmsh.model.occ.addRectangle(0.0, 0.0, 0.0, L, H)
    disks = [(2, gmsh.model.occ.addDisk(cx, cy, 0.0, r, r)) for cx, cy, r in circles]
    if disks:
        gmsh.model.occ.cut([(2, rect)], disks)
    gmsh.model.occ.synchronize()

    lc = 1.0 / resolution
    gmsh.option.setNumber("Mesh.MeshSizeMin", 0.5 * lc)
    gmsh.option.setNumber("Mesh.MeshSizeMax", lc)

    surfaces = gmsh.model.getEntities(2)
    gmsh.model.addPhysicalGroup(2, [s[1] for s in surfaces], tag=10, name="domain")

    # gmsh OCC bounding-box coordinates have ~1e-7 rounding; use EPS=1e-4
    # (well below the smallest geometric feature: circle radius 0.2).
    EPS = 1e-4
    left, right, lower, upper, objects = [], [], [], [], []
    for _, tag in gmsh.model.getEntities(1):
        xmin, ymin, _, xmax, ymax, _ = gmsh.model.getBoundingBox(1, tag)
        if xmax - xmin < EPS and abs(xmin) < EPS:
            left.append(tag)
        elif xmax - xmin < EPS and abs(xmax - L) < EPS:
            right.append(tag)
        elif ymax - ymin < EPS and abs(ymin) < EPS:
            lower.append(tag)
        elif ymax - ymin < EPS and abs(ymax - H) < EPS:
            upper.append(tag)
        else:
            objects.append(tag)

    for tags, name, tag_id in [
        (left,    "left",    1),
        (right,   "right",   2),
        (lower,   "lower",   3),
        (upper,   "upper",   4),
        (objects, "objects", 5),
    ]:
        if tags:
            gmsh.model.addPhysicalGroup(1, tags, tag=tag_id, name=name)

    gmsh.model.mesh.generate(2)

    mesh_data = gmshio.model_to_mesh(gmsh.model, MPI.COMM_WORLD, rank=0, gdim=2)
    gmsh.finalize()
    return mesh_data.mesh, mesh_data.cell_tags, mesh_data.facet_tags
