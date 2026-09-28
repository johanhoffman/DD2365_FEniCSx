import math
import numpy as np
import gmsh
from mpi4py import MPI
from dolfinx.io import gmsh as gmshio


def gmsh_rect_minus_circles(L, H, circles, resolution, segments=32):
    """Rectangle [0,L]×[0,H] minus circular holes, meshed with gmsh OCC.

    Parameters
    ----------
    L, H : float
        Rectangle dimensions.
    circles : list of (cx, cy, r)
        Circle centres and radii to subtract.
    resolution : int
        Mesh density parameter.  The interior size bound is

            lc = 0.63 * sqrt(L² + H²) / resolution

    segments : int, optional
        Number of mesh edges around each circle circumference (default 32).
        Sets the mesh size on the circle boundary to ``2π*r/segments``.
        The legacy mshr Circle Python default is ``segments=0`` (auto-computed
        as ``round(2π*r / (2*R_bounding/resolution))``); for the standard
        cases here (r=0.2, R_bounding≈2.24, resolution=32) that yields ~9
        segments.  We use 32 as a conventional value that gives a smoother
        representation of the circle boundary.

    Returns
    -------
    msh : dolfinx.mesh.Mesh
    cell_tags : dolfinx.mesh.MeshTags   (fluid domain tag = 10)

    Note
    ----
    Facet tags are not produced here.  Call ``tag_boundaries(msh, L, H)``
    on the final mesh (after any refinement) to obtain boundary MeshTags.

    Grading strategy: a Distance+Threshold gmsh field grades each circle
    boundary smoothly from ``lc_circle = 2π*r/segments`` to the interior
    ``lc`` over a distance of ``r/4`` from the circle arc.  Setting
    ``Mesh.MeshSizeExtendFromBoundary = 0`` disables the default boundary
    extension so only the explicit field controls sizing.
    """
    _ALPHA = 0.63
    lc = _ALPHA * math.sqrt(L**2 + H**2) / resolution

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)

    rect = gmsh.model.occ.addRectangle(0.0, 0.0, 0.0, L, H)
    disks = [(2, gmsh.model.occ.addDisk(cx, cy, 0.0, r, r)) for cx, cy, r in circles]
    if disks:
        gmsh.model.occ.cut([(2, rect)], disks)
    gmsh.model.occ.synchronize()

    # Identify which curves are circle arcs by sampling their midpoints
    all_curves = gmsh.model.getEntities(1)
    circle_curve_tags = [[] for _ in circles]
    for dim, tag in all_curves:
        bounds = gmsh.model.getParametrizationBounds(dim, tag)
        mid = float(np.array(bounds).mean())
        x, y, _ = gmsh.model.getValue(dim, tag, [mid])
        for i, (cx, cy, r) in enumerate(circles):
            if abs(math.hypot(x - cx, y - cy) - r) < 0.15 * r:
                circle_curve_tags[i].append(tag)
                break

    # Distance+Threshold field: fine on circle arc, grades to lc over r/4
    bg_fields = []
    for i, (cx, cy, r) in enumerate(circles):
        lc_circle = 2.0 * math.pi * r / segments
        ctags = circle_curve_tags[i]
        if not ctags:
            continue
        d_id = 10 + 2 * i
        t_id = 11 + 2 * i
        gmsh.model.mesh.field.add("Distance", d_id)
        gmsh.model.mesh.field.setNumbers(d_id, "CurvesList", ctags)
        gmsh.model.mesh.field.add("Threshold", t_id)
        gmsh.model.mesh.field.setNumber(t_id, "InField", d_id)
        gmsh.model.mesh.field.setNumber(t_id, "SizeMin", lc_circle)
        gmsh.model.mesh.field.setNumber(t_id, "SizeMax", lc)
        gmsh.model.mesh.field.setNumber(t_id, "DistMin", 0.0)
        gmsh.model.mesh.field.setNumber(t_id, "DistMax", r / 4.0)
        bg_fields.append(t_id)

    if bg_fields:
        if len(bg_fields) == 1:
            gmsh.model.mesh.field.setAsBackgroundMesh(bg_fields[0])
        else:
            min_id = 10 + 2 * len(circles)
            gmsh.model.mesh.field.add("Min", min_id)
            gmsh.model.mesh.field.setNumbers(min_id, "FieldsList", bg_fields)
            gmsh.model.mesh.field.setAsBackgroundMesh(min_id)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

    gmsh.option.setNumber("Mesh.MeshSizeMax", lc)

    surfaces = gmsh.model.getEntities(2)
    gmsh.model.addPhysicalGroup(2, [s[1] for s in surfaces], tag=10, name="domain")

    gmsh.model.mesh.generate(2)

    mesh_data = gmshio.model_to_mesh(gmsh.model, MPI.COMM_WORLD, rank=0, gdim=2)
    gmsh.finalize()
    return mesh_data.mesh, mesh_data.cell_tags
