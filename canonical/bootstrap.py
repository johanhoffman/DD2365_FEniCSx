import sys, os

_on_colab = "google.colab" in sys.modules

if not _on_colab:
    os.environ.setdefault("OMP_NUM_THREADS", "1")

if _on_colab:
    try:
        import gmsh
    except ImportError:
        os.system(
            'wget -q "https://fem-on-colab.github.io/releases/gmsh-install.sh"'
            ' -O /tmp/gmsh-install.sh && bash /tmp/gmsh-install.sh'
        )
    try:
        import dolfinx
    except ImportError:
        os.system(
            'wget -q "https://fem-on-colab.github.io/releases/fenicsx-install-release-real.sh"'
            ' -O /tmp/fenicsx-install.sh && bash /tmp/fenicsx-install.sh'
        )

import dolfinx
print("dolfinx version:", dolfinx.__version__)

if _on_colab:
    from google.colab import files
