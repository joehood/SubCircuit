"""R (resistor or semiconductor resistor) device."""

import interfaces as inter
import sandbox as sb


class X(inter.MNADevice):
    """Subckt instance device (SPICE X)"""

    def __init__(self, nodes, subckt, **parameters):
        """Creates a new subckt instance device
        :param nodes: Device extrnal node names
        :param subckt: Subckt name
        :param parameters: Dictionary of parameters for the subcircuit instance
        :return: New subckt instance device
        """
        inter.MNADevice.__init__(self, nodes, 0, **parameters)
        self.subckt = subckt
        self.parameters = parameters

    def connect(self):
        """Maps the ports to the system node indexes.
        :return: None
        """
        self.port2node = {}
        for p, n in zip(self.netlist.subckts[self.subckt].ports, self.nodes):
            self.port2node[p] = n
