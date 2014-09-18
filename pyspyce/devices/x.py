"""X (resistor or semiconductor resistor) device."""

import pyspyce.interfaces as inter
import pyspyce.sandbox as sb


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


class XBlock2Port(sb.Block):
    """Schematic graphical inteface for R device."""
    friendly_name = "Subcircuit 2-Port"
    family = "Subcircuit"
    label = "X"
    engine = X

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name)

        # ports:
        self.ports['port1'] = sb.Port(self, 0, (60, 0))
        self.ports['port2'] = sb.Port(self, 1, (60, 100))

        # properties:
        self.properties['Subckt Name'] = "MySubckt"
        self.properties['Port 1 name'] = "1"
        self.properties['Port 2 name'] = "2"
        self.properties['Definition'] = "R((1, 2), 10.0)"


        # leads:
        self.lines.append(((60, 0), (60, 20), (45, 25), (75, 35), (45, 45),
                           (75, 55), (45, 65), (75, 75), (60, 80), (60, 100)))

        # box:


    def get_engine(self, nodes):
        ports = self.properties['Port 1 name'], self.properties['Port 2 name']
        subckt = inter.Subckt(ports)
        devicedefs = self.properties["Definition"].split("\n")
        for devicedef in devicedefs:
            device = eval(devicedef)
            subckt.device(devicedef, device)
        return X(nodes, subckt)

