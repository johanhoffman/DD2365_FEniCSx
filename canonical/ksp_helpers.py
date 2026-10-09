from petsc4py import PETSc


def make_ksp(A, ksp_type="bcgs", pc_type="ilu", amg=False, rtol=1e-6, atol=1e-14, max_it=500):
    ksp = PETSc.KSP().create(A.comm)
    ksp.setOperators(A)
    ksp.setType(ksp_type)
    pc = ksp.getPC()
    if amg:
        pc.setType("hypre")
        pc.setHYPREType("boomeramg")
    else:
        pc.setType(pc_type)
    ksp.setTolerances(rtol=rtol, atol=atol, max_it=max_it)
    ksp.setFromOptions()
    return ksp


def solve_checked(ksp, b, x, name):
    ksp.solve(b, x)
    reason = ksp.getConvergedReason()
    iters = ksp.getIterationNumber()
    if reason < 0:
        raise RuntimeError(
            f"KSP '{name}' diverged: reason={reason}, iterations={iters}"
        )


def solve_checked_snes(snes, name):
    reason = snes.getConvergedReason()
    if reason <= 0:
        iters = snes.getIterationNumber()
        raise RuntimeError(
            f"SNES '{name}' did not converge: reason={reason}, iterations={iters}"
        )
