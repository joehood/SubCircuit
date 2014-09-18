"""E (Voltage controlled voltage source) Device."""

import pyspyce.sandbox as sb
import pyspyce.interfaces as inter


class E(inter.MNADevice, inter.CurrentSensor):
    """A SPICE E (VCVS) device."""

    def __init__(self, name, nplus, nminus, ncplus, ncminus, internal,
                 value=1.0, limit=None, **kwargs):

        """Create a new SPICE E (VCVS) device.

        :param name: Name of device. Must be unique within the subcircuit
        :param nplus: Positive port on secondary
        :param nminus: Negative port on secondary
        :param ncplus: Positive port on primary (control)
        :param ncminus: Negative port on primary (control)
        :param internal: Internal node for branch current
        :param value: Either fixed value or transfer function table
        Examples:
        value=10.0  # fixed value
        value=Table((-1, 0), (0, 0), (0.0001, 1))  # lookup table
        TODO: add stimulus option.
        :param kwargs: Additional keyword arguments
        :return: New E instance

        General form:

            EXXXXXXX N+ N- NC+ NC- VALUE

        Examples:

            E1 2 3 14 1 2.0
        N+ is the positive node, and N- is the negative node. NC+ and NC- are
        the positive and negative controlling nodes, respectively. VALUE is the
        voltage gain.

        """
        inter.MNADevice.__init__(self, name, 5)
        self.nodes = [nplus, nminus, ncplus, ncminus, internal]

        self.node2port = {nplus: 0,
                          nminus: 1,
                          ncplus: 2,
                          ncminus: 3,
                          internal: 4}  # define node-to-port mapping

        self.gain = None
        self.table = None

        if isinstance(value, float) or isinstance(value, int):
            self.gain = float(value)

        elif isinstance(value, inter.Table):
            self.table = value

        self.subckt = None
        self.limit = limit

    def start(self, dt):
        """Define the initial VCVS jacobian stamp."""

        if self.gain:
            k = self.gain
        else:
            k = 0.0

        self.jac[0, 4] = 1.0
        self.jac[1, 4] = -1.0
        self.jac[4, 0] = -1.0
        self.jac[4, 1] = 1.0
        self.jac[4, 2] = k
        self.jac[4, 3] = -k

    def step(self, dt, t):
        """TODO Doc"""

        if self.table:
            vc = self.get_across(2, 3)
            k = self.table.output(vc)  # get gain for this control voltage

            if self.limit and not vc == 0.0:
                if vc * k > self.limit:
                    k = self.limit / vc
                if vc * k < -self.limit:
                    k = -self.limit / vc

            self.jac[4, 2] = k
            self.jac[4, 3] = -k

    def get_current_node(self):
        """Return the current node."""
        return self.nodes[4]
