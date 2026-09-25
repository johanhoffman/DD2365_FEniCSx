import numpy as np
import matplotlib.pyplot as plt
import basix.ufl as _bufl
from dolfinx.fem import functionspace, Function


def plot_mesh(msh, title="Mesh"):
    """Plot a 2-D triangular mesh using matplotlib triplot."""
    msh.topology.create_connectivity(msh.topology.dim, 0)
    x = msh.geometry.x
    gdm = msh.geometry.dofmaps[0]
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.triplot(x[:, 0], x[:, 1], gdm, linewidth=0.3, color="k")
    ax.set_aspect("equal")
    ax.set_title(title)
    plt.tight_layout()
    plt.show()


def _p1_scalar_space(msh):
    return functionspace(msh, ("Lagrange", 1))


def _scatter_p1_scalar(f1):
    """Scatter a P1 scalar Function values to geometry nodes.

    Returns (x, geometry_connectivity, node_values).
    """
    V = f1.function_space
    msh = V.mesh
    x = msh.geometry.x
    gdm = msh.geometry.dofmaps[0]
    ldm = V.dofmap.list
    vals = np.zeros(x.shape[0])
    vals[gdm.ravel()] = f1.x.array.real[ldm.ravel()]
    return x, gdm, vals


def plot_p1(u, title="Solution"):
    """Plot a P1 scalar Function using matplotlib tripcolor (Gouraud shading)."""
    plot_scalar(u, title=title)


def plot_scalar(f, title="Scalar field", ax=None):
    """Plot any scalar Lagrange Function via tripcolor (interpolates to P1 if needed).

    Parameters
    ----------
    f : dolfinx.fem.Function   scalar; any Lagrange degree
    title : str
    ax : matplotlib.axes.Axes or None
        If given, draw into this axes (no new figure, no plt.show()).
        If None (default), create a new figure and call plt.show().
    """
    V = f.function_space
    msh = V.mesh
    el = V.ufl_element()
    if el.degree == 1 and el.reference_value_shape == ():
        f1 = f
    else:
        f1 = Function(_p1_scalar_space(msh))
        f1.interpolate(f)
    x, gdm, vals = _scatter_p1_scalar(f1)
    _standalone = ax is None
    if _standalone:
        fig, ax = plt.subplots(figsize=(8, 3))
    tc = ax.tripcolor(x[:, 0], x[:, 1], gdm, vals, shading="gouraud")
    plt.colorbar(tc, ax=ax)
    ax.set_aspect("equal")
    ax.set_title(title)
    if _standalone:
        plt.tight_layout()
        plt.show()


def plot_vector(u, title="Vector field", quiver=True, quiver_stride=8, ax=None):
    """Plot a 2-D vector Lagrange Function as colour map of |u| + optional quiver.

    Parameters
    ----------
    u : dolfinx.fem.Function   value shape (2,); any Lagrange degree
    title : str
    quiver : bool              overlay subsampled arrows (default True)
    quiver_stride : int        take every N-th mesh node for arrows
    ax : matplotlib.axes.Axes or None
        If given, draw into this axes (no new figure, no plt.show()).
        If None (default), create a new figure and call plt.show().
    """
    msh = u.function_space.mesh
    gdim = msh.geometry.dim
    x = msh.geometry.x
    gdm = msh.geometry.dofmaps[0]
    npts = x.shape[0]

    # Interpolate to P1 vector so values align with geometry nodes
    V1v = functionspace(msh, _bufl.element("Lagrange", msh.basix_cell(), 1, shape=(gdim,)))
    u1v = Function(V1v)
    u1v.interpolate(u)

    # Scatter: for a block-size-2 P1 space, dofmap.list gives block indices
    ldm = V1v.dofmap.list      # (ncells, 3)  — block indices
    arr = u1v.x.array.real     # length npts * gdim, interleaved per block
    ux = np.zeros(npts)
    uy = np.zeros(npts)
    ux[gdm.ravel()] = arr[ldm.ravel() * gdim + 0]
    uy[gdm.ravel()] = arr[ldm.ravel() * gdim + 1]
    mag = np.sqrt(ux**2 + uy**2)

    _standalone = ax is None
    if _standalone:
        fig, ax = plt.subplots(figsize=(8, 3))
    tc = ax.tripcolor(x[:, 0], x[:, 1], gdm, mag, shading="gouraud", cmap="viridis")
    plt.colorbar(tc, ax=ax, label="|u|")
    if quiver:
        idx = np.arange(0, npts, quiver_stride)
        ax.quiver(x[idx, 0], x[idx, 1], ux[idx], uy[idx],
                  color="white", alpha=0.6, width=0.002, scale_units="xy", scale=2.0)
    ax.set_aspect("equal")
    ax.set_title(title)
    if _standalone:
        plt.tight_layout()
        plt.show()
