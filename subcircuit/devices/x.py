"""X (resistor or semiconductor resistor) device."""

import subcircuit.interfaces as inter
import subcircuit.sandbox as sb


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
        self.properties['Subckt Name'] = "RLCSeries"
        self.properties['Port 1 Name'] = "1"
        self.properties['Port 2 Name'] = "2"
        self.properties['Device 1'] = "R((1, 3), 1.0)"
        self.properties['Device 2'] = "L((3, 4), 0.001)"
        self.properties['Device 3'] = "C((4, 2), 0.001)"
        self.properties['Device 4'] = ""
        self.properties['Device 5'] = ""
        self.properties['Device 6'] = ""
        self.properties['Device 7'] = ""
        self.properties['Device 8'] = ""
        self.properties['Device 9'] = ""

        # leads:
        self.lines.append(((60, 0), (60, 20), (45, 25), (75, 35), (45, 45),
                           (75, 55), (45, 65), (75, 75), (60, 80), (60, 100)))


    def get_engine(self, nodes, netlist=None):

        ports = self.properties['Port 1 Name'], self.properties['Port 2 Name']
        subckt = inter.Subckt(ports)
        if netlist:
            netlist.subckt(self.properties['Subckt Name'], subckt)
        for i in range(1, 10):
            devicedef = self.properties["Device {0}".format(i)]
            if devicedef.strip():
                try:
                    device = eval(devicedef, globals(), locals())
                    subckt.device(devicedef, device)
                except Exception as e:
                    print(e.message)

        return X(nodes, self.properties['Subckt Name'])

