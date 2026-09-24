import math
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
        Mesh density parameter.  The global size bound is

            lc = 0.65 * sqrt(L² + H²) / resolution

        This matches the mshr/CGAL semantics used in the legacy FEniCS
        notebooks: mshr's ``resolution`` sets a CGAL size bound equal to
        the bounding-box diagonal divided by ``resolution``; gmsh realised
        edges are approximately 0.6× that bound.  The factor 0.65 was
        calibrated so that the standard test case (L=4, H=2, 3 circular
        holes, resolution=32) produces ≈2319 cells — matching the legacy
        mshr mesh (2319 cells, 1247 P1 dofs).

    Returns
    -------
    msh : dolfinx.mesh.Mesh
    cell_tags : dolfinx.mesh.MeshTags   (fluid domain tag = 10)

    Note
    ----
    Facet tags are not produced here.  Call ``tag_boundaries(msh, L, H)``
    on the final mesh (after any refinement) to obtain boundary MeshTags.
    """
    _ALPHA = 0.65
    lc = _ALPHA * math.sqrt(L**2 + H**2) / resolution

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)

    rect = gmsh.model.occ.addRectangle(0.0, 0.0, 0.0, L, H)
    disks = [(2, gmsh.model.occ.addDisk(cx, cy, 0.0, r, r)) for cx, cy, r in circles]
    if disks:
        gmsh.model.occ.cut([(2, rect)], disks)
    gmsh.model.occ.synchronize()

    gmsh.option.setNumber("Mesh.MeshSizeMax", lc)

    surfaces = gmsh.model.getEntities(2)
    gmsh.model.addPhysicalGroup(2, [s[1] for s in surfaces], tag=10, name="domain")

    gmsh.model.mesh.generate(2)

    mesh_data = gmshio.model_to_mesh(gmsh.model, MPI.COMM_WORLD, rank=0, gdim=2)
    gmsh.finalize()
    return mesh_data.mesh, mesh_data.cell_tags
