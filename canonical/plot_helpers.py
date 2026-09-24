import numpy as np
import matplotlib.pyplot as plt


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


def plot_p1(u, title="Solution"):
    """Plot a P1 scalar Function using matplotlib tripcolor (Gouraud shading)."""
    V = u.function_space
    msh = V.mesh
    x = msh.geometry.x
    gdm = msh.geometry.dofmaps[0]  # geometry connectivity (ncells, 3)
    ldm = V.dofmap.list             # DOF map (ncells, 3)
    vals = np.zeros(x.shape[0])
    vals[gdm.ravel()] = u.x.array.real[ldm.ravel()]
    fig, ax = plt.subplots(figsize=(8, 3))
    tc = ax.tripcolor(x[:, 0], x[:, 1], gdm, vals, shading="gouraud")
    plt.colorbar(tc, ax=ax)
    ax.set_aspect("equal")
    ax.set_title(title)
    plt.tight_layout()
    plt.show()
