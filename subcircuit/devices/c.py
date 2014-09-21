"""C (capacitor) device."""

import subcircuit.interfaces as inter
import subcircuit.sandbox as sb


class C(inter.MNADevice):
    """SPICE capacitor device"""

    def __init__(self, nodes, value, mname=None, l=None, w=None, ic=None,
                 **parameters):

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

        name    parameter                         units  default  example
        -----------------------------------------------------------------
        CJ      junction bottom capacitance       F m-2  -        5e-5
        CJSW    junction sidewall capacitance     F m-1  -        2e-11
        DEFW    default device width              m      1e-6     2e-6
        NARROW  narrowing due to side etching     m      0.0      1e-7

        The capacitor has a capacitance computed as

        CAP = CJ(LENGTH - NARROW)(WIDTH - NARROW) + 2.CJSW(LENGTH + WIDTH - 2.NARROW)
        """
        inter.MNADevice.__init__(self, nodes, 0, **parameters)
        self.value = value
        self.ic = ic

    def connect(self):
        npos, nneg = self.nodes
        self.port2node = {0: self.get_node_index(npos),
                          1: self.get_node_index(nneg)}

    def start(self, dt):
        self.jac[0, 0] = self.value / dt
        self.jac[0, 1] = -self.value / dt
        self.jac[1, 0] = -self.value / dt
        self.jac[1, 1] = self.value / dt

    def step(self, dt, t):
        vc = self.get_across_history(0, 1)
        self.bequiv[0] = self.value / dt * vc
        self.bequiv[1] = -self.value / dt * vc


class CBlock(sb.Block):
    """Schematic graphical inteface for L device."""
    friendly_name = "Capacitor"
    family = "Elementary"
    label = "C"
    engine = C

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name, C)

        # ports:
        self.ports['positive'] = sb.Port(self, 0, (60, 0))
        self.ports['negative'] = sb.Port(self, 1, (60, 100))

        # properties:
        self.properties['Capacitance (F)'] = 0.1

        # leads:
        self.lines.append(((60, 0), (60, 40)))
        self.lines.append(((60, 60), (60, 100)))

        # plates:
        self.lines.append(((40, 40), (80, 40)))
        self.lines.append(((40, 60), (80, 60)))

    def get_engine(self, nodes):
        return C(nodes, self.properties['Capacitance (F)'])

