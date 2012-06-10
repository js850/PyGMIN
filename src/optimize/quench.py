import numpy as np
import scipy.optimize

"""
wrappers for the various optimizers.

The options for the optimizers differ, so you'll have to write 
your own wrapper if want fine grained control

we should make this consistent with scipy
scipy.minimize would do a similar thing
"""

class getEnergyGradientWrapper:
    """
    return either the energy or gradient, not both.  This is quite wasteful
    """
    def __init__(self, getEnergyGradient):
        self. getEnergyGradient = getEnergyGradient
    def getEnergy(self, coords):
        e, g = self.getEnergyGradient(coords)
        return e
    def getGradient( self, coords ):
        e, g = self.getEnergyGradient(coords)
        return g


def quench(coords, getEnergyGradient, iprint = -1, tol = 1e-3):
    """
    a wrapper function for lbfgs routine in scipy
    """
    newcoords, newE, dictionary = scipy.optimize.fmin_l_bfgs_b(getEnergyGradient, coords, iprint=iprint, pgtol=tol)
    V = dictionary["grad"]
    funcalls = dictionary["funcalls"]
    warnflag = dictionary['warnflag']
    if warnflag > 0:
        print "warning: problem with quench: ",
        if warnflag == 1:
            print "too many function evaluations"
        else:
            print dictionary['task']
    rms = V.std()
    return newcoords, newE, rms, funcalls 

def fire(coords, getEnergyGradient, iprint = -1, tol = 1e-3):
    import fire as fire
    import numpy as np
    opt = fire.Fire(coords, getEnergyGradient)
    opt.run()
    e,g = getEnergyGradient(opt.coords)
    rms = np.linalg.norm(g)/np.sqrt(len(g))
    return opt.coords, e, rms, opt.nsteps

def cg(coords, getEnergyGradient, iprint = -1, tol = 1e-3):
    """
    a wrapper function for conjugate gradient routine in scipy
    """
    pot = getEnergyGradientWrapper(getEnergyGradient)
    ret = scipy.optimize.fmin_cg(pot.getEnergy, coords, pot.getGradient, gtol=tol, full_output = True)
    newcoords = ret[0]
    #e = ret[1]
    funcalls = ret[2]
    funcalls += ret[3] #calls to gradient
    warnflag = ret[4]
    if warnflag > 0:
        print "warning: problem with quench: ",
        if warnflag == 1:
            print "Maximum number of iterations exceeded"
        if warnflag == 2:
            print "Gradient and/or function calls not changing"
    e,g = getEnergyGradient(newcoords)
    rms = np.linalg.norm(g)/np.sqrt(len(g))
    return newcoords, e, rms, funcalls 

def fmin(coords, getEnergyGradient, iprint = -1, tol = 1e-3):
    """
    a wrapper function for fmin routine in scipy
    
    This algorithm only uses function values, not derivatives or second derivatives.
    """
    pot = getEnergyGradientWrapper(getEnergyGradient)  #this is really stupid
    ret = scipy.optimize.fmin(pot.getEnergy, coords, ftol=tol, full_output = True)
    newcoords = ret[0]
    #e = ret[1]
    funcalls = ret[2]
    warnflag = ret[4]
    if warnflag > 0:
        print "warning: problem with quench: ",
        if warnflag == 1:
            print "Maximum number of function evaluations made."
        if warnflag == 2:
            print "Maximum number of iterations reached."
    e,g = getEnergyGradient(newcoords)  #should I use gradient here?  It seems kind of dumb
    rms = np.linalg.norm(g)/np.sqrt(len(g))
    return newcoords, e, rms, funcalls 

def lbfgs_ase(coords, getEnergyGradient, iprint = -1, tol = 1e-3):
    import fire as fire
    import numpy as np
    opt = fire.Fire(coords, getEnergyGradient)
    opt.run()
    e,g = getEnergyGradient(opt.coords)
    rms = np.linalg.norm(g)/np.sqrt(len(g))
    return opt.coords, e, rms, opt.nsteps


def _steepest_descent(x0, getEnergyGradient, iprint = -1, dx = 1e-4, nsteps = 100000, gtol = 1e-3, maxstep = -1.):
    N = len(x0)
    x=x0.copy()
    E, V = getEnergyGradient(x)
    funcalls = 1
    for k in xrange(nsteps):
        stp = -V * dx
        if maxstep > 0:
            stpsize = np.max(np.abs(V))
            if stpsize > maxstep:
                stp *= maxstep / stpsize                
        x += stp
        E, V = getEnergyGradient(x)
        funcalls += 1
        rms = np.linalg.norm(V)/np.sqrt(N)
        if iprint > 0:
            if funcalls % iprint == 0: 
                print "step %8d energy %20.12g rms gradient %20.12g" % (funcalls, E, rms)
        if rms < gtol:
            break
    return x, E, rms, funcalls

def steepest_descent(coords, getEnergyGradient, iprint = -1, tol = 1e-3):
    return _steepest_descent(coords, getEnergyGradient, iprint = iprint, gtol = tol)

def bfgs(coords, getEnergyGradient, iprint = -1, tol = 1e-3):
    pot = getEnergyGradientWrapper(getEnergyGradient)
    ret = scipy.optimize.fmin_bfgs(pot.getEnergy, coords, fprime = pot.getGradient, gtol = tol, full_output = True, disp=False)
    x = ret[0]
    E = ret[1]
    g = ret[2]
    rms = np.linalg.norm(g)/np.sqrt(len(g))
    funcalls = ret[4] + ret[5]
    return x, E, rms, funcalls


def _lbfgs_py(coords, pot, nsteps = 1e6, iprint = -1, tol = 1e-3, maxstep = 0.1, maxErise = 1e-4, M=10):
    from lbfgs_py import LBFGS
    lbfgs = LBFGS(coords, pot, maxstep = maxstep, maxErise = maxErise)
    
    ret = lbfgs.run(nsteps, tol, iprint)
    coords = ret[0]
    e = ret[1]
    rms = ret[2]
    funcalls = ret[3]
    return coords, e, rms, funcalls

def lbfgs_py(coords, getEnergyGradient, iprint = -1, tol = 1e-3, maxstep = 0.1):
    pot = getEnergyGradientWrapper(getEnergyGradient)
    ret = _lbfgs_py(coords, pot, iprint = iprint, tol = tol, maxstep = maxstep)
    return ret

