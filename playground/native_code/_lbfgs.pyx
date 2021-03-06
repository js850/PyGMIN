import numpy as np
cimport numpy as np
from playground.native_code import _pygmin
cimport _pygmin


cdef extern from "lbfgs_wrapper.cpp" namespace "pygmin":
    cdef cppclass cLBFGS "pygmin::LBFGS":
        cLBFGS() except +
        cLBFGS(_pygmin.cPotential *) except +
        #
        int run(_pygmin.Array &x)

        const char * error_string()
        int error_code()

# we just need to set a different c++ class instance
cdef class LBFGS:
    cdef cLBFGS *thisptr
    cdef _pygmin.Potential pot
    
    def __cinit__(self, _pygmin.Potential pot):
        self.thisptr = <cLBFGS*>new cLBFGS(pot.thisptr)
        self.pot = pot
        
    def __dealloc__(self):
        del self.thisptr
        
    def run(self, np.ndarray[double, ndim=1, mode="c"] x not None):
        ret = self.thisptr.run(_pygmin.Array(<double*> x.data, x.size))
        if ret != 0 and ret != -1001: # ignore rounding errors
            raise RuntimeError("lbfgs failed with error code %d:"%self.thisptr.error_code(), self.thisptr.error_string())
        e, g = self.pot.get_energy_gradient(x)
        return x, e, np.linalg.norm(g) / np.sqrt(g.size), -1
        
