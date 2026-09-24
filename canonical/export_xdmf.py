import sys
import pathlib
from mpi4py import MPI
from dolfinx.io import XDMFFile


def export_xdmf(path, funcs, download=False):
    """Export a list of Functions to XDMF for ParaView.

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
    with XDMFFile(MPI.COMM_WORLD, str(path), "w") as xdmf:
        if funcs:
            xdmf.write_mesh(funcs[0].function_space.mesh)
        for f in funcs:
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
