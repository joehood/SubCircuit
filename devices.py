"""Contains the core (atomic) SPICE circuit element definitions."""


import math

from interfaces import *
import pyspyce


# Elementary Devices:


class R(Device):
    """
    A SPICE R (resistor or semiconductor resistor) device.
    """

    def __init__(self, name, node1, node2, value, rmodel=None, l=None, w=None,
                 temp=None, **kwargs):
        """General form:
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
        """
        Device.__init__(self, name, ports=2)
        self.nodes = [node1, node2]  # define nodes list
        self.node2port = {node1: 0,
                          node2: 1}  # define system node to device port mapping
        self.value = value  # store value (resistance in ohms)

    def setup(self, dt):
        """Define the resistor jacobian stamp.
        """
        if self.value:  # if non-zero:
            g = 1.0 / self.value
        else:
            g = 1.0E12  # approximate short circuit for 0-resistance

        self.jac[0, 0] = g
        self.jac[0, 1] = -g
        self.jac[1, 0] = -g
        self.jac[1, 1] = g

    def step(self, t, dt):
        """Do nothing here. Linear and time-invariant device.
        """
        pass


class C(Device):
    """SPICE capacitor device"""

    def __init__(self, name, node1, node2, value, mname=None, l=None, w=None,
                 ic=None):
        """General form:
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
        """
        Device.__init__(self, name, 2)
        self.nodes = [node1, node2]
        self.node2port = {node1: 0, node2: 1}
        self.value = value
        self.ic = ic

    def setup(self, dt):
        self.jac[0, 0] = self.value / dt
        self.jac[0, 1] = -self.value / dt
        self.jac[1, 0] = -self.value / dt
        self.jac[1, 1] = self.value / dt

    def step(self, t, dt):
        vc = self.subcircuit.across_history[self.nodes[1]] - \
             self.subcircuit.across_history[self.nodes[0]]
        self.bequiv[0] = -self.value / dt * vc
        self.bequiv[1] = self.value / dt * vc


class L(Device, CurrentSensor):
    """SPICE Inductor Device"""

    def __init__(self, name, node1, node2, internal, value, ic=None):
        """
        General form:
        LYYYYYYY N+ N- VALUE <IC=INCOND>
        Examples:
        LLINK 42 69 1UH
        LSHUNT 23 51 10U IC=15.7MA
        N+ and N- are the positive and negative element nodes, respectively. VALUE is the
        inductance in Henries.
        The (optional) initial condition is the initial (time-zero) value of inductor
        current (in Amps) that flows from N+, through the inductor, to N-. Note that the
        initial conditions (if any) apply only if the UIC option is specified on the
        .TRAN analysis line.
        """
        Device.__init__(self, name, 3)
        self.nodes = [node1, node2, internal]
        self.node2port = {node1: 0, node2: 1, internal: 2}
        self.value = value
        self.ic = ic

    def setup(self, dt):
        self.jac[0, 2] = 1.0
        self.jac[1, 2] = -1.0
        self.jac[2, 0] = 1.0
        self.jac[2, 1] = -1.0
        self.jac[2, 2] = -self.value / dt

    def step(self, t, dt):
        inductor_current = self.subcircuit.across_history[self.nodes[2]]
        self.bequiv[2] = self.value / dt * inductor_current


class K(Device):
    def __init__(self, name, l1name, l2name, value):
        """
        Coupled (Mutual) Inductors

        General form:
        KXXXXXXX LYYYYYYY LZZZZZZZ VALUE
        Examples:
        K43 LAA LBB 0.999
        KXFRMR L1 L2 0.87
        LYYYYYYY and LZZZZZZZ are the names of the two coupled inductors, and VALUE is
        the coefficient of coupling, K, which must be greater than 0 and less than or
        equal to 1. Using the 'dot' convention, place a 'dot' on the first node of each
        inductor.
        """
        Device.__init__(self, name, 6)
        self.name = name
        self.value = value
        self.l1name = l1name
        self.l2name = l2name
        self.node11 = None
        self.node12 = None
        self.internal1 = None
        self.internal2 = None
        self.node21 = None
        self.node22 = None
        self.nodes = None
        self.node2port = None
        self.inductance1 = None
        self.inductance2 = None
        self.mutual = None

    def setup(self, dt):
        inductor1 = self.subcircuit.devices[self.l1name]
        inductor2 = self.subcircuit.devices[self.l2name]
        self.node11, self.node12, self.internal1 = inductor1.nodes
        self.node21, self.node22, self.internal2 = inductor2.nodes
        self.nodes = [self.node11, self.node12, self.internal1, self.node21,
                      self.node22, self.internal2]
        self.node2port = {self.node11: 0, self.node12: 1, self.internal1: 2,
                          self.node21: 3, self.node22: 4, self.internal2: 5}
        self.inductance1 = self.subcircuit.devices[self.l1name].value
        self.inductance2 = self.subcircuit.devices[self.l2name].value
        self.mutual = self.value * math.sqrt(
            self.inductance1 * self.inductance2)
        self.jac[2, 5] = -self.mutual / dt
        self.jac[5, 2] = -self.mutual / dt

    def step(self, t, dt):
        current1 = self.subcircuit.across_history[self.internal1]
        current2 = self.subcircuit.across_history[self.internal2]
        self.bequiv[2] = self.mutual / dt * current2
        self.bequiv[5] = self.mutual / dt * current1


class S(Device):
    """
    General form:

    SXXXXXXX N+ N- NC+ NC- MODEL <ON><OFF>
    WYYYYYYY N+ N- VNAM MODEL <ON><OFF>

    Examples:

    s1 1 2 3 4 switch1 ON
    s2 5 6 3 0 sm2 off
    Switch1 1 2 10 0 smodel1
    w1 1 2 vclock switchmod1
    W2 3 0 vramp sm1 ON
    wreset 5 6 vclck lossyswitch OFF

    Nodes 1 and 2 are the nodes between which the switch terminals are connected. The model name is mandatory while the
    initial conditions are optional. For the voltage controlled switch, nodes 3 and 4 are the positive and negative
    controlling nodes respectively. For the current controlled switch, the controlling current is that through the
    specified voltage source. The direction of positive controlling current flow is from the positive node, through
    the source, to the negative node.

    Switch Model (SW/CSW)

    The switch model allows an almost ideal switch to be described in SPICE. The switch is not quite ideal, in that the
    resistance can not change from 0 to infinity, but must always have a finite positive value. By proper selection of
    the on and off resistances, they can be effectively zero and infinity in comparison to other circuit elements. The
    parameters available are:

    name	parameter	units	default	switch
    VT	threshold voltage	Volts	0.0	S
    IT	threshold current	Amps	0.0	W
    VH	hysteresis voltage	Volts	0.0	S
    IH	hysteresis current	Amps	0.0	W
    RON	on resistance	Z	1.0	both
    ROFF	off resistance	Z	1/GMIN*	both

    *(See the .OPTIONS control line for a description of GMIN, its default value results in an off-resistance of
    1.0e+12 ohms.)

    The use of an ideal element that is highly nonlinear such as a switch can cause large discontinuities to occur in
    the circuit node voltages. A rapid change such as that associated with a switch changing state can cause numerical
    roundoff or tolerance problems leading to erroneous results or timestep difficulties. The user of switches can
    improve the situation by taking the following steps: First, it is wise to set ideal switch impedances just high or
    low enough to be negligible with respect to other circuit elements. Using switch impedances that are close to
    "ideal" in all cases aggravates the problem of discontinuities mentioned above. Of course, when modeling real
    devices such as MOSFETS, the on resistance should be adjusted to a realistic level depending on the size of the
    device being modeled. If a wide range of ON to OFF resistance must be used in the switches (ROFF/RON >1e+12), then
    the tolerance on errors allowed during transient analysis should be decreased by using the .OPTIONS control line
    and specifying TRTOL to be less than the default value of 7.0. When switches are placed around capacitors, then the
    option CHGTOL should also be reduced. Suggested values for these two options are 1.0 and 1e-16 respectively. These
    changes inform SPICE3 to be more careful around the switch points so that no errors are made due to the rapid
    change in the circuit.
    """

    def __init__(self, name, nodes, model=None, vsource=None, on=False,
                 **kwargs):
        """
        Defines a switch device instance for subcircuit.
        :param name: name of switch. Must be unique within subcircuit
        :param ports: sequence of three ports if supplying vsource argument:
        (node1, node2, internal); or 4 ports if no vsource is supplied:
        (node1, node2, control_node1, control_node2)
        :param model: name of switch model to use. Must be defined and added to
        circuit before using here.
        :param vsource: name of the controlling voltage source. Optional
        :param on: defines whether the initial state of the switch is ON at t=0
        """
        Device.__init__(self, name, 3)
        self.name = name
        self.node1 = nodes[0]
        self.node2 = nodes[1]
        self.internal = nodes[2]
        self.nodes = [self.node1, self.node2, self.internal]
        self.node2port = {self.node1: 0, self.node2: 1, self.internal: 2}
        self.cnode1 = None
        self.cnode2 = None

        if len(nodes) == 5:
            self.cnode1 = nodes[3]
            self.cnode2 = nodes[4]

        self.model = model
        self.vsource = vsource
        self.on = on
        self.params = {}
        self.state = on

        # model params:
        self.vt = 0.0
        self.it = 0.0
        self.vh = 0.0
        self.ih = 0.0
        self.ron = 1.0
        self.roff = pyspyce.ONE_OVER_GMIN

        self.kwargs = kwargs

    def setup(self, dt):
        """Initialize the switch model for t=0."""

        # transfer model params from model to member variables (__dict__) if
        # one is asscociated with this switch device:
        if self.model:
            for key in self.model.params:
                if key in self.__dict__:
                    self.__dict__[key] = self.model.params[key]

        # now override with any passed-in keyword args:
        if self.kwargs:
            for key in self.kwargs:
                if key in self.__dict__:
                    self.__dict__[key] = self.kwargs[key]

        # initialize switch state:
        self.state = self.on

        # set constant part of jacobian:
        self.jac[0, 2] = 1.0
        self.jac[1, 2] = -1.0
        self.jac[2, 0] = 1.0
        self.jac[2, 1] = -1.0

        # determine switch state and transition if necessary:
        if self.state:
            self.jac[2, 2] = -self.ron
        else:
            self.jac[2, 2] = -self.roff

        self.bequiv[2] = 0.0

    def step(self, t, dt):
        """Do nothing here. Non-linear device behavior is modeled in minor_step()."""
        pass

    def minor_step(self, k, t, dt):
        """
        Update the jacobian and b-equivalent for this switch for the current minor step iteration.
        :param k: current netwon iteration index
        :param t: current time
        :param dt: current timestep
        :return: None
        """

        # determine control signal:
        control_signal = 0.0
        if self.vsource:
            control_signal = -self.get_across(device=self.vsource)
        else:
            control_signal = self.get_across(self.cnode1, self.cnode2)

        # determine switch state and transition if necessary:
        if control_signal >= self.vt:
            if not self.state:
                self.state = True
                self.jac[2, 2] = -self.ron
                # self.bequiv[2] = self.get_across(0, 1)
        elif control_signal < self.vt:
            if self.state:
                self.state = False
                self.jac[2, 2] = -self.roff
                # self.bequiv[2] = -(self.ron * self.get_across(2))


class W(Device):
    pass  # todo


# Independant Sources:


class V(Device, CurrentSensor):
    """A SPICE Voltage source or current sensor."""

    def __init__(self, name, node1, node2, internal,
                 value, resistance=0.0, inductance=0.0, **kwargs):

        """Create a new SPICE Diode device instance.
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
        """
        Device.__init__(self, name, 3)  # three port device (one internal node)
        self.nodes = [node1, node2, internal]
        self.node2port = {node1: 0, node2: 1, internal: 2}

        self.stimulus = None
        if isinstance(value, Stimulus):
            self.stimulus = value
            self.stimulus.device = self
        else:
            self.value = value

        self.resistance = resistance
        self.inductance = inductance

    def setup(self, dt):
        self.jac[0, 2] = 1.0
        self.jac[1, 2] = -1.0
        self.jac[2, 0] = 1.0
        self.jac[2, 1] = -1.0
        self.jac[2, 2] = -self.resistance + -self.inductance / dt

        volt = 0.0
        if self.stimulus:
            volt = self.stimulus.setup(dt)
        elif self.value:
            volt = self.value

        self.bequiv[2] = volt

    def step(self, t, dt):
        """Step the voltage source.
        """
        if self.stimulus:
            volt = self.stimulus.step(t, dt)
        else:
            volt = self.value

        if self.inductance:
            il = self.get_across_history(2)
            volt += self.inductance / dt * il

        self.bequiv[2] = volt

    def get_current_node(self):
        """
        So this device can be used as a current sensor, this function returns the
        node index of the internal current state variable node.
        """
        return self.nodes[2]


class I(Device):
    """A SPICE Current source or current sensor."""

    def __init__(self, name, node1, node2,
                 value, resistance=0.0, **kwargs):

        """TODO
        """
        Device.__init__(self, name, 2)
        self.nodes = [node1, node2]
        self.node2port = {node1: 0, node2: 1}

        self.stimulus = None
        if isinstance(value, Stimulus):
            self.stimulus = value
            self.stimulus.device = self
        else:
            self.value = value

        self.resistance = resistance

    def setup(self, dt):

        g = 0.0
        if self.resistance > 0.0:
            g = 1.0 / self.resistance

        self.jac[0, 0] = g
        self.jac[0, 1] = -g
        self.jac[1, 0] = -g
        self.jac[1, 1] = g

        current = 0.0
        if self.stimulus:
            current = self.stimulus.setup(dt)
        elif self.value:
            current = self.value

        self.bequiv[0] = current
        self.bequiv[1] = -current

    def step(self, t, dt):
        """Step the current source.
        """
        if self.stimulus:
            current = self.stimulus.step(t, dt)
        else:
            current = self.value

        self.bequiv[0] = current
        self.bequiv[1] = -current


# Linear Dependant Sources:


class G(Device):
    pass  # todo


class E(Device, CurrentSensor):
    """A SPICE E (VCVS) device."""

    def __init__(self, name, nplus, nminus, ncplus, ncminus, internal,
                 value=1.0, **kwargs):

        """General form:

            EXXXXXXX N+ N- NC+ NC- VALUE

        Examples:

            E1 2 3 14 1 2.0
        N+ is the positive node, and N- is the negative node. NC+ and NC- are
        the positive and negative controlling nodes, respectively. VALUE is the
        voltage gain.

        """
        Device.__init__(self, name, 5)
        self.nodes = [nplus, nminus, ncplus, ncminus, internal]

        self.node2port = {nplus: 0,
                          nminus: 1,
                          ncplus: 2,
                          ncminus: 3,
                          internal: 4}  # define node-to-port mapping

        self.value = value  # store value (gain)

    def setup(self, dt):
        """Define the VCVS jacobian stamp."""
        np, nm, ncp, ncm, ik = 0, 1, 2, 3, 4

        self.jac[np, ik] = 1.0
        self.jac[nm, ik] = -1.0
        self.jac[ik, np] = -1.0
        self.jac[ik, nm] = 1.0
        self.jac[ik, ncp] = self.value
        self.jac[ik, ncm] = -self.value

    def step(self, t, dt):
        """Do nothing here. Linear and time-invariant device."""
        pass

    def get_current_node(self):
        """Return the current node."""
        return self.nodes[4]


class F(Device):
    pass  # todo


class H(Device):
    pass  # todo


# Non-linear Dependant Sources:


class B(Device):
    pass  # todo


# Transmission Lines:


class T(Device):
    pass  # todo


class O(Device):
    pass  # todo


class U(Device):
    pass  # todo


# Diodes and Transistors:


class D(Device):
    """Represents a SPICE Diode device."""

    def __init__(self, name, nplus, nminus, mname=None, area=None, off=None,
                 ic=None, temp=None, **kwargs):
        """
        General form:

             DXXXXXXX N+ N- MNAME <AREA> <OFF> <IC=VD> <TEMP=T>

        Examples:

             DBRIDGE 2 10 DIODE1
             DCLMP 3 7 DMOD 3.0 IC=0.2

        N+ and N- are the positive and negative nodes, respectively. MNAME is the model name,
        AREA is the area factor, and OFF indicates an (optional) starting condition on the
        device for dc analysis. If the area factor is omitted, a value of 1.0 is assumed. The
        (optional) initial condition specification using IC=VD is intended for use with the
        UIC option on the .TRAN control line, when a transient analysis is desired starting
        from other than the quiescent operating point. The (optional) TEMP value is the
        temperature at which this device is to operate, and overrides the temperature
        specification on the .OPTION control line.
        """
        Device.__init__(self, name, 2)
        self.nodes = [nplus, nminus]
        self.node2port = {nplus: 0, nminus: 1}
        self.mname = mname
        self.area = area
        self.off = off
        self.ic = ic
        self.temp = temp
        self.kwargs = kwargs  # these will be used to override the default or model params (see setup() function)

        # model parameters:
        self.Is = 1.0e-14  # can't be 'is' because 'is' is a keyword
        self.rs = 0.0
        self.n = 1.0
        self.tt = 0.0
        self.cjo = 0.0
        self.vj = 1.0
        self.m = 0.5
        self.eg = 1.11
        self.xti = 3.0
        self.kf = 0.0
        self.af = 1.0
        self.fc = 0.5
        self.bv = float('inf')
        self.ibv = 1.0e-3
        self.tnom = 27.0
        self.model = None

    def setup(self, dt):
        """Initialize the diode device at t-0."""

        # transfer model params from model to member variables (__dict__)
        # if one is asscociated with this device:
        if self.model:
            for key in self.model.params:
                if key in self.__dict__:
                    self.__dict__[key] = self.model.params[key]

        # now override with any passed-in keyword args:
        if self.kwargs:
            for key in self.kwargs:
                if key in self.__dict__:
                    self.__dict__[key] = self.kwargs[key]

    def step(self, t, dt):
        """ Do nothing here. Non-linear device."""
        pass

    def minor_step(self, k, t, dt):
        vt = 25.85e-3
        v = self.get_across(0, 1)
        v = min(v, 0.8)
        geq = self.Is / vt * math.exp(v / vt)
        ieq = self.Is * (math.exp(v / vt) - 1.0)
        beq = ieq - geq * v
        self.jac[0, 0] = geq
        self.jac[0, 1] = -geq
        self.jac[1, 0] = -geq
        self.jac[1, 1] = geq
        self.bequiv[0] = -beq
        self.bequiv[1] = beq


class Q(Device):
    pass  # todo


class J(Device):
    pass  # todo


class M(Device):
    pass  # todo


class Z(Device):
    pass  # todo


# Experimental:


class GenericTwoPort(Device):
    """
    EXPERIMENTAL
    Device that allows the definition of a two port device with an arbitrary
    non-linear current function.
    """

    def __init__(self, name, node1, node2, i):
        """
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
        """
        Device.__init__(self, name, 2)
        self.nodes = [node1, node2]
        self.node2port = {node1: 0, node2: 1}
        self.i = i
        # self.g = sympy.diff(i, v)
        # self.get_g = sympy.lambdify(v, self.g, "math")
        # self.get_i = sympy.lambdify(v, self.i, "math")

    def setup(self, dt):
        pass

    def step(self, t, dt):
        pass

    def minor_step(self, k, t, dt):
        v = (self.subcircuit.across[self.nodes[1]] -
             self.subcircuit.across[self.nodes[0]])

        g = self.get_g(v)
        i = self.get_i(v) - g * v
        self.jac[0, 0] = g
        self.jac[0, 1] = -g
        self.jac[1, 0] = -g
        self.jac[1, 1] = g
        self.bequiv[0] = -i
        self.bequiv[1] = i


# Models:


class RMod(Model):
    """Semiconductor resistor model."""

    def __init__(self, name, **kwargs):
        """
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
        """
        Model.__init__(self, name, **kwargs)


class CMod(Model):
    """Semiconductor capacitor model."""

    def __init__(self, name, **kwargs):
        """
        todo: add docs from spice docs
        """
        Model.__init__(self, name, **kwargs)


class SwMod(Model):
    """ Voltage controlled switch model"""

    def __init__(self, name, **kwargs):
        """
        todo: add docs from spice docs
        """
        Model.__init__(self, name, **kwargs)


class CwMod(Model):
    """Current controlled switch model."""

    def __init__(self, name, **kwargs):
        """
        todo: add docs from spice docs
        """
        Model.__init__(self, name, **kwargs)


class UrcMod(Model):
    """Uniform distributed RC model."""

    def __init__(self, name, **kwargs):
        """
        todo: add docs from spice docs
        """
        Model.__init__(self, name, **kwargs)


class LtraMod(Model):
    """Lossy transmission line model """

    def __init__(self, name, **kwargs):
        """
        todo: add docs from spice docs
        """
        Model.__init__(self, name, **kwargs)


class DMod(Model):
    def __init__(self, name, **kwargs):
        """
        The dc characteristics of the diode are determined by the parameters IS and N.
        An ohmic resistance, RS, is included. Charge storage effects are modeled by a
        transit time, TT, and a nonlinear depletion layer capacitance which is determined
        by the parameters CJO, VJ, and M. The temperature dependence of the saturation
        current is defined by the parameters EG, the energy and XTI, the saturation
        current temperature exponent. The nominal temperature at which these parameters
        were measured is TNOM, which defaults to the circuit-wide value specified on the
        .OPTIONS control line. Reverse breakdown is modeled by an exponential increase in
        the reverse diode current and is determined by the parameters BV and IBV (both of
        which are positive numbers).

        #  name parameter                        units default example
        --------------------------------------------------------------
        1  IS   saturation current               A     1.0e-14 1.0e-14
        2  RS   ohmic resistance                 Z     0       10
        3  N    emission coefficient             -     1       1.0
        4  TT   transit-time                     sec   0       0.1ns
        5  CJO  zero-bias junction capacitance   F     0       2pF
        6  VJ   junction potential               V     1       0.6
        7  M    grading coefficient              -     0.5     0.5
        8  EG   activation energy                eV    1.11    1.11 Si, 0.69 Sbd, 0.67 Ge
        9  XTI  saturation-current temp. exp     -     3.0     3.0 jn, 2.0 Sbd
        10 KF   flicker noise coefficient        -     0       -
        11 AF   flicker noise exponent           -     1       -
        12 FC   coef. forward-bias depletion cap -     0.5     -
        13 BV   reverse breakdown voltage        V     inf     40.0
        14 IBV  current at breakdown voltage     A     1.0e-3  -
        15 TNOM parameter measurement temp       degC  27      50

        """
        Model.__init__(self, name, **kwargs)


class NpnMod(Model):
    """NPN BJT model."""

    def __init__(self, name, **kwargs):
        """
        todo: add docs from spice docs
        """
        Model.__init__(self, name, **kwargs)


class PnpMod(Model):
    """PNP BJT model."""

    def __init__(self, name, **kwargs):
        """
        todo: add docs from spice docs
        """
        Model.__init__(self, name, **kwargs)


class NfjMod(Model):
    """N-channel JFET model"""

    def __init__(self, name, **kwargs):
        """
        todo: add docs from spice docs
        """
        Model.__init__(self, name, **kwargs)


class PfjMod(Model):
    """P-channel JFET model."""

    def __init__(self, name, **kwargs):
        """
        todo: add docs from spice docs
        """
        Model.__init__(self, name, **kwargs)


class NmosMod(Model):
    """N-channel MOSFET model"""

    def __init__(self, name, **kwargs):
        """
        todo: add docs from spice docs
        """
        Model.__init__(self, name, **kwargs)


class PmosMod(Model):
    """P-channel MOSFET model."""

    def __init__(self, name, **kwargs):
        """
        todo: add docs from spice docs
        """
        Model.__init__(self, name, **kwargs)


class NmfMod(Model):
    """N-channel MESFET model"""

    def __init__(self, name, **kwargs):
        """
        todo: add docs from spice docs
        """
        Model.__init__(self, name, **kwargs)


class PmfMod(Model):
    """P-channel MESFET model."""

    def __init__(self, name, **kwargs):
        """
        todo: add docs from spice docs
        """
        Model.__init__(self, name, **kwargs)


# Stimuli:


class Pulse(Stimulus):
    def __init__(self, v1, v2, td=0.0, tr=None, tf=None, pw=None, per=None):
        """
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

        time        value
        -----------------
        0           V1
        TD          V1
        TD+TR       V2
        TD+TR+PW    V2
        TD+TR+PW+TF V1
        TSTOP       V1

        Intermediate points are determined by linear interpolation.
        """
        self.v1 = v1
        self.v2 = v2
        self.td = td
        self.tr = tr
        self.tf = tf
        self.pw = pw
        self.per = per
        self.device = None

    def setup(self, dt):
        if self.tr is None:
            self.tr = dt
        if self.tf is None:
            self.tf = dt
        if self.pw is None:
            self.pw = dt
        if self.per is None:
            self.per = self.td + 3.0 * dt
        return self.v1

    def step(self, t, dt):
        t %= self.per
        if (self.td + self.tr) <= t < (self.td + self.tr + self.pw):
            return self.v2
        elif self.td <= t < (self.td + self.tr):
            return self.v1 + (self.v2 - self.v1) * (t - self.td) / self.tr
        elif (self.td + self.tr + self.pw) <= t < (
                    self.td + self.tr + self.pw + self.tf):
            return self.v2 + (self.v1 - self.v2) * (
            t - (self.td + self.tr + self.pw)) / self.tf
        else:
            return self.v1


class Sin(Stimulus):
    """Models a sin wave stimulus for independent sources."""

    def __init__(self, vo=0.0, va=1.0, freq=1.0, td=0.0, theta=0.0, phi=0.0):
        """
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
        TD to TSTOP	VO+VA.exp[-(t-TD)/THETA].sin[2pi.FREQ.(t+TD)]
        """
        self.vo = vo
        self.va = va
        self.freq = freq
        self.td = td
        self.theta = theta
        self.phi = phi
        self.device = None

    def setup(self, dt):
        """Sets up the pulse stimulus and returns the initial output."""
        return self.step(0, dt)

    def step(self, t, dt):
        """Update and return the stimulus value at the current time."""
        if t < self.td:
            return 0.0
        elif self.theta:
            return (self.vo + self.va * math.exp(-(t + self.td) / self.theta) *
                    math.sin(2.0 * math.pi * self.freq
                             * (t + self.td) + self.phi))
        else:
            return self.vo + self.va * math.sin(
                2.0 * math.pi * self.freq * (t + self.td) + self.phi)


class Exp(Stimulus):
    """Generates a SPICE EXP stimulus for independant sources."""

    def __init__(self, v1, v2, td1=0.0, tau1=None, td2=None, tau2=None):
        """
        Define a pulse stimulus.
        :param v1: initial value (V or A)
        :param v2: pulsed value (V or A)
        :param td1: rise time delay, default=0.0 (s)
        :param tau1: rise time constant default=None (will be set to timestep) (s)
        :param td2: fall delay time, default=None (will be set to td1 + timestep) (s)
        :param tau2: fall time constant, default=None (will be set to timestep) (s)
        :return: None
        """
        self.v1 = v1
        self.v2 = v2
        self.td1 = td1
        self.tau1 = tau1
        self.td2 = td2
        self.tau2 = tau2

    def setup(self, dt):
        """Initialize the Exp output at time 0s."""
        if not self.tau1:
            self.tau1 = dt
        if not self.td2:
            self.td2 = self.td1 + dt
        if not self.tau2:
            self.tau2 = dt
        return self.step(dt)

    def step(self, t, dt):
        """Update and return the current value of the Exp stimulus"""
        if 0.0 >= t < self.td1:
            return self.v1
        elif self.td1 <= t < self.td1:
            return self.v1 + (self.v2 - self.v2) * (
            1.0 - math.exp(-(t - self.td1) / self.tau1))
        else:
            return (1.0 + (self.v2 - self.v1)
                    * (1.0 - math.exp(-(t - self.td1) / self.tau1))
                    + (self.v1 - self.v2) * (
            1.0 - math.exp(-(t - self.td2) / self.tau2)))


class Pwl(Stimulus):
    """TODO Doc"""
    def __init__(self, *time_voltage_pairs):
        self.xp = []
        self.yp = []
        for time, value in time_voltage_pairs:
            try:
                self.xp.append(float(time))
                self.yp.append(float(value))
            except ValueError as e:
                pass
            pass

    def setup(self, dt):
        pass

    def step(self, dt):
        x = self.device.get_time()
        return self.interp(x)

    def interp(self, x):
        if x <= self.xp[0]:
            return self.yp[0]
        elif x >= self.xp[-1]:
            return self.yp[-1]
        else:
            itr = 1
            while x > self.xp[itr] and itr < (len(self.xp) - 1):
                itr += 1
            x0, y0 = self.xp[itr - 1], self.yp[itr - 1]
            x1, y1 = self.xp[itr], self.yp[itr]
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


class Sffm(Stimulus):
    def __init__(self, vo, va, fc, md1, fs):
        pass  # todo

    def setup(self, dt):
        pass

    def step(self, dt):
        pass


# Main:
if __name__ == '__main__':
    pass  # TODO: test code here