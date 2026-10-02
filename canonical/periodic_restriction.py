"""
Periodic boundary condition via algebraic restriction matrix (serial only).

periodic_restriction(V, x_target, x_source, tol=1e-12) -> (P, n_red)
  P : PETSc AIJ matrix (n_full x n_red).  Each non-source dof maps to itself
      (identity column), each source dof maps to its matched target dof column.
  n_red : number of columns in P = number of independent dofs after periodicity.

reduce_system(A, b, P) -> (Ar, br)
  Ar = P^T A P  (via MatPtAP),  br = P^T b.

expand_solution(x_r, P) -> x_full
  x_full = P x_r.  Source dofs automatically receive the value of their target.

dof_map(P) -> np.ndarray shape (n_full,)
  full_to_red[i] = column index (reduced dof) for full dof i.
  Call once at setup; use numpy indexing to map Dirichlet full dofs to reduced.

apply_dirichlet_reduced(Ar, br, bc_red_dofs, bc_red_vals)
  Zero rows/cols, unit diagonal, lifted RHS in the reduced system.
  Pass deduplicated reduced-space dofs and their prescribed values.
"""

import numpy as np
from petsc4py import PETSc


def periodic_restriction(V, x_target, x_source, tol=1e-12):
    """
    Build restriction matrix P for x-periodicity; assert serial.

    Source nodes (x ≈ x_source) are identified with target nodes (x ≈ x_target)
    by matching the remaining coordinates within tol, per block component.
    Corner nodes that are both periodic and Dirichlet must carry the same
    prescribed value on both sides (checked in apply_dirichlet_reduced by the
    fact that both map to the same reduced dof).

    Returns (P, n_red).
    """
    assert V.mesh.comm.size == 1, "periodic_restriction: serial only"

    bs     = V.dofmap.bs                         # block size (1 scalar, 2 vector, …)
    coords = V.tabulate_dof_coordinates()        # (n_nodes, 3)  one row per block-node
    n_nodes = coords.shape[0]
    n_full  = n_nodes * bs

    # Build per-component maps: maps[c][node] -> full scalar dof index
    if bs == 1:
        maps = [np.arange(n_nodes, dtype=np.int64)]
    else:
        maps = []
        for c in range(bs):
            _, mc = V.sub(c).collapse()
            maps.append(np.array(mc, dtype=np.int64).ravel())

    # Identify source nodes (x ≈ x_source) and target nodes (x ≈ x_target)
    src_idx = np.where(np.abs(coords[:, 0] - x_source) < tol)[0]
    tgt_idx = np.where(np.abs(coords[:, 0] - x_target) < tol)[0]
    tgt_y   = coords[tgt_idx, 1]

    # Match each source node to the target node with the same y-coordinate
    node_pair = {}                               # source_node -> target_node
    for s in src_idx:
        diff = np.abs(tgt_y - coords[s, 1])
        j    = int(np.argmin(diff))
        if diff[j] > tol:
            raise RuntimeError(
                f"periodic_restriction: no target match for source node at y={coords[s,1]:.6g}"
            )
        node_pair[int(s)] = int(tgt_idx[j])

    src_set = set(node_pair)

    # Assign reduced node indices: non-source nodes in order, source -> target's index
    node_to_red = {}
    r = 0
    for n in range(n_nodes):
        if n not in src_set:
            node_to_red[n] = r; r += 1
    for s, t in node_pair.items():
        node_to_red[s] = node_to_red[t]          # source shares target's reduced index
    n_red = r * bs

    # Map every full scalar dof to its reduced dof
    full_to_red = np.empty(n_full, dtype=np.int64)
    for comp, mp in enumerate(maps):
        for nd in range(n_nodes):
            full_to_red[int(mp[nd])] = node_to_red[nd] * bs + comp

    # Build P: one nonzero per row
    P = PETSc.Mat().createAIJ([n_full, n_red], nnz=1, comm=PETSc.COMM_SELF)
    P.setUp()
    for row in range(n_full):
        P.setValue(int(row), int(full_to_red[row]), 1.0)
    P.assemblyBegin()
    P.assemblyEnd()
    return P, n_red


def reduce_system(A, b, P):
    """Compute Ar = P^T A P (MatPtAP) and br = P^T b."""
    Ar = A.ptap(P)
    br = P.createVecRight()          # length n_red
    P.multTranspose(b, br)           # br = P^T b
    return Ar, br


def expand_solution(x_r, P):
    """Compute x_full = P x_r."""
    x_full = P.createVecLeft()       # length n_full
    P.mult(x_r, x_full)
    return x_full


def dof_map(P):
    """
    Return full_to_red array: full_to_red[i] = reduced dof index for full dof i.
    O(n_full); call once at setup, not in the time loop.
    """
    n_full, _ = P.getSize()
    f2r = np.empty(n_full, dtype=np.int32)
    for i in range(n_full):
        cols, _ = P.getRow(i)
        f2r[i] = int(cols[0])
    return f2r


def apply_dirichlet_reduced(Ar, br, bc_red_dofs, bc_red_vals):
    """
    Apply Dirichlet BCs in the reduced system.
    Zero rows/cols, unit diagonal, lifted RHS (standard penalty-free approach).

    bc_red_dofs : list/array of reduced-space dof indices (deduplicated).
    bc_red_vals : corresponding prescribed values.
    """
    n_red = Ar.getSize()[0]

    # Dirichlet value vector in reduced space
    u_D = PETSc.Vec().createSeq(n_red, comm=PETSc.COMM_SELF)
    u_D.set(0.0)
    for r, v in zip(bc_red_dofs, bc_red_vals):
        u_D.setValue(int(r), float(v))
    u_D.assemblyBegin(); u_D.assemblyEnd()

    # zeroRowsColumns zeros row r and col r, sets diag=1, and lifts br:
    #   br[j] -= Ar[j,r] * u_D[r]  for j != r,  br[r] = u_D[r] * diag
    Ar.zeroRowsColumns([int(r) for r in bc_red_dofs], diag=1.0, x=u_D, b=br)
