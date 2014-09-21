"""S (voltage controled switch) Device."""

import subcircuit.sandbox as sb
import subcircuit.interfaces as inter


class S(inter.MNADevice, inter.CurrentSensor):
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

    Nodes 1 and 2 are the nodes between which the switch terminals are
    connected. The model name is mandatory while the initial conditions are
    optional. For the voltage controlled switch, nodes 3 and 4 are the positive
    and negative controlling nodes respectively. For the current controlled
    switch, the controlling current is that through the specified voltage
    source. The direction of positive controlling current flow is from the
    positive node, through the source, to the negative node.

    Switch Model (SW/CSW)

    The switch model allows an almost ideal switch to be described in SPICE.
    The switch is not quite ideal, in that the resistance can not change from 0
    to infinity, but must always have a finite positive value. By proper
    selection of the on and off resistances, they can be effectively zero and
    infinity in comparison to other circuit elements. The parameters available
    are:

    name   parameter            units    default  switch
    ----------------------------------------------------
    VT     threshold voltage    Volts    0.0      S
    IT     threshold current    Amps     0.0      W
    VH     hysteresis voltage   Volts    0.0      S
    IH     hysteresis current   Amps     0.0      W
    RON    on resistance        Z        1.0      both
    ROFF   off resistance       Z        1/GMIN*  both

    *(See the .OPTIONS control line for a description of GMIN, its default
    value results in an off-resistance of 1.0e+12 ohms.)

    The use of an ideal element that is highly nonlinear such as a switch can
    cause large discontinuities to occur in the circuit node voltages. A rapid
    change such as that associated with a switch changing state can cause
    numerical roundoff or tolerance problems leading to erroneous results or
    timestep difficulties. The user of switches can improve the situation by
    taking the following steps: First, it is wise to set ideal switch impedances
    just high or low enough to be negligible with respect to other circuit
    elements. Using switch impedances that are close to "ideal" in all cases
    aggravates the problem of discontinuities mentioned above. Of course, when
    modeling real devices such as MOSFETS, the on resistance should be adjusted
    to a realistic level depending on the size of the device being modeled. If
    a wide range of ON to OFF resistance must be used in the switches
    (ROFF/RON >1e+12), then the tolerance on errors allowed during transient
    analysis should be decreased by using the .OPTIONS control line and
    specifying TRTOL to be less than the default value of 7.0. When switches
    are placed around capacitors, then the option CHGTOL should also be reduced.
    Suggested values for these two options are 1.0 and 1e-16 respectively. These
    changes inform SPICE3 to be more careful around the switch points so that no
    errors are made due to the rapid change in the circuit.
    """
    RON = 1.0E-6
    ROFF = 1.0E6

    def __init__(self, nodes, model=None, vsource=None, on=False,
                 **parameters):
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
        inter.MNADevice.__init__(self, nodes, 1, **parameters)

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
        self.ron = S.RON
        self.roff = S.ROFF

        self.parameters = parameters

        self.ncp, self.ncm, self.np, self.nm = None, None, None, None

    def connect(self):
        self.ncp, self.ncm, self.np, self.nm = self.nodes
        self.port2node = {0: self.get_node_index(self.ncp),
                          1: self.get_node_index(self.ncm),
                          2: self.get_node_index(self.np),
                          3: self.get_node_index(self.nm),
                          4: self.create_internal("{0}_int".format(self.name))}


    def start(self, dt):
        """Initialize the switch model for t=0."""

        # transfer model params from model to member variables (__dict__) if
        # one is asscociated with this switch device:
        if self.model:
            for key in self.model.params:
                if key in self.__dict__:
                    self.__dict__[key] = self.model.params[key]

        # now override with any passed-in keyword args:
        if self.parameters:
            for key in self.parameters:
                if key in self.__dict__:
                    self.__dict__[key] = self.parameters[key]

        # initialize switch state:
        self.state = self.on

        # set constant part of jacobian:
        self.jac[2, 4] = 1.0
        self.jac[3, 4] = -1.0
        self.jac[4, 2] = 1.0
        self.jac[4, 3] = -1.0

        # determine switch state and transition if necessary:
        if self.state:
            self.jac[4, 4] = -self.ron
        else:
            self.jac[4, 4] = -self.roff

        self.bequiv[4] = 0.0

    def step(self, dt, t):
        """Do nothing here. Non-linear behavior is modeled in minor_step()."""
        pass

    def minor_step(self, dt, t, k):
        """
        Update the jacobian and b-equivalent for this switch for this iteration.
        :param k: current netwon iteration index
        :param t: current time
        :param dt: current timestep
        :return: None
        """

        # determine control signal:
        control_signal = 0.0
        if self.vsource:
            control_signal = self.get_across(external_device=self.vsource)
        else:
            control_signal = self.get_across(0, 1)

        # determine switch state and transition/update jac if necessary:
        if control_signal >= self.vt:
            if not self.state:
                self.state = True
                self.jac[4, 4] = -self.ron
        elif control_signal < self.vt:
            if self.state:
                self.state = False
                self.jac[4, 4] = -self.roff

        # update beq:
        if self.state:
            self.bequiv[4] = -(self.ron * self.get_across(2))
        else:
            self.bequiv[4] = self.get_across(0, 1)

    def get_current_node(self):
        return self.nodes[4], 1.0


class SBlock(sb.Block):
    """Schematic graphical inteface for S device."""
    friendly_name = "Voltage Controlled Switch (S)"
    family = "Switches"
    label = "S"
    engine = S

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name)

        # ports:
        self.ports['control positive'] = sb.Port(self, 0, (20, 40))
        self.ports['control negative'] = sb.Port(self, 1, (20, 60))
        self.ports['positive'] = sb.Port(self, 2, (60, 0))
        self.ports['negative'] = sb.Port(self, 3, (60, 100))

        # properties:

        # leads:
        self.lines.append(((60, 0), (60, 35)))
        self.lines.append(((60, 65), (60, 100)))

        self.lines.append(((20, 40), (35, 40)))
        self.lines.append(((20, 60), (35, 60)))

        # box:
        self.lines.append(((60, 65), (75, 38)))
        self.rects.append((35, 20, 50, 60, 3))


    def get_engine(self, nodes):
        return S(nodes)

