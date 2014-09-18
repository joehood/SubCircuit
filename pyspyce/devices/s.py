"""S (voltage controled switch) Device."""

import pyspyce.sandbox as sb
import pyspyce.interfaces as inter


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
        inter.MNADevice.__init__(self, name, 3)
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
        self.roff = 1.0E12

        self.kwargs = kwargs

    def start(self, dt):
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
            control_signal = self.get_across(self.cnode1, self.cnode2)

        # determine switch state and transition/update jac if necessary:
        if control_signal >= self.vt:
            if not self.state:
                self.state = True
                self.jac[2, 2] = -self.ron
        elif control_signal < self.vt:
            if self.state:
                self.state = False
                self.jac[2, 2] = -self.roff

        # update beq:
        if self.state:
            self.bequiv[2] = -(self.ron * self.get_across(2))
        else:
            self.bequiv[2] = self.get_across(0, 1)

    def get_current_node(self):
        return self.nodes[2]