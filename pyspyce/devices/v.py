"""V (independant voltage source) device."""

import math
import pyspyce.interfaces as inter
import pyspyce.sandbox as sb
import pyspyce.stimuli as stim


class V(inter.MNADevice, inter.CurrentSensor):
    """A SPICE Voltage source or current sensor."""

    def __init__(self, nodes, value, res=0.0, induct=0.0, **kwargs):

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
        inter.MNADevice.__init__(self, nodes, 1, **kwargs)

        # determine type of value provided:
        if isinstance(value, inter.Stimulus):
            self.stimulus = value
            self.stimulus.device = self
        elif isinstance(value, float) or isinstance(value, int):
            self.stimulus = None
            self.value = float(value)

        self.res = res
        self.induct = induct

    def connect(self):
        nplus, nminus = self.nodes
        self.port2node = {0: self.get_node_index(nplus),
                          1: self.get_node_index(nminus),
                          2: self.create_internal("{0}_int".format(self.name))}

    def start(self, dt):

        self.jac[0, 2] = 1.0
        self.jac[1, 2] = -1.0
        self.jac[2, 0] = 1.0
        self.jac[2, 1] = -1.0
        self.jac[2, 2] = -(self.res + self.induct / dt)

        volt = 0.0
        if self.stimulus:
            volt = self.stimulus.start(dt)
        elif self.value:
            volt = self.value

        self.bequiv[2] = volt

    def step(self, dt, t):

        if self.stimulus:
            volt = self.stimulus.step(dt, t)
        else:
            volt = self.value

        if self.induct:
            il = self.get_across_history(2)
            volt += self.induct / dt * il

        self.bequiv[2] = volt

    def get_current_node(self):
        return self.port2node[2], -1.0


class VBlock(sb.Block):
    """Schematic graphical inteface for V device."""
    friendly_name = "Voltage Source (DC)"
    family = "Sources"
    label = "V"
    engine = V

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name, V)

        # ports:
        self.ports['positive'] = sb.Port(self, 0, (60, 0))
        self.ports['negative'] = sb.Port(self, 1, (60, 100))

        # properties:
        self.properties['Voltage (V)'] = 1.0

        # leads:
        self.lines.append(((60, 0), (60, 25)))
        self.lines.append(((60, 75), (60, 100)))

        # plus:
        self.lines.append(((60, 33), (60, 43)))
        self.lines.append(((55, 38), (65, 38)))

        # circle
        self.circles.append((60, 50, 25))

    def get_engine(self, nodes):
        return V(nodes, self.properties['Voltage (V)'])


class VSinBlock(sb.Block):
    friendly_name = "Voltage Source (Sine)"
    family = "Sources"
    label = "VSIN"
    engine = V

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name, V)

        # ports:
        self.ports['positive'] = sb.Port(self, 0, (60, 0))
        self.ports['negative'] = sb.Port(self, 1, (60, 100))

        # properties:
        self.properties['Voltage Offset (V)'] = 0.0
        self.properties['Voltage Amplitude (V)'] = 1.0
        self.properties['Frequency (Hz)'] = 60.0
        self.properties['Delay (s)'] = 0.0
        self.properties['Damping factor (1/s)'] = 0.0
        self.properties['Phase (rad)'] = 0.0

        # leads:
        self.lines.append(((60, 0), (60, 25)))
        self.lines.append(((60, 75), (60, 100)))

        # plus:
        self.lines.append(((60, 33), (60, 43)))
        self.lines.append(((55, 38), (65, 38)))

        # circle
        self.circles.append((60, 50, 25))

        # sine:
        a1 = math.pi * 1.0
        a2 = math.pi * 0.0
        self.arcs.append((53, 58, 7, a1, a2, True))
        self.arcs.append((67, 58, 7, -a1, -a2, False))

    def get_engine(self, nodes):
        vo = self.properties['Voltage Offset (V)']
        va = self.properties['Voltage Amplitude (V)']
        freq = self.properties['Frequency (Hz)']
        td = self.properties['Delay (s)']
        theta = self.properties['Damping factor (1/s)']
        phi = self.properties['Phase (rad)']

        sin = stim.Sin(vo, va, freq, td, theta, phi)
        return V(nodes, sin)


class VPulseBlock(sb.Block):
    friendly_name = "Voltage Source (Pulse)"
    family = "Sources"
    label = "VPULSE"
    engine = V

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name, V)

        # ports:
        self.ports['positive'] = sb.Port(self, 0, (60, 0))
        self.ports['negative'] = sb.Port(self, 1, (60, 100))

        # properties:
        self.properties['Voltage 1 (V)'] = 0.0
        self.properties['Voltage 2 (V)'] = 1.0
        self.properties['Delay (s)'] = 0.0
        self.properties['Rise Time (s)'] = 0.0
        self.properties['Fall Time (s)'] = 0.0
        self.properties['Width (s)'] = 0.01
        self.properties['Period (s)'] = 0.02

        # leads:
        self.lines.append(((60, 0), (60, 25)))
        self.lines.append(((60, 75), (60, 100)))

        # plus:
        self.lines.append(((60, 33), (60, 43)))
        self.lines.append(((55, 38), (65, 38)))

        # circle
        self.circles.append((60, 50, 25))

        # pulse:
        self.lines.append(((45, 60), (55, 60), (55, 50),
                           (65, 50), (65, 60), (75, 60)))

    def get_engine(self, nodes):
        v1 = self.properties['Voltage 1 (V)']
        v2 = self.properties['Voltage 2 (V)']
        td = self.properties['Delay (s)']
        tr = self.properties['Rise Time (s)']
        tf = self.properties['Fall Time (s)']
        pw = self.properties['Width (s)']
        per = self.properties['Period (s)']

        pulse = stim.Pulse(v1, v2, td, tr, tf, pw, per)
        return V(nodes, pulse)

