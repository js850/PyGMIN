cimport _pygmin

# use external c++ class
cdef extern from "lj.h" namespace "pygmin":
    cdef cppclass  cLJ "pygmin::LJ":
        cLJ(double eps, double sigma) except +

# we just need to set a different c++ class instance
cdef class LJ(_pygmin.Potential):
    def __cinit__(self, double sigma=1.0, double epsilon=1.0):
        self.thisptr = <_pygmin.cPotential*>new cLJ(sigma, epsilon)