import sys
import pathlib
from mpi4py import MPI
from dolfinx.io import XDMFFile


def export_xdmf(path, funcs):
    """Export a list of Functions to XDMF for ParaView.

    On Colab, tars the .xdmf/.h5 pair and triggers a browser download.
    """
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with XDMFFile(MPI.COMM_WORLD, str(path), "w") as xdmf:
        if funcs:
            xdmf.write_mesh(funcs[0].function_space.mesh)
        for f in funcs:
            xdmf.write_function(f)
    if "google.colab" in sys.modules:
        import tarfile
        from google.colab import files as colab_files
        tar_path = str(path.with_suffix(".tar.gz"))
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(str(path), arcname=path.name)
            h5 = path.with_suffix(".h5")
            if h5.exists():
                tar.add(str(h5), arcname=h5.name)
        colab_files.download(tar_path)
