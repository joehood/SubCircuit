"""Quantized DEVS-LIM modeling and simulation framework.
"""

from math import pi    as PI   
from math import sin   as SIN  
from math import cos   as COS  
from math import acos  as ACOS 
from math import tan   as TAN  
from math import acos  as ACOS 
from math import atan2 as ATAN2
from math import sqrt  as SQRT 
from math import floor as FLOOR

from collections import OrderedDict as odict
from array import array

import pandas as pd

import numpy as np
import numpy.linalg as la

from mpl_toolkits import mplot3d
import matplotlib as mpl
import matplotlib.pyplot as plt
mpl.rc('axes.formatter', useoffset=False)

from scipy.integrate import solve_ivp
from scipy.optimize import fsolve
from scipy.interpolate import interp1d
from scipy.stats import gaussian_kde

import sympy as sp
from sympy import sin, cos, tan, atan2, acos, pi, sqrt
from sympy.solvers import solve
from sympy.utilities.lambdify import lambdify, implemented_function


# ============================ Private Constants ===============================


_EPS = 1.0e-15
_INF = float('inf')
_MAXITER = 1000


# ============================ Public Constants ================================


#DEF_DQ = 1.0e-6        # default delta Q
#DEF_DQMIN = 1.0e-6     # default minimum delta Q (for dynamic dq mode)
#DEF_DQMAX = 1.0e-6     # default maximum delta Q (for dynamic dq mode)
#DEF_DQERR = 1.0e-2     # default delta Q absolute error (for dynamic dq mode)
DEF_DTMIN = 1.0e-12    # default minimum time step
DEF_DMAX = 1.0e5       # default maximum derivative (slew-rate)

PI_4 = float(pi / 4.0)
PI_3 = float(pi / 3.0)
PI5_6 = float(5.0 * pi / 6.0)
PI7_6 = float(7.0 * pi / 6.0)



# =============================== Globals ======================================


sys = None  # set by qdl.System constructor for visibility from fode function.


# ============================= Enumerations ===================================


class SourceType:

    NONE = "NONE"
    CONSTANT = "CONSTANT"
    STEP = "STEP"
    SINE = "SINE"
    PWM = "PWM"
    RAMP = "RAMP"
    FUNCTION = "FUNCTION"


# ============================= Qdl Model ======================================


def print_matrix_dots(m):
    s = ""
    for i in m.size(0):
        for j in m.size(1):
            if m[i,j]:
                s += "x"
            else:
                s += " "
        s += "\n"
    print(s)


class Atom(object):

    def __init__(self, name, x0=0.0, dq=None, dqmin=None, dqmax=None,
                 dqerr=None, dtmin=None, dmax=1e10, units=""):

        # params:

        self.name = name
        self.x0 = x0
        self.dq = dq
        self.dqmin = dqmin
        self.dqmax = dqmax
        self.dqerr = dqerr
        self.dtmin = dtmin
        self.dmax = dmax 
        self.units = units

        # simulation variables:

        self.dq0 = self.dq
        self.qlo = 0.0   
        self.qhi = 0.0 
        self.time = 0.0
        self.tlast = 0.0  
        self.tnext = 0.0  
        self.x = x0    
        self.d = 0.0      
        self.d0 = 0.0     
        self.q = x0      
        self.q0 = x0     
        self.triggered = False

        # results data storage:

        # qss:
        self.tout = None  # output times quantized output
        self.qout = None  # quantized output 
        self.tzoh = None  # zero-order hold output times quantized output
        self.qzoh = None  # zero-order hold quantized output 
        self.updates = 0  # qss updates

        # state space:
        self.tout_ss = None  # state space time output
        self.xout_ss = None  # state space value output
        self.updates_ss = 0  # state space update count

        # non-linear ode:
        self.tout_ode = None  # state space time output
        self.xout_ode = None  # state space value output
        self.updates_ode = 0  # state space update count

        # atom connections:

        self.broadcast_to = []  # push updates to
        self.connections = []   # recieve updates from

        # jacobian cell functions:

        self.jacfuncs = []
        self.derargfunc = None

        # parent object references:

        self.sys = None
        self.device = None

        # other:

        self.implicit = True

    def add_connection(self, other, coefficient=1.0, coeffunc=None):
        
        connection = Connection(self, other, coefficient=coefficient,
                                coeffunc=coeffunc)

        connection.device = self.device

        self.connections.append(connection)

        return connection

    def add_jacfunc(self, other, func):

        self.jacfuncs.append((other, func))

    def set_state(self, value, quantize=False):

        self.x = float(value)

        if quantize:

            self.quantize(implicit=False)

        else:
            self.q = value
            self.qhi = self.q + self.dq
            self.qlo = self.q - self.dq

    def initialize(self, t0):

        self.tlast = t0
        self.time = t0
        self.tnext = _INF

        # init state:                        

        if isinstance(self, StateAtom):
            self.x = self.x0

        if isinstance(self, SourceAtom):
            self.dint()

        self.q = self.x
        self.q0 = self.x
        self.qsave = self.x
        self.xsave = self.x

        # init quantizer values:

        #self.dq = self.dqmin
        self.qhi = self.q + self.dq
        self.qlo = self.q - self.dq

        # init output:

        typecode = "d"

        self.tout     = array(typecode)
        self.qout     = array(typecode)
        self.nupd     = array(typecode)
        self.tzoh     = array(typecode)
        self.qzoh     = array(typecode)
        self.tout_ss  = array(typecode)
        self.xout_ss  = array(typecode)
        self.nupd_ss  = array(typecode)
        self.tout_ode = array(typecode)
        self.xout_ode = array(typecode)
        self.nupd_ode = array(typecode)

        self.updates = 0
        self.updates_ss = 0
        self.updates_ode = 0

        self.tout.append(self.time)
        self.qout.append(self.q0)
        self.nupd.append(0)
        self.tzoh.append(self.time)
        self.qzoh.append(self.q0)

        self.tout_ss.append(self.time)
        self.xout_ss.append(self.q0)
        self.nupd_ss.append(0)

        self.tout_ode.append(self.time)
        self.xout_ode.append(self.q0)
        self.nupd_ode.append(0)

    def update(self, time):

        self.time = time
        self.updates += 1
        self.triggered = False  # reset triggered flag

        self.d = self.f()

        #if self.sys.enable_slewrate:
        #    self.d = max(self.d, -self.dmax*self.dq)
        #    self.d = min(self.d, self.dmax*self.dq)

        self.dint()
        self.quantize()
        self.ta()

        # trigger external update if quantized output changed:
        
        if self.q != self.q0:
            self.save()
            self.q0 = self.q
            self.broadcast()
            self.update_dq()

    def step(self, time):

        self.time = time
        self.updates += 1
        self.d = self.f()
        self.dint()
        self.q = self.x
        self.save()
        self.q0 = self.q

    def dint(self):

        raise NotImplementedError()

    def quantize(self):

        raise NotImplementedError()

    def ta(self):

        raise NotImplementedError()

    def f(self, q=None):

        raise NotImplementedError()

    def broadcast(self):

        for atom in self.broadcast_to:
            if atom is not self:
                atom.triggered = True

    def update_dq(self):

        if not self.dqerr:
            return
        else:
            if self.dqerr <= 0.0:
                return

        if not (self.dqmin or self.dqmax):
            return

        if (self.dqmax - self.dqmin) < _EPS:
            return
            
        self.dq = min(self.dqmax, max(self.dqmin, abs(self.dqerr * self.q))) 
            
        self.qlo = self.q - self.dq
        self.qhi = self.q + self.dq

    def save(self, force=False):
    
        if self.time != self.tout[-1] or force:

            self.tout.append(self.time)           
            self.qout.append(self.q)
            self.nupd.append(self.updates)

            self.tzoh.append(self.time)           
            self.qzoh.append(self.q0)
            self.tzoh.append(self.time)           
            self.qzoh.append(self.q)

    def save_ss(self, t, x):

        self.tout_ss.append(t)           
        self.xout_ss.append(x)
        self.nupd_ss.append(self.updates_ss)
        self.updates_ss += 1

    def save_ode(self, t, x):

        self.tout_ode.append(t)           
        self.xout_ode.append(x)
        self.nupd_ode.append(self.updates_ss)
        self.updates_ode += 1

    def get_error(self, typ="l2"):

        # interpolate qss to ss time vector:
        # this function can only be called after state space AND qdl simualtions
        # are complete

        qout_interp = numpy.interp(self.tout2, self.tout, self.qout)

        if typ.lower().strip() == "l2":

            # calculate the L**2 relative error:
            #      ________________
            #     / sum((y - q)**2)
            #    /  --------------
            #  \/      sum(y**2)

            dy_sqrd_sum = 0.0
            y_sqrd_sum = 0.0

            for q, y in zip(qout_interp, self.qout2):
                dy_sqrd_sum += (y - q)**2
                y_sqrd_sum += y**2

            return sqrt(dy_sqrd_sum / y_sqrd_sum)

        elif typ.lower().strip() == "nrmsd":   # <--- this is what we're using

            # calculate the normalized relative root mean squared error:
            #      ________________
            #     / sum((y - q)**2) 
            #    /  ---------------
            #  \/          N
            # -----------------------
            #       max(y) - min(y)

            dy_sqrd_sum = 0.0
            y_sqrd_sum = 0.0

            for q, y in zip(qout_interp, self.qout2):
                dy_sqrd_sum += (y - q)**2
                y_sqrd_sum += y**2

            return sqrt(dy_sqrd_sum / len(qout_interp)) / (max(self.qout2) 
                                                           - min(self.qout2))


        elif typ.lower().strip() == "re":

            # Pointwise relative error
            # e = [|(y - q)| / |y|] 

            e = []

            for q, y in zip(qout_interp, self.qout2):
                e.append(abs(y-q) / abs(y))

            return e

        elif typ.lower().strip() == "rpd":

            # Pointwise relative percent difference
            # e = [ 100% * 2 * |y - q| / (|y| + |q|)] 

            e = []

            for q, y in zip(qout_interp, self.qout2):
                den = abs(y) + abs(q)
                if den >= _EPS: 
                    e.append(100 * 2 * abs(y-q) / (abs(y) + abs(q)))
                else:
                    e.append(0)                                         

            return e

        return None

    def get_previous_state(self):

        if self.qout:
            if len(self.qout) >= 2:
                return self.qout[-2]
            else:
                return self.x0
        else:
            return self.x0

    def full_name(self):

        return self.device.name + "." + self.name

    def __repr__(self):

        return self.full_name()

    def __str__(self):

        return __repr__(self)


class SourceAtom(Atom):

    def __init__(self, name, source_type=SourceType.CONSTANT, u0=0.0, u1=0.0,
                 u2=0.0, ua=0.0, freq=0.0, phi=0.0, duty=0.0, t1=0.0, t2=0.0,
                 srcfunc=None, dq=None, dqmin=None, dqmax=None, dqerr=None,
                 dtmin=None, dmax=1e10, units=""):

        Atom.__init__(self, name=name, x0=u0, dq=dq, dqmin=dqmin, dqmax=dqmax,
                      dqerr=dqerr, dtmin=dtmin, dmax=dmax, units=units)

        self.source_type = source_type
        self.u0 = u0
        self.u1 = u1
        self.u2 = u2
        self.ua = ua
        self.freq = freq
        self.phi = phi
        self.duty = duty
        self.t1 = t1
        self.t2 = t2 
        self.srcfunc = srcfunc

        # source derived quantities:

        self.u = self.u0

        self.omega = 2.0 * pi * self.freq

        if self.freq:
            self.T = 1.0 / self.freq

        if self.source_type == SourceType.RAMP:
            self.u0 = self.u1

        self.ramp_slope = 0.0
        if (self.t2 - self.t1) > 0:
            self.ramp_slope = (self.u2 - self.u1) / (self.t2 - self.t1)

    def dint(self):

        self.u_prev = self.u

        if self.source_type == SourceType.FUNCTION:

            u = self.srcfunc(self.device, self.time)

        elif self.source_type == SourceType.CONSTANT:

            u = self.u0

        elif self.source_type == SourceType.STEP:

            if self.time < self.t1:
                u = self.u0
            else:
                u = self.u1

        elif self.source_type == SourceType.SINE:

            if self.time >= self.t1:
                u = self.u0 + self.ua * sin(self.omega * self.time + self.phi)
            else:
                u = self.u0

        elif self.source_type == SourceType.PWM:

            pass # todo

        elif self.source_type == SourceType.RAMP:

            if self.time <= self.t1:
                u = self.u1
            elif self.time <= self.t2:
                u = self.u1 + (self.time - self.t1) * self.d 
            else:
                u = self.u2

        elif self.source_type == SourceType.FUNCTION:

            u = self.srcfunc()

        if self.sys.enable_slewrate:
            if u > self.u_prev:
                self.u = min(u, self.dmax * self.dq * (self.time - self.tlast) + self.u_prev)
            elif u < self.u_prev:
                self.u = max(u, -self.dmax * self.dq * (self.time - self.tlast) + self.u_prev)
        else:
            self.u = u

        self.tlast = self.time

        self.x = self.u
        self.q = self.u

        return self.u

    def quantize(self):
        
        self.q = self.x
        return False

    def ta(self):

        self.tnext = _INF

        if self.source_type == SourceType.FUNCTION:

            pass

        if self.source_type == SourceType.RAMP:

            if self.time < self.t1:
                self.tnext = self.t1

            elif self.time < self.t2:
                if self.d > 0.0:
                    self.tnext = self.time + (self.q + self.dq - self.u)/self.d
                elif self.d < 0.0:
                    self.tnext = self.time + (self.q - self.dq - self.u)/self.d
                else:
                    self.tnext = _INF

            else:
                self.tnext = _INF

        elif self.source_type == SourceType.STEP:

            if self.time < self.t1:
                self.tnext = self.t1
            else:
                self.tnext = _INF

        elif self.source_type == SourceType.SINE:

            if self.time < self.t1:

                self.tnext = self.t1

            else: 

                w = self.time % self.T             # cycle time
                t0 = self.time - w                 # cycle start time
                theta = self.omega * w + self.phi  # wrapped angular position

                # value at current time w/o dc offset:
                u = self.ua * sin(2.0 * pi * self.freq * self.time)

                # determine next transition time. Saturate at +/- xa:
            
                # quadrant I
                if theta < pi/2.0:      
                    self.tnext = (t0 + (asin(min(1.0, (u + self.dq)/self.ua)))
                                  / self.omega)

                # quadrant II
                elif theta < pi:        
                    self.tnext = (t0 + self.T/2.0
                                  - (asin(max(0.0, (u - self.dq)/self.ua)))
                                  / self.omega)

                # quadrant III
                elif theta < 3.0*pi/2:  
                    self.tnext = (t0 + self.T/2.0
                                  - (asin(max(-1.0, (u - self.dq)/self.ua)))
                                  / self.omega)

                # quadrant IV
                else:                   
                    self.tnext = (t0 + self.T
                                  + (asin(min(0.0, (u + self.dq)/self.ua)))
                                  / self.omega)

        elif self.source_type == SourceType.FUNCTION:

            pass
            #self.tnext = self.time + self.srcdt # <-- should we do this?

        self.tnext = max(self.tnext, self.tlast + self.dtmin)

    def f(self, q=None):

        if not q:
            q = self.q

        d = 0.0

        if self.source_type == SourceType.RAMP:

            d = self.ramp_slope

        elif self.source_type == SourceType.SINE:

            d = self.omega * self.ua * cos(self.omega * self.time + self.phi)

        elif self.source_type == SourceType.STEP:

            pass  # todo: sigmoid approx.

        elif self.source_type == SourceType.PWM:

            pass  # todo: sigmoid approx.

        elif self.source_type == SourceType.FUNCTION:

            d = 0.0  # todo: add a time derivative function delegate

        return d


class StateAtom(Atom):

    """ Qdl State Atom.
    """

    def __init__(self, name, x0=0.0, coefficient=0.0, coeffunc=None,
                 derfunc=None, dq=None, dqmin=None, dqmax=None, dqerr=None,
                 dtmin=None, dmax=1e10, units=""):

        Atom.__init__(self, name=name, x0=x0, dq=dq, dqmin=dqmin, dqmax=dqmax,
                      dqerr=dqerr, dtmin=dtmin, dmax=dmax, units=units)

        self.coefficient = coefficient
        self.coeffunc = coeffunc
        self.derfunc = derfunc

    def dint(self):

        self.x += self.d * (self.time - self.tlast)

        self.tlast = self.time

        return self.x

    def quantize(self, implicit=True):
        
        interp = False
        change = False

        self.d0 = self.d

        # derivative based:

        if self.x >= self.qhi:

            self.q = self.qhi
            self.qlo += self.dq
            change = True

        elif self.x <= self.qlo:

            self.q = self.qlo
            self.qlo -= self.dq
            change = True

        self.qhi = self.qlo + 2.0 * self.dq

        if change and self.implicit and implicit:  # we've ventured out of (qlo, qhi) bounds

            self.d = self.f()

            # if the derivative has changed signs, then we know 
            # we are in a potential oscillating situation, so
            # we will set the q such that the derivative ~= 0:

            if (self.d * self.d0) < 0:  # if derivative has changed sign
                flo = self.f(self.qlo) 
                fhi = self.f(self.qhi)
                if flo != fhi:
                    a = (2.0 * self.dq) / (fhi - flo)
                    self.q = self.qhi - a * fhi
                    interp = True

        return interp

    def ta(self):

        if self.d > _EPS:
            self.tnext = self.time + (self.qhi - self.x) / self.d
        elif self.d < -_EPS:
            self.tnext = self.time + (self.qlo - self.x) / self.d
        else:
            self.tnext = _INF
            
        self.tnext = max(self.tnext, self.tlast + self.dtmin)

    def compute_coefficient(self):

        if self.coeffunc:
            return self.coeffunc(self.device)
        else:
            return self.coefficient

    def f(self, q=None):

        if not q:
            q = self.q

        if self.derfunc:
            if self.derargfunc:
                args = self.derargfunc(self.device)
                return self.derfunc(*args)
            else:
                return self.derfunc(self.device, q)

        d = self.compute_coefficient() * q

        for connection in self.connections:
            d += connection.value()

        return d


class System(object):

    def __init__(self, name="sys", dq=None, dqmin=None, dqmax=None, dqerr=None,
                 dtmin=None, dmax=None, print_time=False):
        
        global sys
        sys = self

        self.name = name

        # qss solution parameters:

        #self.dq = DEF_DQ
        #if dq:
        #    self.dq = dq
        #
        #self.dqmin = DEF_DQMIN
        #if dqmin:
        #    self.dqmin = dqmin
        #elif dq:
        #    self.dqmin = dq
        #
        #self.dqmax = DEF_DQMAX
        #if dqmax:
        #    self.dqmax = dqmax
        #elif dq:
        #    self.dqmax = dq
        #
        #self.dqerr = DEF_DQERR
        #if dqerr:
        #    self.dqerr = dqerr
        #
        self.dtmin = DEF_DTMIN
        if dtmin:
            self.dtmin = dtmin
        
        self.dmax = DEF_DMAX
        if dmax:
            self.dmax = dmax

        # child elements:

        self.devices = []
        self.atoms = []
        self.state_atoms = []
        self.source_atoms = []
        self.n = 0
        self.m = 0

        # simulation variables:

        self.tstop = 0.0  # end simulation time
        self.time = 0.0   # current simulation time
        self.tsave = 0.0  # saved time for state restore
        self.iprint = 0   # for runtime updates
        self.print_time = print_time
        self.dt = 1e-4
        self.enable_slewrate = False
        self.jacobian = None
        self.Km = 1.2

        # events:

        self.events = {}

    def schedule(self, func, time):

        if not time in self.events:
            self.events[time] = []

        self.events[time].append(func)

    def add_device(self, device):

        self.devices.append(device)

        for atom in device.atoms:

            if not atom.dq:
                atom.dq = self.dq

            #if not atom.dqmin:
            #    atom.dqmin = self.dqmin
            #
            #if not atom.dqmax:
            #    atom.dqmax = self.dqmax
            #
            #if not atom.dqerr:
            #    atom.dqerr = self.dqerr

            if not atom.dtmin:
                atom.dtmin = self.dtmin

            if not atom.dmax:
                atom.dmax = self.dmax

            atom.device = device
            atom.sys = self
            self.atoms.append(atom)

            if isinstance(atom, StateAtom):
                atom.index = self.n
                self.state_atoms.append(atom)
                self.n += 1

            elif isinstance(atom, SourceAtom):
                atom.index = self.m
                self.source_atoms.append(atom)
                self.m += 1

        setattr(self, device.name, device)

    def add_devices(self, *devices):

        for device in devices:
            device.setup_connections()

        for device in devices:
            device.setup_functions()

        for device in devices:
            self.add_device(device)

    def save_state(self):

        self.tsave = self.time

        for atom in self.atoms:
            atom.qsave = atom.q
            atom.xsave = atom.x

    def connect(self, from_electrical_port, to_electrical_port):

        from_electrical_port["input_port"]["ports"].append(to_electrical_port["output_port"])
        to_electrical_port["input_port"]["ports"].append(from_electrical_port["output_port"])

    def connectdq(self, from_dq_port, to_dq_port):

        from_dq_port["inputd_port"]["ports"].append(to_dq_port["outputd_port"])
        from_dq_port["inputq_port"]["ports"].append(to_dq_port["outputq_port"])

        to_dq_port["inputd_port"]["ports"].append(from_dq_port["outputd_port"])
        to_dq_port["inputq_port"]["ports"].append(from_dq_port["outputq_port"])

    def restore_state(self):

        self.time = self.tsave

        for atom in self.atoms:
            atom.q = atom.qsave
            atom.x = atom.xsave

            atom.qhi = atom.q + atom.dq
            atom.qlo = atom.q - atom.dq

    def get_jacobian(self):

        jacobian = np.zeros((self.n, self.n))

        for atom in self.state_atoms:
            for other, func in atom.jacfuncs:
                if atom.derargfunc:
                    args = atom.derargfunc(atom.device)
                    jacobian[atom.index, other.index] = func(*args)
                else:
                    if atom is other:
                        jacobian[atom.index, other.index] = func(atom.device, atom.q)
                    else:
                        jacobian[atom.index, other.index] = func(atom.device, atom.q, other.index)

        return jacobian

    @staticmethod
    def fode(t, x, sys):

        """Returns array of derivatives from state atoms. This function must be
        a static method in order to be passed as a delgate to the
        scipy ode integrator function. Note that sys is a global module variable.
        """

        dx_dt = [0.0] * sys.n

        for atom in sys.state_atoms:
            atom.q = x[atom.index]

        for atom in sys.state_atoms:
            dx_dt[atom.index] = atom.f()

        return dx_dt

    @staticmethod
    def fode2(x, t=0.0, sys=None):

        """Returns array of derivatives from state atoms. This function must be
        a static method in order to be passed as a delgate to the
        scipy ode integrator function. Note that sys is a global module variable.
        """

        y = [0.0] * sys.n

        for atom in sys.state_atoms:
            atom.q = x[atom.index]

        for atom in sys.state_atoms:
            y[atom.index] = atom.f()

        return y

    def solve_dc(self, init=True, set=True):

        xi = [0.0]*self.n

        for atom in self.state_atoms:
            if init:
                xi[atom.index] = atom.x0
            else:
                xi[atom.index] = atom.x

        xdc = fsolve(self.fode2, xi, args=(0, sys), xtol=1e-12)

        for atom in self.state_atoms:
            if init:
                atom.x0 = xdc[atom.index]
            elif set:
                atom.x = xdc[atom.index]
                atom.q = atom.x

        return xdc

    def initialize(self, t0=0.0, dt=1e-4, dc=False):

        self.time = t0
        self.dt = dt

        self.dq0 = np.zeros((self.n, 1))

        for atom in self.state_atoms:
            self.dq0[atom.index] = atom.dq0

        if dc:
            self.solve_dc()

        for atom in self.state_atoms:   
            atom.initialize(self.time)

        for atom in self.source_atoms:   
            atom.initialize(self.time)

    def run(self, tstop, ode=True, qss=True, verbose=True, qss_fixed_dt=None,
            ode_method="RK45", optimize_dq=False, chk_ss_delay=None):

        self.verbose = verbose
        self.calc_ss = False

        if optimize_dq or chk_ss_delay:
            self.calc_ss = True
            self.update_steadystate_distance()

        # get the event times and event function lists, sorted by time:

        sorted_events = sorted(self.events.items())

        # add the last tstop event to the lists:

        sorted_events.append((tstop, None))

        # loop through the event times and solve:
                                       
        for time, events in sorted_events:

            if self.calc_ss:
                self.calc_steadystate()

            if optimize_dq:
                self.optimize_dq()
                self.update_steadystate_distance()

            self.tstop = time

            if ode:

                print("ODE Simulation started...")

                self.save_state()
                self.enable_slewrate = False

                xi = [0.0]*self.n
                for atom in self.state_atoms:
                    xi[atom.index] = atom.x

                tspan = (self.time, self.tstop)

                soln = solve_ivp(self.fode, tspan, xi, ode_method, args=(sys,),
                                 max_step=self.dt)

                t = soln.t
                x = soln.y

                for i in range(len(t)):

                    for atom in self.state_atoms:
                        atom.q = x[atom.index, i]
                        atom.save_ode(t[i], atom.q)

                    for atom in self.source_atoms:
                        atom.save_ode(t[i], atom.dint())

                for atom in self.state_atoms:
                    xf = x[atom.index, -1]
                    atom.x = xf
                    atom.q = xf

                for atom in self.source_atoms:
                    atom.dint()
                    atom.q = atom.q

                self.time = self.tstop
                self.enable_slewrate = True

                print("ODE Simulation completed.")

            if qss:

                print("QSS Simulation started...")

                if ode: self.restore_state()

                # start by updating all atoms:

                for atom in self.atoms:
                    atom.update(self.time)
                    atom.save(force=True)

                if qss_fixed_dt:

                    while(self.time <= self.tstop):

                        for atom in self.source_atoms:
                            atom.step(self.time)

                        for atom in self.state_atoms:
                            atom.step(self.time)

                        self.time += qss_fixed_dt

                else:
                    # now iterate over atoms until nothing triggered:

                    i = 0
                    while i < _MAXITER:
                        triggered = False
                        for atom in self.atoms:
                            if atom.triggered:
                                triggered = True
                                atom.update(self.time)
                        if not triggered:
                            break
                        i += 1

                    # main simulation loop:

                    tlast = self.time
                    last_print_time =  self.time
                    interval = (self.tstop - self.time) * 0.02

                    chk_ss_clock = 0.0

                    while self.time < self.tstop:

                        self.advance()

                        if verbose and self.time-last_print_time > interval:
                            print("t = {0:5.2f} s".format(self.time))
                            last_print_time = self.time

                        if chk_ss_delay:

                            chk_ss_clock += self.time - tlast

                            if not self.check_steadystate(apply_if_true=False):
                                chk_ss_clock = 0.0

                            if chk_ss_clock >= chk_ss_delay:
                                self.check_steadystate(apply_if_true=True)

                        tlast = self.time

                    self.time = self.tstop

                    for atom in self.atoms:
                        atom.update(self.time)
                        atom.save()

                print("QSS Simulation completed.")

            if events:

                for event in events:
                    event(self)

    def calc_steadystate(self):
        
        self.jac1 = self.get_jacobian()

        self.save_state()

        self.xf = self.solve_dc(init=False, set=False)

        for atom in self.state_atoms:
            atom.xf = self.xf[atom.index]

        self.jac2 = self.get_jacobian()

        self.restore_state()

    def update_steadystate_distance(self):

       dq0 = [0.0]*self.n
       for atom in self.state_atoms:
           dq0[atom.index] = atom.dq0

       self.steadystate_distance = la.norm(dq0) * self.Km

    def optimize_dq(self):

        if self.verbose:
            print("dq0 = {}\n".format(self.dq0))
            print("jac1 = {}\n".format(self.jac1))

        if 0:

            QQ0 = np.square(self.dq0)
            
            JTJ = self.jac1.transpose().dot(self.jac1)
            QQ = la.solve(JTJ, QQ0)
            dq1 = np.sqrt(np.abs(QQ))

            JTJ = self.jac2.transpose().dot(self.jac1)
            QQ = la.solve(JTJ, QQ0)
            dq2 = np.sqrt(np.abs(QQ))

        if 1:

            factor = 0.5
            
            E = np.zeros((self.n, self.n))

            dq1 = np.zeros((self.n, 1))
            dq2 = np.zeros((self.n, 1))
        
            for atom in self.state_atoms:
                for j in range(self.n):
                    if atom.index == j:
                        E[atom.index, atom.index] = (atom.dq0*factor)**2
                    else:
                        pass
                        E[atom.index, j] = (atom.dq0*factor)     
                 
            JTJ = self.jac1.transpose().dot(self.jac1)
            Q = la.solve(JTJ, E)

            for atom in self.state_atoms:
                dq = 999999.9
                for j in range(self.n):
                    if atom.index == j:
                       dqii = sqrt(abs(Q[atom.index, j]))
                       dqii = abs(Q[atom.index, j])
                       if dqii < dq:
                           dq = dqii
                    else:
                       dqij = abs(Q[atom.index, j])
                       if dqij < dq:
                           dq = dqij  
                dq1[atom.index, 0] = dq

            JTJ = self.jac2.transpose().dot(self.jac2)
            Q = la.solve(JTJ, E)
            
            for atom in self.state_atoms:
                dq = 999999.9
                for j in range(self.n):
                    if atom.index == j:
                        dqii = sqrt(abs(Q[atom.index, j]))
                        dqii = abs(Q[atom.index, j])
                        if dqii < dq:
                            dq = dqii
                    else:
                        dqij = abs(Q[atom.index, j])
                        if dqij < dq:
                            dq = dqij  
                dq2[atom.index, 0] = dq

        if self.verbose:
            print("at t=inf:")
            print("dq1 = {}\n".format(dq1))
            print("at t=0+:")
            print("dq2 = {}\n".format(dq2))

        for atom in self.state_atoms:
        
            #atom.dq = min(atom.dq0, dq1[atom.index, 0], dq2[atom.index, 0])
            atom.dq = min(dq1[atom.index, 0], dq2[atom.index, 0])
        
            atom.qhi = atom.q + atom.dq
            atom.qlo = atom.q - atom.dq
        
            if self.verbose:
                print("dq_{} = {} ({})\n".format(atom.full_name(), atom.dq, atom.units))

    def check_steadystate(self, apply_if_true=True):

        is_ss = False

        q = [0.0]*self.n
        for atom in self.state_atoms:
            q[atom.index] = atom.q

        qe = la.norm(np.add(q, -self.xf))

        if (qe < self.steadystate_distance):
            is_ss = True

        if is_ss and apply_if_true:

            for atom in self.state_atoms:
                atom.set_state(self.xf[atom.index])

            for atom in self.source_atoms:
                atom.dint()
                atom.q = atom.x

        return is_ss

    def advance(self):

        tnext = _INF

        for atom in self.atoms:
            tnext = min(atom.tnext, tnext)

        self.time = max(tnext, self.time + _EPS)
        self.time = min(self.time, self.tstop)

        for atom in self.atoms:
            if atom.tnext <= self.time or self.time >= self.tstop:
                atom.update(self.time)

        i = 0
        while i < _MAXITER:
            triggered = False
            for atom in self.atoms:
                if atom.triggered:
                    triggered = True
                    atom.update(self.time)
            if not triggered:
                break
            i += 1

    def plot_devices(self, *devices, plot_qss=True, plot_ss=False,
             plot_qss_updates=False, plot_ss_updates=False, legend=False):

        for device in devices:
            for atom in devices.atoms:
                atoms.append(atom)

        self.plot(self, *atoms, plot_qss=plot_qss, plot_ss=plot_ss,
                  plot_qss_updates=plot_qss_updates,
                  plot_ss_updates=plot_ss_updates, legend=legend)

    def plot_old(self, *atoms, plot_qss=True, plot_ss=False,
             plot_qss_updates=False, plot_ss_updates=False, legend=False):

        if not atoms:
            atoms = self.state_atoms

        c, j = 2, 1
        r = floor(len(atoms)/2) + 1

        for atom in atoms:

            ax1 = None
            ax2 = None

            plt.subplot(r, c, j)
    
            if plot_qss or plot_ss:

                ax1 = plt.gca()
                ax1.set_ylabel("{} ({})".format(atom.full_name(), atom.units),
                               color='b')
                ax1.grid()

            if plot_qss_updates or plot_ss_updates:
                ax2 = ax1.twinx()
                ax2.set_ylabel('updates', color='r')

            if plot_qss:
                ax1.plot(atom.tzoh, atom.qzoh, 'b-', label="qss_q")

            if plot_ss:
                ax1.plot(atom.tout_ss, atom.xout_ss, 'c--', label="ss_x")
                
            if plot_qss_updates:
                ax2.hist(atom.tout, 100)
                #ax2.plot(atom.tout, atom.nupd, 'r-', label="qss updates")

            if plot_ss_updates:
                ax2.plot(self.tout_ss, self.nupd_ss, 'm--', label="ss_upds")

            if ax1 and legend:
                ax1.legend(loc="upper left")

            if ax2 and legend:
                ax2.legend(loc="upper right")

            plt.xlabel("t (s)")
 
            j += 1

        plt.tight_layout()
        plt.show()

    def plot_groups(self, *groups, plot_qss=False, plot_ss=False, plot_ode=False):

        c, j = 1, 1
        r = len(groups)/c

        if r % c > 0.0: r += 1

        for atoms in groups:

            plt.subplot(r, c, j)

            if plot_qss:

                for i, atom in enumerate(atoms):

                    color = "C{}".format(i)

                    lbl = "{} qss ({})".format(atom.full_name(), atom.units)

                    plt.plot(atom.tout, atom.qout,
                             marker='.',
                             markersize=4,
                             markerfacecolor='none',
                             markeredgecolor=color,
                             markeredgewidth=0.5,
                             linestyle='none',
                             label=lbl)

            if plot_ode:

                for i, atom in enumerate(atoms):

                    color = "C{}".format(i)

                    lbl = "{} ode ({})".format(atom.full_name(), atom.units)

                    plt.plot(atom.tout_ode, atom.xout_ode, 
                             color=color,
                             alpha=0.6,
                             linewidth=1.0,
                             linestyle='dashed',
                             label=lbl)

            plt.legend(loc="lower right")
            plt.ylabel("atom state")
            plt.xlabel("t (s)")
            plt.grid()

            j += 1

        plt.tight_layout()
        plt.show()

    def plot(self, *atoms, plot_qss=False, plot_zoh=False, plot_ss=False, plot_ode=False,
             plot_qss_updates=False, plot_ss_updates=False, legloc=None,
             plot_ode_updates=False, legend=True, errorband=False, upd_bins=1000,
             pth=None):

        c, j = 1, 1
        r = len(atoms)/c

        if r % c > 0.0: r += 1

        fig = plt.figure()

        for i, atom in enumerate(atoms):

            plt.subplot(r, c, j)

            ax1 = plt.gca()
            ax1.set_ylabel("{} ({})".format(atom.full_name(),
                            atom.units), color='tab:red')
            ax1.grid()

            ax2 = None

            if plot_qss_updates or plot_ss_updates:

                ax2 = ax1.twinx()
                ylabel = "update density ($s^{-1}$)"
                ax2.set_ylabel(ylabel, color='tab:blue')

            if plot_qss_updates:

                dt = atom.tout[-1] / upd_bins

                label = "update density"
                #ax2.hist(atom.tout, upd_bins, alpha=0.5,
                #         color='b', label=label, density=True)

                n = len(atom.tout)
                bw = n**(-2/3)
                kde = gaussian_kde(atom.tout, bw_method=bw)
                t = np.arange(0.0, atom.tout[-1], dt/10)
                pdensity = kde(t) * n

                ax2.fill_between(t, pdensity, 0, lw=0,
                                 color='tab:blue', alpha=0.2,
                                 label=label)

            if plot_ss_updates:

                ax2.plot(self.tout_ss, self.nupd_ss, 'tab:blue', label="ss_upds")

            if plot_qss:

                #lbl = "{} qss ({})".format(atom.full_name(), atom.units)
                lbl = "qss"

                ax1.plot(atom.tout, atom.qout,
                         marker='.',
                         markersize=4,
                         markerfacecolor='none',
                         markeredgecolor='tab:red',
                         markeredgewidth=0.5,
                         alpha=1.0,
                         linestyle='none',
                         label=lbl)

            if plot_zoh:
                
                lbl = "qss (zoh)"

                ax1.plot(atom.tzoh, atom.qzoh, color="tab:red", linestyle="-",
                         alpha=0.5, label=lbl)

            if plot_ss:

                lbl = "ss"

                ax1.plot(atom.tout_ss, atom.xout_ss, 
                         color='r',
                         linewidth=1.0,
                         linestyle='dashed',
                         label=lbl)

            if plot_ode:

                lbl = "ode"

                if errorband:

                    xhi = [x + atom.dq0 for x in atom.xout_ode]
                    xlo = [x - atom.dq0 for x in atom.xout_ode]


                    ax1.plot(atom.tout_ode, atom.xout_ode, 
                             color='k',
                             alpha=0.6,
                             linewidth=1.0,
                             linestyle='dashed',
                             label=lbl)

                    lbl = "error band"

                    ax1.fill_between(atom.tout_ode, xhi, xlo, color='k', alpha=0.1, 
                                     label=lbl)

                else:

                    ax1.plot(atom.tout_ode, atom.xout_ode, 
                             color='k',
                             alpha=0.6,
                             linewidth=1.0,
                             linestyle='dashed',
                             label=lbl)

            loc = "best"

            if legloc:
                loc = legloc

            lines1, labels1 = ax1.get_legend_handles_labels()

            if ax2:
                lines2, labels2 = ax2.get_legend_handles_labels()
                ax1.legend(lines1+lines2, labels1+labels2, loc=loc)
            else:
                ax1.legend(lines1, labels1, loc=loc)

            plt.xlabel("t (s)")
            j += 1

        plt.tight_layout()

        if pth:
            fig.savefig(pth)
        else:
            plt.show()

    def plotxy(self, atomx, atomy, arrows=False, ss_region=False, auto_limits=False):

        ftheta = interp1d(atomx.tout, atomx.qout, kind='zero')
        fomega = interp1d(atomy.tout, atomy.qout, kind='zero')

        tboth = np.concatenate((atomx.tout, atomy.tout))
        tsort = np.sort(tboth)
        t = np.unique(tsort)

        x = ftheta(t)
        y = fomega(t)
        u = np.diff(x, append=x[-1])
        v = np.diff(y, append=x[-1])

        fig = plt.figure()
        ax = fig.add_subplot(111)

        if not auto_limits:
            r = max(abs(max(x)), abs(min(x)), abs(max(y)), abs(min(y)))
    
            dq = atomx.dq
            rx = r + (dq - r % dq) + dq * 5
    
            dx = rx*0.2 + (dq - rx*0.2 % dq)
            x_major_ticks = np.arange(-rx, rx, dx)
            x_minor_ticks = np.arange(-rx, rx, dx*0.2)

            dq = atomy.dq
            ry = r + (dq - r % dq) + dq * 5
    
            dy = ry*0.2 + (dq - ry*0.2 % dq)
            y_major_ticks = np.arange(-ry, ry, dy)
            y_minor_ticks = np.arange(-ry, ry, dy*0.2)

            ax.set_xticks(x_major_ticks)
            ax.set_xticks(x_minor_ticks, minor=True)
            ax.set_yticks(y_major_ticks)
            ax.set_yticks(y_minor_ticks, minor=True)

            plt.xlim([-rx, rx])
            plt.ylim([-ry, ry])

        if ss_region:
            dq = sqrt(atomx.dq**2 + atomx.dq**2) * self.Km
            region= plt.Circle((atomx.xf, atomy.xf), dq, color='k', alpha=0.2)
            ax.add_artist(region)

        if arrows:
            ax.quiver(x[:-1], y[:-1], u[:-1], v[:-1], color="tab:red",
                   units="dots", width=1, headwidth=10, headlength=10, label="qss")

            ax.plot(x, y, color="tab:red", linestyle="-")
        else:
            ax.plot(x, y, color="tab:red", linestyle="-", label="qss")

        ax.plot(atomx.xout_ode, atomy.xout_ode, color="tab:blue", linestyle="--", alpha=0.4, label="ode")

        ax.grid(b=True, which="major", color="k", alpha=0.3, linestyle="-")
        ax.grid(b=True, which="minor", color="k", alpha=0.1, linestyle="-")

        plt.xlabel(atomx.full_name() + " ({})".format(atomx.units))
        plt.ylabel(atomy.full_name() + " ({})".format(atomy.units))

        ax.set_aspect("equal")

        plt.legend()
        plt.show()

    def plotxyt(self, atomx, atomy, arrows=True, ss_region=False):

        fx = interp1d(atomx.tout, atomx.qout, kind='zero')
        fy = interp1d(atomy.tout, atomy.qout, kind='zero')

        tboth = np.concatenate((atomx.tout, atomy.tout))
        tsort = np.sort(tboth)
        t = np.unique(tsort)

        x = fx(t)
        y = fy(t)
        u = np.diff(x, append=x[-1])
        v = np.diff(y, append=x[-1])

        fig = plt.figure()

        ax = plt.axes(projection="3d")

        dq = sqrt(atomx.dq**2 + atomx.dq**2) * self.Km

        def cylinder(center, r, l):
            x = np.linspace(0, l, 100)
            theta = np.linspace(0, 2*pi, 100)
            theta_grid, x_grid = np.meshgrid(theta, x)
            y_grid = r * np.cos(theta_grid) + center[0]
            z_grid = r * np.sin(theta_grid) + center[1]
            return x_grid, y_grid, z_grid

        Xc, Yc, Zc = cylinder((0.0, 0.0), 0.1, t[-1])

        ax.plot_surface(Xc, Yc, Zc, alpha=0.2)

        ax.scatter3D(t, x, y, c=t, cmap="hsv", marker=".")
        ax.plot3D(t, x, y)
        
        ax.plot3D(atomy.tout_ode, atomx.xout_ode, atomy.xout_ode, color="tab:blue", linestyle="--", alpha=0.4, label="ode")
        
        ax.set_ylabel(atomx.full_name() + " ({})".format(atomx.units))
        ax.set_zlabel(atomy.full_name() + " ({})".format(atomy.units))
        ax.set_xlabel("t (s)")
        
        xmax = max(abs(min(x)), max(x))
        ymax = max(abs(min(y)), max(y))
        xymax = max(xmax, ymax)

        ax.set_xlim([0.0, t[-1]])
        ax.set_ylim([-xymax, xymax])
        ax.set_zlim([-xymax, xymax])

        plt.legend()

        plt.show()

    def plotxy2(self, atomsx, atomsy, arrows=True, ss_region=False):

        fx1 = interp1d(atomsx[0].tout, atomsx[0].qout, kind='zero')
        fx2 = interp1d(atomsx[1].tout, atomsx[1].qout, kind='zero')

        fy1 = interp1d(atomsy[0].tout, atomsy[0].qout, kind='zero')
        fy2 = interp1d(atomsy[1].tout, atomsy[1].qout, kind='zero')

        tall = np.concatenate((atomsx[0].tout, atomsx[1].tout,
                               atomsy[0].tout, atomsy[1].tout))

        tsort = np.sort(tall)

        t = np.unique(tsort)

        x1 = fx1(t)
        x2 = fx2(t)

        y1 = fy1(t)
        y2 = fy2(t)

        x = np.multiply(x1, x2)
        y = np.multiply(y1, y2)

        u = np.diff(x, append=x[-1])
        v = np.diff(y, append=x[-1])

        fig = plt.figure()
        ax = fig.add_subplot(111)

        r = max(abs(max(x)), abs(min(x)), abs(max(y)), abs(min(y)))
    
        dq = atomsx[0].dq
        rx = r + (dq - r % dq) + dq * 5
    
        dx = rx*0.2 + (dq - rx*0.2 % dq)
        x_major_ticks = np.arange(-rx, rx, dx)
        x_minor_ticks = np.arange(-rx, rx, dx*0.2)

        dq = atomsy[0].dq
        ry = r + (dq - r % dq) + dq * 5
    
        dy = ry*0.2 + (dq - ry*0.2 % dq)
        y_major_ticks = np.arange(-ry, ry, dy)
        y_minor_ticks = np.arange(-ry, ry, dy*0.2)

        ax.set_xticks(x_major_ticks)
        ax.set_xticks(x_minor_ticks, minor=True)
        ax.set_yticks(y_major_ticks)
        ax.set_yticks(y_minor_ticks, minor=True)

        #plt.xlim([-rx, rx])
        #plt.ylim([-ry, ry])

        #if ss_region:
        #    dq = sqrt(atomx.dq**2 + atomx.dq**2) * self.Km
        #    region= plt.Circle((atomx.xf, atomy.xf), dq, color='k', alpha=0.2)
        #    ax.add_artist(region)

        if arrows:
            ax.quiver(x[:-1], y[:-1], u[:-1], v[:-1], color="tab:red",
                   units="dots", width=1, headwidth=10, headlength=10, label="qss")

            ax.plot(x, y, color="tab:red", linestyle="-")
        else:
            ax.plot(x, y, color="tab:red", linestyle="-", label="qss")

        xode = np.multiply(atomsx[0].xout_ode, atomsx[1].xout_ode)
        yode = np.multiply(atomsy[0].xout_ode, atomsy[1].xout_ode)

        ax.plot(xode, yode, color="tab:blue", linestyle="--", alpha=0.4, label="ode")

        #ax.grid(b=True, which="major", color="k", alpha=0.3, linestyle="-")
        #ax.grid(b=True, which="minor", color="k", alpha=0.1, linestyle="-")

        plt.xlabel("{} * {}".format(atomsx[0].name, atomsx[0].name))
        plt.ylabel("{} * {}".format(atomsy[0].name, atomsy[0].name))

        #ax.set_aspect("equal")

        plt.legend()
        plt.show()

    def __repr__(self):

        return self.name

    def __str__(self):

        return self.name


# ========================== Interface Model ===================================


class Device(object):

    """Collection of Atoms and Connections that comprise a device
    """

    def __init__(self, name):

        self.name = name
        self.atoms = []
        self.ports = []

    def add_atom(self, atom):
        
        self.atoms.append(atom)
        atom.device = self
        setattr(self, atom.name, atom)

    def add_atoms(self, *atoms):
        
        for atom in atoms:
            self.add_atom(atom)

    def setup_connections(self):

        pass

    def setup_functions(self):

        pass

    def __repr__(self):

        return self.name

    def __str__(self):

        return __repr__(self)


class Connection(object):

    """Connection between atoms.
    """
       
    def __init__(self, atom=None, other=None, coefficient=1.0, coeffunc=None, valfunc=None):

        self.atom = atom
        self.other = other

        self.coefficient = coefficient
        self.coeffunc = coeffunc
        self.valfunc = valfunc

        self.device = None

        if atom and other:
            self.reset_atoms(atom, other)

    def reset_atoms(self, atom, other):

        self.atom = atom
        self.other = other

        self.other.broadcast_to.append(self.atom)

    def compute_coefficient(self):

        if self.coeffunc:
            return self.coeffunc(self.device)
        else:
            return self.coefficient                                                  

    def value(self):

        if self.other:
            if self.valfunc:
                return self.valfunc(self.other)
            else:
                if isinstance(self.other, StateAtom):
                    return self.compute_coefficient() * self.other.q

                elif isinstance(self.other, SourceAtom):
                    return self.compute_coefficient() * self.other.dint()
        else:
            return 0.0


class PortConnection(object):

    def __init__(self, variable, sign=1, expr=""):

        self.variable = variable
        self.sign = sign
        self.expr = expr
        self.from_connections = []


class Port(object):

    def __init__(self, name, typ="in", *connections):

        self.name = name
        self.typ = typ
        self.from_ports = []

        if connections:
            self.connections = connections
        else:
            self.connections = []

    def connect(self, other):

        if self.typ == "in":
            self.connections[0].from_connections.append(other.connections[0]) 

        elif self.typ == "out":
            other.connections[0].from_connections.append(self.connections[0]) 

        elif self.typ in ("inout"):
            self.connections[0].from_connections.append(other.connections[0])
            other.connections[0].from_connections.append(self.connections[0])

        elif self.typ in ("dq"):
            self.connections[0].from_connections.append(other.connections[0])
            other.connections[0].from_connections.append(self.connections[0])
            self.connections[1].from_connections.append(other.connections[1])
            other.connections[1].from_connections.append(self.connections[1])


class SymbolicDevice(Device):

    def __init__(self, name):

        Device.__init__(self, name)

        self.states = odict()
        self.constants = odict()
        self.parameters = odict()

        self.input_ports = odict()
        self.output_ports = odict()
        self.electrical_ports = odict()
        self.dq_ports = odict()

        self.algebraic = odict()
        self.diffeq = []

        self.dermap = odict()
        self.jacobian = odict()

        self.ports = odict()

    def add_state(self, name, dername, desc="", units="", x0=0.0, dq=1e-3):

        self.states[name] = odict()

        self.states[name]["name"] = name
        self.states[name]["dername"] = dername
        self.states[name]["desc"] = desc
        self.states[name]["units"] = units
        self.states[name]["x0"] = x0
        self.states[name]["dq"] = dq
        self.states[name]["device"] = self

        self.states[name]["sym"] = None
        self.states[name]["dersym"] = None
        self.states[name]["expr"] = None
        self.states[name]["atom"] = None

        self.dermap[dername] = name

    def add_input_port(self, name, var, sign=1, expr=""):

        self.input_ports[name] = odict()

        self.input_ports[name]["name"] = name
        self.input_ports[name]["var"] = var
        self.input_ports[name]["ports"] = []
        self.input_ports[name]["sign"] = sign

        #setattr(self, name, self.input_ports[name])

        #connection = PortConnection(var, sign=sign, expr=expr)
        #self.ports[name] = Port(name, typ="in", connection)
        #setattr(self, name, self.ports[name])

    def add_output_port(self, name, var, state):

        self.output_ports[name] = odict()

        self.output_ports[name]["name"] = name
        self.output_ports[name]["var"] = var
        self.output_ports[name]["device"] = self
        self.output_ports[name]["state"] = state
        self.output_ports[name]["atom"] = None

        #setattr(self, name, self.output_ports[name])

        #connection = PortConnection(var, sign=sign, expr=expr)
        #self.ports[name] = Port(name, typ="out", connection)
        #setattr(self, name, self.ports[name])

    def add_constant(self, name, desc="", units="", value=None):

        self.constants[name] = odict()

        self.constants[name]["name"] = name
        self.constants[name]["desc"] = desc
        self.constants[name]["units"] = units
        self.constants[name]["value"] = value

        self.constants[name]["sym"] = None

    def add_parameter(self, name, desc="", units="", value=None):

        self.parameters[name] = odict()

        self.parameters[name]["name"] = name
        self.parameters[name]["desc"] = desc
        self.parameters[name]["units"] = units
        self.parameters[name]["value"] = value

        self.parameters[name]["sym"] = None

    def add_diffeq(self, equation):

        self.diffeq.append(equation)

    def add_algebraic(self, var, rhs):

        self.algebraic[var] = rhs

    def update_parameter(self, key, value):

        self.parameters[key]["value"] = value

    def add_electrical_port(self, name, input, output, sign=1, expr=""):

        self.electrical_ports[name] = odict()

        setattr(self, name, self.electrical_ports[name])

        self.add_input_port(name, input, sign)
        self.add_output_port(name, input, output)

        self.electrical_ports[name]["input_port"] = self.input_ports[name]
        self.electrical_ports[name]["output_port"] = self.output_ports[name]

        connection = PortConnection(input, sign=sign, expr=expr)
        self.ports[name] = Port(name, "inout", connection)
        setattr(self, name, self.ports[name])

    def add_dq_port(self, name, inputs, outputs, sign=1, exprs=None):

        self.dq_ports[name] = odict()

        setattr(self, name, self.dq_ports[name])

        inputd, inputq = inputs
        outputd, outputq = outputs

        self.add_input_port(name+"d", inputd, sign)
        self.add_output_port(name+"d", inputd, outputd)

        self.add_input_port(name+"q", inputq, sign)
        self.add_output_port(name+"q", inputq, outputq)

        self.dq_ports[name]["inputd_port"] = self.input_ports[name+"d"]
        self.dq_ports[name]["outputd_port"] = self.output_ports[name+"d"]

        self.dq_ports[name]["inputq_port"] = self.input_ports[name+"q"]
        self.dq_ports[name]["outputq_port"] = self.output_ports[name+"q"]

        expr_d = ""
        expr_q = ""

        if exprs:
            expr_d, expr_q = exprs

        connection_d = PortConnection(inputs[0], sign=sign, expr=expr_d)
        connection_q = PortConnection(inputs[1], sign=sign, expr=expr_q)

        self.ports[name] = Port(name, "dq", connection_d, connection_q)

        setattr(self, name, self.ports[name])

    def setup_connections(self):

        for name, state in self.states.items():

            atom = StateAtom(name, x0=state["x0"], dq=state["dq"],
                             units=state["units"])

            atom.derargfunc = self.get_args

            self.add_atom(atom)

            self.states[name]["atom"] = atom

    def setup_functions(self):

        # 1. create sympy symbols:

        x = []
        dx_dt = []

        for name, state in self.states.items():

            sym = sp.Symbol(name)
            dersym = sp.Symbol(state["dername"])

            x.append(name)
            dx_dt.append(state["dername"])

            self.states[name]["sym"] = sym
            self.states[name]["dersym"] = dersym

        for name in self.constants:
            sp.Symbol(name)

        for name in self.parameters:
            sp.Symbol(name)

        for name in self.input_ports:
            sp.Symbol(self.input_ports[name]["var"])

        for var in self.algebraic:
            sp.Symbol(var)

        # 2. create symbolic derivative expressions:

        # 2a. substitute algebraic equations:

        n = len(self.algebraic)
        m = len(self.diffeq)

        algebraic = [[sp.Symbol(var), sp.sympify(expr)] for var, expr in self.algebraic.items()]


        for i in range(n-1):
             for j in range(i+1, n):
                 algebraic[j][1] = algebraic[j][1].subs(algebraic[i][0], algebraic[i][1])

        diffeq = self.diffeq.copy()

        for i in range(m):
            diffeq[i] = sp.sympify(diffeq[i])
            for var, expr in algebraic:
                diffeq[i] = diffeq[i].subs(var, expr)

        # 3. solve for derivatives:

        derexprs = solve(diffeq, *dx_dt, dict=True)

        for lhs, rhs in derexprs[0].items():

            dername = str(lhs)
            statename = self.dermap[dername]
            self.states[statename]["expr"] = rhs
         
        # 4. create atoms:

        ext_state_names = []

        ext_state_subs = {}

        external_states = []

        for portname in self.input_ports:

            connected_ports = self.input_ports[portname]["ports"]
            varname = self.input_ports[portname]["var"]

            for port in connected_ports:

                devicename = port["device"].name
                statename = port["state"]
                mangeld_name = "{}_{}".format(devicename, statename)
                ext_state_names.append(mangeld_name)

            ext_state_subs[varname] = "(" + " + ".join(ext_state_names) + ")"

            sign = self.input_ports[portname]["sign"] 
            if sign == -1:
               ext_state_subs[varname] = "-" + ext_state_subs[varname]

            external_states.append(port["device"].states[statename])

        argstrs = (list(self.constants.keys()) + list(self.parameters.keys())
                   + list(self.states.keys()) + ext_state_names)

        argstr = " ".join(argstrs)
        argsyms = sp.var(argstr)

        for name, state in self.states.items():

            expr = state["expr"]

            for var, substr in ext_state_subs.items():
                subexpr = sp.sympify(substr)
                expr = expr.subs(var, subexpr)

            state["expr"] = expr

            func = lambdify(argsyms, expr, dummify=False)

            self.states[name]["atom"].derfunc = func

        for name in self.output_ports:

            statename = self.output_ports[name]["state"]
            state = self.states[statename]
            self.output_ports[name]["atom"] = state["atom"]

        # 5. connect atoms:

        for statex in self.states.values():  

            for statey in self.states.values():

                f = statex["expr"]

                if statey["sym"] in f.free_symbols:

                    # connect:
                    statex["atom"].add_connection(statey["atom"])

                    # add jacobian expr:
                    df_dy = sp.diff(f, statey["sym"])

                    func = lambdify(argsyms, df_dy, dummify=False)

                    statex["atom"].add_jacfunc(statey["atom"], func)

            for statey in external_states:

                f = statex["expr"]

                mangled_name = "{}_{}".format(statey["device"].name, statey["name"])
                mangled_symbol = sp.Symbol(mangled_name)

                if mangled_symbol in f.free_symbols:

                    # connect:
                    statex["atom"].add_connection(statey["atom"])

                    # jacobian expr:
                    df_dy = sp.diff(f, mangled_symbol)

                    func = lambdify(argsyms, df_dy, dummify=False)

                    statex["atom"].add_jacfunc(statey["atom"], func)

    @staticmethod
    def get_args(self):

        args = []

        for name, constant in self.constants.items():
            args.append(float(constant["value"]))

        for name, parameter in self.parameters.items():
            args.append(float(parameter["value"]))

        for name, state in self.states.items():
            args.append(float(state["atom"].q))

        for name, port in self.input_ports.items():
            for port2 in port["ports"]:
               args.append(port2["atom"].q)

        return args
