"""LIM Branch device.
"""

import math

import subcircuit.interfaces as inter
import subcircuit.sandbox as sb
import subcircuit.qdl as qdl


class LimBranch(qdl.Device):

    """QSS LIM Branch Device"""

    def __init__(self, nodes, name, l, r=0.0, e=0.0, i0=0.0, dq=1e-4, **parameters):

        self.l = l
        self.r = r

        qdl.Device.__init__(self, name)

        self.e = qdl.SourceAtom("e", u0=e, dq=dq, units="V")

        self.current = qdl.StateAtom("current", x0=i0, coeffunc=self.aii, dq=dq, units="A")

        self.add_atoms(self.e, self.current)

        self.current.add_connection(self.e, coeffunc=self.bii)

        self.current.add_jacfunc(self.current, self.aii)

    def connect(self):

        inode, jnode = self.nodes
        self.port2node = {0: self.get_node_index(self.nodes[0]),
                          1: self.get_node_index(jnode)}

    def start(self, dt):

        pass

    @staticmethod
    def aii(self):
        return -self.r / self.l

    @staticmethod
    def bii(self):
        return 1.0 / self.l

    @staticmethod
    def aij(self):
        return 1.0 / self.l

    @staticmethod
    def aji(self):
        return -1.0 / self.l


class LimBranchBlock(sb.Block):

    """Schematic graphical inteface for L device."""

    friendly_name = "Lim Branch"
    family = "QSS"
    label = "B"
    engine = LimBranch

    symbol = sb.Symbol()

    symbol.lines.append(((-130, 0), (-110, 0)))
    symbol.lines.append(((-50, 0), (-30, 0)))
    symbol.lines.append(((30, 0), (50, 0)))
    symbol.lines.append(((110, 0), (130, 0)))

    # source:
    symbol.circles.append((-80, 0, 30))
    symbol.lines.append(((-97, 5), (-97, -5)))
    symbol.lines.append(((-63, 5), (-63, -5)))
    symbol.lines.append(((-68, 0), (-58, 0)))

    # resitor
    symbol.lines.append(((30, 0), (25, -10), (15, 10), (5, -10),
                       (-5, 10), (-15, -10), (-25, 10), (-30, 0)))

    # coils (x, y, r, ang0, ang1, clockwise)
    symbol.arcs.append((60, 0, 10, math.pi, 0.0, True))
    symbol.arcs.append((80, 0, 10, math.pi, 0.0, True))
    symbol.arcs.append((100, 0, 10, math.pi, 0.0, True))

    def __init__(self, name):

        # init super:
        sb.Block.__init__(self, name, LimBranch)

        # ports:
        self.ports['positive'] = sb.Port(self, 0, (-130, 0))
        self.ports['negative'] = sb.Port(self, 1, (130, 0))

        # properties:
        self.properties['Inductance (H)'] = 1.0
        self.properties['Resistance (Ohm)'] = 1.0
        self.properties['Voltage (V)'] = 1.0
        self.properties['Initial Current (A)'] = 0.0
        self.properties['Quantization Step (V)'] = 1e-4

    def get_engine(self, nodes):

        return LimBranch(nodes, self.name,
                         self.properties['Inductance (H)'],
                         self.properties['Resistance (Ohm)'],
                         self.properties['Voltage (V)'],
                         self.properties['Initial Current (A)'],
                         self.properties['Quantization Step (V)'])
