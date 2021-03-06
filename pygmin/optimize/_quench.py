"""
wrappers for the various optimizers.

warning: we've tried to make the most common options the same but there are still differences 

we should make this consistent with scipy.
scipy.minimize would do a similar thing
"""

import numpy as np

from pygmin.optimize import LBFGS, MYLBFGS, Fire, Result
from pygmin.potentials import BasePotential

__all__ = ["lbfgs_scipy", "fire", "lbfgs_py", "mylbfgs", "cg", 
           "steepest_descent", "bfgs_scipy"]

class _getEnergyGradientWrapper(BasePotential):
    """
    create a potential object from getEnergyGradient.  This is quite wasteful
    """
    def __init__(self, getEnergyGradient):
        self.get_e_g = getEnergyGradient
#        print "warning: the minimizer usage has changed, please pass a potential object not the function getEnergyGradient"
    def getEnergy(self, coords):
        e, g = self.get_e_g(coords)
        return e
    def getEnergyGradient(self, coords):
        return self.get_e_g(coords)

def lbfgs_scipy(coords, pot, iprint=-1, tol=1e-3, nsteps=15000):
    """
    a wrapper function for lbfgs routine in scipy
    
    .. warn::
        the scipy version of lbfgs uses linesearch based only on energy
        which can make the minimization stop early.  When the step size
        is so small that the energy doesn't change to within machine precision (times the
        parameter `factr`) the routine declares success and stops.  This sounds fine, but
        if the gradient is analytical the gradient can still be not converged.  This is
        because in the vicinity of the minimum the gradient changes much more rapidly then
        the energy.  Thus we want to make factr as small as possible.  Unfortunately,
        if we make it too small the routine realizes that the linesearch routine
        isn't working and declares failure and exits.
        
        So long story short, if your tolerance is very small (< 1e-6) this routine
        will probably stop before truly reaching that tolerance.  If you reduce `factr` 
        too much to mitigate this lbfgs will stop anyway, but declare failure misleadingly.  
    """
    if not hasattr(pot, "getEnergyGradient"):
        # for compatibility with old quenchers.
        # assume pot is a getEnergyGradient function
        pot = _getEnergyGradientWrapper(pot)
    import scipy.optimize
    res = Result()
    res.coords, res.energy, dictionary = scipy.optimize.fmin_l_bfgs_b(pot.getEnergyGradient, 
            coords, iprint=iprint, pgtol=tol, maxfun=nsteps, factr=10.)
    res.grad = dictionary["grad"]
    res.nfev = dictionary["funcalls"]
    warnflag = dictionary['warnflag']
    #res.nsteps = dictionary['nit'] #  new in scipy version 0.12
    res.nsteps = res.nfev
    res.message = dictionary['task']
    res.success = True
    if warnflag > 0:
        print "warning: problem with quench: ",
        res.success = False
        if warnflag == 1:
            res.message = "too many function evaluations"
        else:
            res.message = str(dictionary['task'])
        print res.message
    #note: if the linesearch fails the lbfgs may fail without setting warnflag.  Check
    #tolerance exactly
    if False:
        if res.success:
            maxV = np.max( np.abs(res.grad) )
            if maxV > tol:
                print "warning: gradient seems too large", maxV, "tol =", tol, ". This is a known, but not understood issue of scipy_lbfgs"
                print res.message
    res.rms = res.grad.std()
    return res

def fire(coords, pot, tol=1e-3, nsteps=100000, **kwargs):
    """
    A wrapper function for the pygmin FIRE implementation
    """
    if not hasattr(pot, "getEnergyGradient"):
        # for compatibility with old quenchers.
        # assume pot is a getEnergyGradient function
        pot = _getEnergyGradientWrapper(pot)
    opt = Fire(coords, pot, **kwargs)
    res = opt.run(fmax=tol, steps=nsteps)
    return res

def cg(coords, pot, iprint=-1, tol=1e-3, nsteps=5000, **kwargs):
    """
    a wrapper function for conjugate gradient routine in scipy
    """
    if not hasattr(pot, "getEnergyGradient"):
        # for compatibility with old quenchers.
        # assume pot is a getEnergyGradient function
        pot = _getEnergyGradientWrapper(pot)
    import scipy.optimize
    ret = scipy.optimize.fmin_cg(pot.getEnergy, coords, pot.getGradient, 
                                 gtol=tol, full_output=True, disp=iprint>0, 
                                 maxiter=nsteps, **kwargs)
    res = Result()
    res.coords = ret[0]
    #e = ret[1]
    res.nfev = ret[2]
    res.nfev += ret[3] #calls to gradient
    res.success = True
    warnflag = ret[4]
    if warnflag > 0:
#        print "warning: problem with quench: ",
        res.success = False
        if warnflag == 1:
            res.message = "Maximum number of iterations exceeded"
        if warnflag == 2:
            print "Gradient and/or function calls not changing"
    res.energy, res.grad = pot.getEnergyGradient(res.coords)
    g = res.grad
    res.rms = np.linalg.norm(g)/np.sqrt(len(g))
    return res 


def steepest_descent(x0, pot, iprint=-1, dx=1e-4, nsteps=100000,
                      tol=1e-3, maxstep=-1., event=None):
    if not hasattr(pot, "getEnergyGradient"):
        # for compatibility with old quenchers.
        # assume pot is a getEnergyGradient function
        pot = _getEnergyGradientWrapper(pot)
    N = len(x0)
    x=x0.copy()
    E, V = pot.getEnergyGradient(x)
    funcalls = 1
    for k in xrange(nsteps):
        stp = -V * dx
        if maxstep > 0:
            stpsize = np.max(np.abs(V))
            if stpsize > maxstep:
                stp *= maxstep / stpsize                
        x += stp
        E, V = pot.getEnergyGradient(x)
        funcalls += 1
        rms = np.linalg.norm(V)/np.sqrt(N)
        if iprint > 0:
            if funcalls % iprint == 0: 
                print "step %8d energy %20.12g rms gradient %20.12g" % (funcalls, E, rms)
        if event != None:
            event(E, x, rms)
        if rms < tol:
            break
    res = Result()
    res.coords = x
    res.energy = E
    res.rms = rms
    res.grad = V
    res.nfev = funcalls
    res.nsteps = k
    res.success = res.rms <= tol 
    return res

def bfgs_scipy(coords, pot, iprint=-1, tol=1e-3, nsteps=5000, **kwargs):
    """
    a wrapper function for the scipy BFGS algorithm
    """
    if not hasattr(pot, "getEnergyGradient"):
        # for compatibility with old quenchers.
        # assume pot is a getEnergyGradient function
        pot = _getEnergyGradientWrapper(pot)
    import scipy.optimize
    ret = scipy.optimize.fmin_bfgs(pot.getEnergy, coords, fprime=pot.getGradient,
                                   gtol=tol, full_output=True, disp=iprint>0, 
                                   maxiter=nsteps, **kwargs)
    res = Result()
    res.coords = ret[0]
    res.energy = ret[1]
    res.grad = ret[2]
    res.rms = np.linalg.norm(res.grad) / np.sqrt(len(res.grad))
    res.nfev = ret[4] + ret[5]
    res.nsteps = res.nfev #  not correct, but no better information
    res.success = np.max(np.abs(res.grad)) < tol
    return res

def lbfgs_py(coords, pot, **kwargs):
    if not hasattr(pot, "getEnergyGradient"):
        # for compatibility with old quenchers.
        # assume pot is a getEnergyGradient function
        pot = _getEnergyGradientWrapper(pot)
    lbfgs = LBFGS(coords, pot, **kwargs)    
    return lbfgs.run()

def mylbfgs(coords, pot, **kwargs):
    if not hasattr(pot, "getEnergyGradient"):
        # for compatibility with old quenchers.
        # assume pot is a getEnergyGradient function
        pot = _getEnergyGradientWrapper(pot)
    lbfgs = MYLBFGS(coords, pot, **kwargs)
    return lbfgs.run()


import unittest
class TestMinimizers(unittest.TestCase):
    def setUp(self):
        from pygmin.systems import LJCluster
        natoms = 31
        self.system = LJCluster(natoms)
        self.pot = self.system.get_potential()
        
        # get a partially minimized structure
        x0 = self.system.get_random_configuration()
        ret = lbfgs_py(x0, self.pot, tol=1e-1)
        self.x0 = ret.coords.copy()
        self.E0 = ret.energy
        
        ret = lbfgs_py(self.x0, self.pot, tol=1e-7)
        self.x = ret.coords.copy()
        self.E = ret.energy
    
    def check_attributes(self, res):
        self.assertTrue(hasattr(res, "energy"))
        self.assertTrue(hasattr(res, "coords"))
        self.assertTrue(hasattr(res, "nsteps"))
        self.assertTrue(hasattr(res, "nfev"))
        self.assertTrue(hasattr(res, "rms"))
        self.assertTrue(hasattr(res, "grad"))
        self.assertTrue(hasattr(res, "success"))
    
    def test_lbfgs_py(self):
        res = lbfgs_py(self.x0, self.pot, tol=1e-7)
        self.assertTrue(res.success)
        self.assertAlmostEqual(self.E, res.energy, 4)
        self.check_attributes(res)
        
    def test_mylbfgs(self):
        res = mylbfgs(self.x0, self.pot, tol=1e-7)
        self.assertTrue(res.success)
        self.assertAlmostEqual(self.E, res.energy, 4)
        self.check_attributes(res)
    
    def test_fire(self):
        res = fire(self.x0, self.pot, tol=1e-7)
        self.assertTrue(res.success)
        self.assertAlmostEqual(self.E, res.energy, 4)
        self.check_attributes(res)
    
    def test_lbfgs_scipy(self):
        res = lbfgs_scipy(self.x0, self.pot, tol=1e-7)
        self.assertTrue(res.success)
        self.assertAlmostEqual(self.E, res.energy, 4)
        self.check_attributes(res)
    
    def test_bfgs_scipy(self):
        res = bfgs_scipy(self.x0, self.pot, tol=1e-7)
        self.assertTrue(res.success)
        self.assertAlmostEqual(self.E, res.energy, 4)
        self.check_attributes(res)
        
        
if __name__ == "__main__":
    unittest.main()
#    from pygmin.systems import LJCluster
#    system = LJCluster(13)
#    pot = system.get_potential()
#    coords = system.get_random_configuration()
#    res = lbfgs_scipy(coords, pot)
#    res = lbfgs_scipy(coords, pot.getEnergyGradient)
#    x, e, rms, nfev, res = lbfgs_scipy(coords, pot)
#    print "quench success", res.success
        