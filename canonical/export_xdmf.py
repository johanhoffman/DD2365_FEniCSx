import sys
import pathlib
import basix.ufl as _bufl
from mpi4py import MPI
from dolfinx.io import XDMFFile
from dolfinx.fem import functionspace, Function


def _to_p1(f):
    """Interpolate f to P1 (scalar or vector) if needed.

    XDMF only reliably stores P1 Lagrange data; higher-degree functions (e.g.
    P2 velocity from Taylor-Hood) must be projected to P1 before export so that
    ParaView can read the file without geometry/value mismatches.
    """
    V = f.function_space
    msh = V.mesh
    el = V.ufl_element()
    vshape = el.reference_value_shape  # () for scalar, (2,) for vector
    if el.degree == 1:
        return f
    if vshape == ():
        V1 = functionspace(msh, ("Lagrange", 1))
    else:
        V1 = functionspace(msh, _bufl.element("Lagrange", msh.basix_cell(), 1, shape=vshape))
    f1 = Function(V1, name=f.name)
    f1.interpolate(f)
    return f1


def export_xdmf(path, funcs, download=False):
    """Export a list of Functions to XDMF for ParaView.

    Higher-degree functions (P2, mixed sub-functions, etc.) are automatically
    interpolated to P1 before writing — XDMF stores values at mesh nodes and
    ParaView cannot reliably read nodal data for higher-order Lagrange elements.

    Parameters
    ----------
    path : str or Path
        Output .xdmf file path (an .h5 sidecar is written alongside it).
    funcs : list of dolfinx.fem.Function
        Functions to export (must share the same mesh).
    download : bool, optional
        If True *and* running on Colab, tar the .xdmf/.h5 pair and trigger
        a browser download.  Default False.
    """
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    funcs_p1 = [_to_p1(f) for f in funcs]
    with XDMFFile(MPI.COMM_WORLD, str(path), "w") as xdmf:
        if funcs_p1:
            xdmf.write_mesh(funcs_p1[0].function_space.mesh)
        for f in funcs_p1:
            xdmf.write_function(f)
    if download and "google.colab" in sys.modules:
        import tarfile
        from google.colab import files as colab_files
        tar_path = str(path.with_suffix(".tar.gz"))
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(str(path), arcname=path.name)
            h5 = path.with_suffix(".h5")
            if h5.exists():
                tar.add(str(h5), arcname=h5.name)
        colab_files.download(tar_path)
