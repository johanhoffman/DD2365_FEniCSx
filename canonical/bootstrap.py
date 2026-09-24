import sys, os, subprocess

_on_colab = "google.colab" in sys.modules

if not _on_colab:
    os.environ.setdefault("OMP_NUM_THREADS", "1")

if _on_colab:
    try:
        import gmsh
    except ImportError:
        subprocess.run(
            'wget -q "https://fem-on-colab.github.io/releases/gmsh-install.sh"'
            ' -O /tmp/gmsh-install.sh && bash /tmp/gmsh-install.sh',
            shell=True, check=True,
        )
    try:
        import dolfinx
    except ImportError:
        subprocess.run(
            'wget -q "https://fem-on-colab.github.io/releases/fenicsx-install-release-real.sh"'
            ' -O /tmp/fenicsx-install.sh && bash /tmp/fenicsx-install.sh',
            shell=True, check=True,
        )

import dolfinx
print("dolfinx version:", dolfinx.__version__)

if _on_colab:
    from google.colab import files
