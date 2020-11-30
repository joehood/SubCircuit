"""LIM DQ Bus device.
"""

import math

import subcircuit.interfaces as inter
import subcircuit.sandbox as sb
import subcircuit.qdl as qdl


class DqNode(inter.MNADevice):

    """
                        inoded                                inodeq
                           o                                     o
                           |   | isumd                           |   | isumq  
                           |   v                                 |   v
    .----------------------+-------------------------------------+-------------.
    |                      |                                     |             |
    |           .----------+---------.                .----------+---------.   |
    |           |          |         |                |          |         |   |
    |  vd *  ^ <.       ^ _|_       ,-.      vq *  ^ <.       ^ _|_       ,-.  |
    |(g+w*C) | <. vd'*C | ___ id(t)( ^ )   (g+w*C) | <. vq'*C | ___ iq(t)( ^ ) |
    |        | <.       |  |        `-'            | <.       |  |        `-'  |
    |           |          |         |                |          |         |   |
    |           '----------+---------'                '----------+---------'   |     
    |                     _|_                                   _|_            |
    |                      -                                     -             |
    '--------------------------------------------------------------------------'
    """

    def __init__(self, nodes, c, g=0.0, id0=0.0, iq0=0.0, w=188.0, vd0=0.0,
                 vq0=0.0, source_type=qdl.SourceType.CONSTANT, id1=0.0, id2=0.0,
                 ida=0.0, freqd=0.0, phid=0.0, dutyd=0.0, td1=0.0, td2=0.0,
                 iq1=0.0, iq2=0.0, iqa=0.0, freqq=0.0, phiq=0.0, dutyq=0.0,
                 tq1=0.0, tq2=0.0, dq=None, **parameters):

        if len(nodes) == 2:
            inter.MNADevice.__init__(self, nodes, 1, **parameters)

        self.c = c
        self.g = g
        self.w = w
        self.vd0 = vd0
        self.vq0 = vq0

    def connect(self):
        self.port2node = {0: self.get_node_index(self.nodes[0])}

    def start(self, dt):
        self.jac[0, 0] = 1.0


class DqNodeBlock(sb.Block):

    """Schematic graphical inteface for LimNode device."""

    friendly_name = "DQ Bus"
    family = "QSS"
    label = "BUS"
    engine = DqNode

    symbol = sb.Symbol()

    symbol.rects.append((50, 0, 10, 120, 0))

    def __init__(self, name):

        # init super:
        sb.Block.__init__(self, name, DqNode)

        # ports:
        self.ports['positive1'] = sb.Port(self, 0, (50, 20))
        self.ports['positive2'] = sb.Port(self, 0, (50, 60))
        self.ports['positive3'] = sb.Port(self, 0, (50, 100))
        self.ports['positive4'] = sb.Port(self, 0, (60, 20))
        self.ports['positive5'] = sb.Port(self, 0, (60, 60))
        self.ports['positive6'] = sb.Port(self, 0, (60, 100))

        # properties:
        self.properties['Capacitance (F)'] = 1.0
        self.properties['Conductance (S)'] = 1.0

    def get_engine(self, nodes):

        return DqNode(nodes, self.properties['Capacitance (F)'],
                       self.properties['Conductance (S)'])
