"""LIM DQ Branch device.
"""

import math

import subcircuit.interfaces as inter
import subcircuit.sandbox as sb
import subcircuit.qdl as qdl


class DqBranch(inter.MNADevice):

    """RLV Branch DQ Dynamic Phasor Model.

                 .-------------------------------------.
                 |  vd(t)    id*(r + w*L)      id'*L   |
                 |   ,-.    +            -    +     -  |
     inodep  o---|--(- +)---------VVV-----------UUU----|---o  jnodep  
                 |   `-'             id -->            |
                 |                                     |
                 |  vq(t)    iq*(r + w*L)      iq'*L   |
                 |   ,-.    +            -    +     -  |
     inodeq  o---|--(- +)---------VVV-----------UUU----|---o  jnodeq
                 |   `-'             iq -->            |
                 |                                     |
                 '-------------------------------------'
    """

    def __init__(self, nodes, l, r=0.0, vd0=0.0, vq0=0.0, w=188.0, id0=0.0,
                 iq0=0.0, source_type=qdl.SourceType.CONSTANT, 
                 vd1=0.0, vd2=0.0, vda=0.0, freqd=0.0, phid=0.0, dutyd=0.0,
                 td1=0.0, td2=0.0, vq1=0.0, vq2=0.0, vqa=0.0,
                 freqq=0.0, phiq=0.0, dutyq=0.0, tq1=0.0, tq2=0.0, dq=1e0,
                 **parameters):

        if len(nodes) == 2:
            inter.MNADevice.__init__(self, nodes, 1, **parameters)

        self.l = l
        self.r = r
        self.w = w
        self.id0 = id0
        self.iq0 = iq0

    def connect(self):
        inode, jnode = self.nodes
        self.port2node = {0: self.get_node_index(self.nodes[0]),
                          1: self.get_node_index(jnode)}

    def start(self, dt):
        self.jac[0, 0] = 1.0
        self.jac[1, 1] = -1.0
        self.jac[1, 0] = 1.0
        self.jac[1, 1] = -1.0


class DqCableBlock(sb.Block):

    """Schematic graphical inteface for DQ Cable device."""

    friendly_name = "DQ Cable"
    family = "QSS"
    label = "CBL"
    engine = DqBranch

    symbol = sb.Symbol()

    symbol.lines.append(((0, 60), (20, 60)))
    symbol.lines.append(((100, 60), (120, 60)))

    symbol.rects.append((20, 50, 80, 20, 0))

    def __init__(self, name):

        # init super:
        sb.Block.__init__(self, name, DqBranch)

        # ports:
        self.ports['positive'] = sb.Port(self, 0, (0, 60))
        self.ports['negative'] = sb.Port(self, 1, (120, 60))

        # properties:
        self.properties['Inductance (H)'] = 1.0
        self.properties['Resistance (Ohm)'] = 1.0

    def get_engine(self, nodes):

        return DqBranch(nodes, self.properties['Inductance (H)'],
                               self.properties['Resistance (Ohm)'])



class DqSourceBlock(sb.Block):

    """Schematic graphical inteface for DQ Source device."""

    friendly_name = "DQ Source"
    family = "QSS"
    label = "GEN"
    engine = DqBranch

    symbol = sb.Symbol()

    # leads:
    symbol.lines.append(((90, 60), (110, 60)))

    # circle
    symbol.circles.append((60, 60, 30))

    # sine:
    a1 = math.pi
    a2 = 0.0
    symbol.arcs.append((50, 60, 10, a1, a2, True))
    symbol.arcs.append((70, 60, 10, -a1, -a2, False))

    def __init__(self, name):

        # init super:
        sb.Block.__init__(self, name, DqBranch)

        # ports:
        self.ports['positive'] = sb.Port(self, 0, (110, 60))
        self.ports['negative'] = sb.Port(self, 1, (60, 90))

        # properties:
        self.properties['Inductance (H)'] = 1.0
        self.properties['Resistance (Ohm)'] = 1.0
        self.properties['Voltage (V)'] = 1.0

    def get_engine(self, nodes):

        return DqBranch(nodes, self.properties['Inductance (H)'],
                               self.properties['Resistance (Ohm)'],
                               self.properties['Voltage (V)'])



class DqLoadBlock(sb.Block):

    """Schematic graphical inteface for DQ Load device."""

    friendly_name = "DQ Source"
    family = "QSS"
    label = "GEN"
    engine = DqBranch

    symbol = sb.Symbol()

    # leads:
    symbol.lines.append(((90, 60), (110, 60)))

    # circle
    symbol.circles.append((60, 60, 30))

    # sine:
    a1 = math.pi
    a2 = 0.0
    symbol.arcs.append((50, 60, 10, a1, a2, True))
    symbol.arcs.append((70, 60, 10, -a1, -a2, False))

    def __init__(self, name):

        # init super:
        sb.Block.__init__(self, name, DqBranch)

        # ports:
        self.ports['positive'] = sb.Port(self, 0, (110, 60))
        self.ports['negative'] = sb.Port(self, 1, (60, 90))

        # properties:
        self.properties['Inductance (H)'] = 1.0
        self.properties['Resistance (Ohm)'] = 1.0
        self.properties['Voltage (V)'] = 1.0

    def get_engine(self, nodes):

        return DqBranch(nodes, self.properties['Inductance (H)'],
                               self.properties['Resistance (Ohm)'],
                               self.properties['Voltage (V)'])