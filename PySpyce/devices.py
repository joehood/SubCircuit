'''
Contains the core (atomic) SPICE circuit element definitios.
'''
import math
import cmath
import sympy
import numpy

from circuit import *
from interfaces import *

v = sympy.symbols('v') # used by GenericTwoPort model.


class R(Device):
  '''
  A SPICE R (resistor or semiconductor resistor) device.
  '''
  def __init__(self, name, node1, node2, value, rmodel=None, l=None, w=None, temp=None, **kwargs):
    '''General form:
    RXXXXXXX N1 N2 VALUE

    Examples:
    R1 1 2 100
    RC1 12 17 1K
    N1 and N2 are the two element nodes. VALUE is the resistance (in ohms) and
    may be positive or negative but not zero.

    Semiconductor Resistors:
    General form:
    RXXXXXXX N1 N2 <VALUE> <MNAME> <L=LENGTH> <W=WIDTH> <TEMP=T>

    Examples:
    RLOAD 2 10 10K
    RMOD 3 7 RMODEL L=10u W=1u
    '''
    Device.__init__(self, name, 2) # call base constructor for 2-port device
    self.nodes = [node1, node2] # define nodes list
    self.node2port = {node1:0, node2:1} # define system node to device port mapping
    self.value = value # store value (resistance in ohms)

  def setup(self, dt):
    '''
    Define the resistor jacobian stamp.
    '''
    if self.value: # if non-zero:
      g = 1.0 / self.value
    else:
      g = 1.0E12 # approximate short circuit for 0-resistance

    self.jacobian[0, 0] = g
    self.jacobian[0, 1] = -g
    self.jacobian[1, 0] = -g
    self.jacobian[1, 1] = g

  def step(self, dt):
    '''
    Do nothing here. Linear and time-invariant device.
    '''
    pass


class V(Device, CurrentSensor):
  '''
  A SPICE Voltage source or current sensor.
  '''
  def __init__(self, name, node1, node2, internal, value, **kwargs):
    '''
    General form:

          VXXXXXXX N+ N- <<DC> DC/TRAN VALUE> <AC <ACMAG <ACPHASE>>>
          +       <DISTOF1 <F1MAG <F1PHASE>>> <DISTOF2 <F2MAG <F2PHASE>>>
          IYYYYYYY N+ N- <<DC> DC/TRAN VALUE> <AC <ACMAG <ACPHASE>>>
          +       <DISTOF1 <F1MAG <F1PHASE>>> <DISTOF2 <F2MAG <F2PHASE>>>
    Examples:

          VCC 10 0 DC 6
          VIN 13 2 0.001 AC 1 SIN(0 1 1MEG)
          ISRC 23 21 AC 0.333 45.0 SFFM(0 1 10K 5 1K)
          VMEAS 12 9
          VCARRIER 1 0 DISTOF1 0.1 -90.0
          VMODULATOR 2 0 DISTOF2 0.01
          IIN1 1 5 AC 1 DISTOF1 DISTOF2 0.001

    N+ and N- are the positive and negative nodes, respectively. Note that voltage sources
    need not be grounded. Positive current is assumed to flow from the positive node, through
    the source, to the negative node. A current source of positive value forces current to
    flow out of the N+ node, through the source, and into the N- node. Voltage sources, in
    addition to being used for circuit excitation, are the 'ammeters' for SPICE, that is,
    zero valued voltage sources may be inserted into the circuit for the purpose of measuring
    current. They of course have no effect on circuit operation since they represent 
    short-circuits.
    DC/TRAN is the dc and transient analysis value of the source. If the source value is 
    zero both for dc and transient analyses, this value may be omitted. If the source value
    is time-invariant (e.g., a power supply), then the value may optionally be preceded by
    the letters DC.
    ACMAG is the ac magnitude and ACPHASE is the ac phase. The source is set to this value
    in the ac analysis. If ACMAG is omitted following the keyword AC, a value of unity is 
    assumed. If ACPHASE is omitted, a value of zero is assumed. If the source is not an ac 
    small-signal input, the keyword AC and the ac values are omitted.
    DISTOF1 and DISTOF2 are the keywords that specify that the independent source has 
    distortion inputs at the frequencies F1 and F2 respectively (see the description of 
    the .DISTO control line). The keywords may be followed by an optional magnitude and 
    phase. The default values of the magnitude and phase are 1.0 and 0.0 respectively.
    Any independent source can be assigned a time-dependent value for transient analysis. 
    If a source is assigned a time-dependent value, the time-zero value is used for dc 
    analysis. There are five independent source functions: pulse, exponential, sinusoidal, 
    piece-wise linear, and single-frequency FM. If parameters other than source values 
    are omitted or set to zero, the default values shown are assumed. (TSTEP is the printing 
    increment and TSTOP is the final time (see the .TRAN control line for explanation)).
    '''
    Device.__init__(self, name, 3) # three port device (one internal node)
    self.nodes = [node1, node2, internal]
    self.node2port = {node1:0, node2:1, internal:2}

    if isinstance(value, Stimulus):
      self.stimulus = value
      self.stimulus.device = self
    else:
      self.value = value
  
  def setup(self, dt):
    self.jacobian[0, 2] = 1.0
    self.jacobian[1, 2] = -1.0
    self.jacobian[2, 0] = 1.0
    self.jacobian[2, 1] = -1.0

    volt = 0.0
    if self.stimulus:
      volt = self.stimulus.setup()
    elif self.value:
      volt = self.value

    self.bequiv[2] = volt # add forced voltage to gyrator current source


  def step(self, dt):
    '''
    TODO: implement time-varying source behavior here:
    '''
    if self.stimulus:
      voltage = self.stimulus.step()
      self.bequiv[2] = voltage # add forced voltage to gyrator current source

  def get_current_node(self):
    '''
    So this device can be used as a current sensor, this function returns the 
    node index of the internal current state variable node.
    '''
    return self.nodes[2]


class C(Device):
  def __init__(self, name, node1, node2, value, mname=None, l=None, w=None, ic=None):
    '''General form:
    CXXXXXXX N+ N- VALUE <IC=INCOND>

    Examples:
        CBYP 13 0 1UF
        COSC 17 23 10U IC=3V

    N+ and N- are the positive and negative element nodes, respectively. VALUE is
    the capacitance in Farads.
    The (optional) initial condition is the initial (time-zero) value of capacitor
    voltage (in Volts). Note that the initial conditions (if any) apply 'only' if
    the UIC option is specified on the .TRAN control line.
    
    Semiconductor Capacitors:
    General form:
        CXXXXXXX N1 N2 <VALUE> <MNAME> <L=LENGTH> <W=WIDTH> <IC=VAL>

    Examples:
        CLOAD 2 10 10P
        CMOD 3 7 CMODEL L=10u W=1u

    This is the more general form of the Capacitor presented in section 6.2, and
    allows for the calculation of the actual capacitance value from strictly
    geometric information and the specifications of the process. If VALUE is
    specified, it defines the capacitance. If MNAME is specified, then the
    capacitance is calculated from the process information in the model MNAME and
    the given LENGTH and WIDTH. If VALUE is not specified, then MNAME and LENGTH
    must be specified. If WIDTH is not specified, then it is taken from the
    default width given in the model. Either VALUE or MNAME, LENGTH, and WIDTH 
    may be specified, but not both sets.
    The capacitor model contains process information that may be used to compute
    the capacitance from strictly geometric information.

    name    parameter	                      units  default  example
    ---------------------------------------------------------------
    CJ      junction bottom capacitance	    F m-2	 -        5e-5
    CJSW    junction sidewall capacitance	  F m-1	 -        2e-11
    DEFW    default device width	          m      1e-6     2e-6
    NARROW  narrowing due to side etching	  m      0.0      1e-7

    The capacitor has a capacitance computed as

    CAP = CJ (LENGTH - NARROW) (WIDTH - NARROW) + 2 CJSW (LENGTH + WIDTH - 2 NARROW)
    '''
    Device.__init__(self, name, 2)
    self.nodes = [node1, node2]
    self.node2port = {node1:0, node2:1}
    self.value = value
    self.ic = ic
  
  def setup(self, dt):
    self.jacobian[0, 0] = self.value / dt
    self.jacobian[0, 1] = -self.value / dt
    self.jacobian[1, 0] = -self.value / dt
    self.jacobian[1, 1] = self.value / dt

  def step(self, dt):
    vc = self.subcircuit.across_history[self.nodes[1]] - self.subcircuit.across_history[self.nodes[0]]
    self.bequiv[0] = -self.value / dt * vc
    self.bequiv[1] = self.value / dt * vc


class L(Device):
  def __init__(self, name, node1, node2, internal, value, ic=None):
    Device.__init__(self, name, 3)
    self.nodes = [node1, node2, internal]
    self.node2port = {node1:0, node2:1, internal:2}
    self.value = value
    self.ic = ic
  
  def setup(self, dt):
    self.jacobian[0, 2] = 1.0
    self.jacobian[1, 2] = -1.0
    self.jacobian[2, 0] = 1.0
    self.jacobian[2, 1] = -1.0
    self.jacobian[2, 2] = -self.value / dt

  def step(self, dt):
    iL = self.subcircuit.across_history[self.nodes[2]]
    self.bequiv[2] = -self.value / dt * iL


class GenericTwoPort(Device):
  '''
  EXPERIMENTAL
  Device that allows the definition of a two port device with an arbitrary current function.
  '''
  def __init__(self, name, node1, node2, i):
    '''
    Creates a new generic two-port device.
    Arguments:
    name  -- A mandatory name (must be unique within parent subcircuit)
    node1 -- The index of the node attached to the positive or anode port
    node2 -- The index of the node attached to the negative or cathode port
    i     -- The current equation as a function of the sympy symbol 'v'
    Example usage:
    To create a simple non-linear diode model using Schockley's equation:

    Is = 5.0E-9
    vT = 25.85E-3
    diode = GenericTwoPort('D1', 1, 0, i = (Isat * math.exp(v / vT) - 1.0))
    '''
    Device.__init__(self, name, 2)
    self.nodes = [node1, node2]
    self.node2port = {node1:0, node2:1}
    self.i = i
    self.g = sympy.diff(i, v) 
    self.get_g = sympy.lambdify(v, self.g, "math")
    self.get_i = sympy.lambdify(v, self.i, "math")

  def setup(self, dt):
    pass

  def step(self, dt):
    pass

  def minor_step(self):
    v = self.subcircuit.across[self.nodes[1]] - self.subcircuit.across[self.nodes[0]]
    g = self.get_g(v)
    i = self.get_i(v) - g * v
    self.jacobian[0, 0] = g 
    self.jacobian[0, 1] = -g
    self.jacobian[1, 0] = -g
    self.jacobian[1, 1] = g
    self.bequiv[0] = -i
    self.bequiv[1] = i


# ============================ MODELS ==================================

# TODO: implement these or find a way to make them generic...

class RMOD(Model):
  '''Semiconductor resistor model.'''
  def __init__(self, name, **kwargs):
    '''
    This is the more general form of the resistor presented in section 6.1, and
    allows the modeling of temperature effects and for the calculation of the
    actual resistance value from strictly geometric information and the
    specifications of the process. If VALUE is specified, it overrides the
    geometric information and defines the resistance. If MNAME is specified, 
    then the resistance may be calculated from the process information in the
    model MNAME and the given LENGTH and WIDTH. If VALUE is not specified, then
    MNAME and LENGTH must be specified. If WIDTH is not specified, then it is
    taken from the default width given in the model. The (optional) TEMP value
    is the temperature at which this device is to operate, and overrides the
    temperature specification on the .OPTION control line.
    The resistor model consists of process-related device data that allow the
    resistance to be calculated from geometric information and to be corrected
    for temperature. The parameters available are:

    name   parameter                         units    default example
    -----------------------------------------------------------------
    TC1    first order temperature coeff.    ZdegC-1  0.0     -
    TC2    second order temperature coeff.   ZdegC-2  0.0	    -
    RSH    sheet resistance                  ohm/[]   -       50
    DEFW   default width                     m        1e-6    2e-6
    NARROW narrowing due to side etching     m        0.0     1e-7
    TNOM   parameter measurement temperature degC     27      50

    The sheet resistance is used with the narrowing parameter and L and W from
    the resistor device to determine the nominal resistance by the formula

                              L - NARROW
                      R = RSH ----------
                              W - NARROW

    DEFW is used to supply a default value for W if one is not specified for the
    device. If either RSH or L is not specified, then the standard default
    resistance value of 1k Z is used. TNOM is used to override the circuit-wide
    value given on the .OPTIONS control line where the parameters of this model
    have been measured at a different temperature. After the nominal resistance is calculated, it is adjusted for temperature by the formula:

        R(T) = R(T0) [1 + TC1 (T - T0) + TC2 (T-T0)**2 ]
    '''
    Model.__init__(self, name, **kwargs)



"""
'C', 	  # Semiconductor capacitor model 
'SW', 	# Voltage controlled switch 
'CSW', 	# Current controlled switch 
'URC', 	# Uniform distributed RC model 
'LTRA', # Lossy transmission line model 
'D', 	  # Diode model 
'NPN',	# NPN BJT model 
'PNP',	# PNP BJT model 
'NJF', 	# N-channel JFET model 
'PJF',	# P-channel JFET model 
'NMOS', # 	N-channel MOSFET model 
'PMOS',	# P-channel MOSFET model 
'NMF', 	# N-channel MESFET model 
'PMF' 	# P-channel MESFET model 
"""

# ======================== SOURCE STIMULI MODELS ================================

class Pulse(Stimulus):
  def __init__(self, v1, v2, td=0.0, tr=None, tf=None, pw=None, per=None):
    '''
    General form:

         PULSE(V1 V2 TD TR TF PW PER)

    Examples:

         VIN 3 0 PULSE(-1 1 2NS 2NS 2NS 50NS 100NS)

    parameter	default value	units
    V1 (initial value)	 	V or A
    V2 (pulsed value)	 	V or A
    TD (delay time)	0.0	s
    TR (rise time)	TSTEP	s
    TF (fall time)	TSTEP	s
    PW (pulse width)	TSTOP	s
    PER (period)	TSTOP	seconds

    A single pulse so specified is described by the following table:

    time	value
    0	V1
    TD	V1
    TD+TR	V2
    TD+TR+PW	V2
    TD+TR+PW+TF	V1
    TSTOP	V1

    Intermediate points are determined by linear interpolation.
    '''
  def setup(self, device):
    pass

  def step(self, device, dt):
    pass



class Sin(Stimulus):
  def __init__(self, vo, va, freq=1.0, td=0.0, theta=None):
    '''
    General form:

         SIN(VO VA FREQ TD THETA)

    Examples:

         VIN 3 0 SIN(0 1 100MEG 1NS 1E10)

    parameters	default value	units
    VO (offset)	 	V or A
    VA (amplitude)	 	V or A
    FREQ (frequency)	1/TSTOP	Hz
    TD (delay)	0.0	s
    THETA (damping factor)	0.0	s-1

    The shape of the waveform is described by the following table:

    time, t	value
    0 to TD	VO
    TD to TSTOP	VO+VA.exp[-(t-TD)/THETA].sin[2?.FREQ.(t+TD)]
    '''
    self.vo = vo
    self.va = va
    self.freq = freq
    self.td = td
    self.theta = theta
    self.device = None

  def setup(self):
    return self.step()

  def step(self):
    t = self.device.get_time()
    value = 0.0
    if t < self.td:
      value = 0.0
    elif self.theta:
      value = (self.vo + self.va * math.exp(-(t + self.td) / self.theta) *
              math.sin(2.0 * math.pi * self.freq  * (t + self.td)))
    else:
      value = self.vo + self.va * math.sin(2.0 * math.pi * self.freq  * (t + self.td))
    return value