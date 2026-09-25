import sys
import pathlib
import basix.ufl as _bufl
from mpi4py import MPI
from dolfinx.io import XDMFFile
from dolfinx.fem import functionspace, Function


def _to_p1(f):
    """Interpolate f to P1 (scalar or vector) if needed."""
    V = f.function_space
    msh = V.mesh
    el = V.ufl_element()
    vshape = el.reference_value_shape
    if el.degree == 1:
        return f
    if vshape == ():
        V1 = functionspace(msh, ("Lagrange", 1))
    else:
        V1 = functionspace(msh, _bufl.element("Lagrange", msh.basix_cell(), 1, shape=vshape))
    f1 = Function(V1, name=f.name)
    f1.interpolate(f)
    return f1


class XDMFSeries:
    """Time-series XDMF writer.

    Opens one XDMFFile, writes the mesh once on the first write() call,
    then appends each time step.  Higher-degree functions are automatically
    interpolated to P1 before writing.

    Usage::

        xdmf = XDMFSeries("output/solution.xdmf")
        for t in ...:
            xdmf.write([u1, p1, w1], t)
        xdmf.close()          # or: `with XDMFSeries(...) as xdmf:`

    Parameters
    ----------
    path : str or Path
        Output ``.xdmf`` file path.  The ``.h5`` sidecar is written alongside.
    download : bool, optional
        If True *and* running on Colab, tar the pair and trigger a download
        when :meth:`close` is called.
    """

    def __init__(self, path, download=False):
        self._path = pathlib.Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._download = download
        self._xdmf = XDMFFile(MPI.COMM_WORLD, str(self._path), "w")
        self._mesh_written = False

    def write(self, funcs, t):
        """Write *funcs* at time *t*."""
        funcs_p1 = [_to_p1(f) for f in funcs]
        if not self._mesh_written:
            self._xdmf.write_mesh(funcs_p1[0].function_space.mesh)
            self._mesh_written = True
        for f in funcs_p1:
            self._xdmf.write_function(f, t)

    def close(self):
        """Close the file and optionally trigger a Colab download."""
        self._xdmf.close()
        if self._download and "google.colab" in sys.modules:
            import tarfile
            from google.colab import files as colab_files
            tar_path = str(self._path.with_suffix(".tar.gz"))
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(str(self._path), arcname=self._path.name)
                h5 = self._path.with_suffix(".h5")
                if h5.exists():
                    tar.add(str(h5), arcname=h5.name)
            colab_files.download(tar_path)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
