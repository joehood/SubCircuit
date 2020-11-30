"""LIM Node device.

Copyright 2020 Joe Hood

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import math
import numpy as np

import subcircuit.interfaces as inter
import subcircuit.sandbox as sb
import subcircuit.qdl as qdl


class LimNode(qdl.Device):

    """QSS LIM Node Device"""

    def __init__(self, nodes, name, c, g=0.0, h=0.0, v0=0.0, dq=1e-4, **parameters):

        self.c = c
        self.g = g

        qdl.Device.__init__(self, name)

        self.h = qdl.SourceAtom("h", u0=h, dq=dq, units="A")

        self.voltage = qdl.StateAtom("voltage", x0=v0, coeffunc=self.aii, dq=dq, units="V")

        self.add_atoms(self.h, self.voltage)

        self.voltage.add_connection(self.h, coeffunc=self.bii)

        self.voltage.add_jacfunc(self.voltage, self.aii)

    def connect(self):

        self.port2node = {0: self.get_node_index(self.nodes[0])}

    def start(self, dt):

        pass

    @staticmethod
    def aii(self):
        return -self.g / self.c

    @staticmethod
    def bii(self):
        return 1.0 / self.c

    @staticmethod
    def aij(self):
        return -1.0 / self.c

    @staticmethod
    def aji(self):
        return 1.0 / self.c


class LimGround(qdl.Device):

    """QSS LIM Ground Device"""

    def __init__(self, nodes, name):

        qdl.Device.__init__(self, name)

        self.atom = qdl.SourceAtom(name="source", source_type=qdl.SourceType.CONSTANT,
                                   u0=0.0, units="V", dq=1.0)

        self.add_atom(self.atom)

    def connect(self):

        self.port2node = {0: self.get_node_index(self.nodes[0])}


class LimNodeBlock(sb.Block):

    """Schematic graphical inteface for LimNode device."""

    friendly_name = "Lim Node"
    family = "QSS"
    label = "N"
    engine = LimNode

    symbol = sb.Symbol()

    #source:
    symbol.circles.append((-60, 50, 30))
    symbol.lines.append(((-60, 0), (-60, 20)))
    symbol.lines.append(((-60, 80), (-60, 100)))
    symbol.lines.append(((-60, 65), (-60, 35)))
    symbol.lines.append(((-65, 45), (-60, 35), (-55, 45)))

    # resistor:
    symbol.lines.append(((0, -20), (0, 20), (-10, 25), (10, 35), (-10, 45),
                           (10, 55), (-10, 65), (10, 75), (0, 80), (0, 120)))

    # capacitor:
    symbol.lines.append(((60, 0), (60, 40)))
    symbol.lines.append(((60, 60), (60, 100)))
    symbol.lines.append(((40, 40), (80, 40)))
    symbol.lines.append(((40, 60), (80, 60)))

    # ground:
    symbol.lines.append(((45-60, 55+65), (75-60, 55+65)))
    symbol.lines.append(((52-60, 64+65), (68-60, 64+65)))
    symbol.lines.append(((58-60, 73+65), (62-60, 73+65)))

    # connections:
    symbol.lines.append(((-60, 100), (60, 100)))
    symbol.lines.append(((-60, 0), (60, 0)))

    k = 0.5
    dy = 60.0
    dx = 60.0

    lines2 = []
    for poly in symbol.lines:
        poly2 = []
        for pt in poly:
           x, y = pt[0]*k + dx, pt[1]*k
           poly2.append((x, y))
        lines2.append(poly2)
    symbol.lines = lines2

    
    circles2 = []

    for circle in symbol.circles:
        circle2 = circle[0]*k + dx, circle[0]*k + dy, circle[2]*k 
        circles2.append(circle)

    symbol.circles = circles2

    def __init__(self, name):

        # init super:
        sb.Block.__init__(self, name, LimNode)
 
        # ports:
        self.ports['positive'] = sb.Port(self, 0, (0, -20))

        # properties:
        self.properties['Capacitance (F)'] = 1.0
        self.properties['Conductance (S)'] = 1.0
        self.properties['Current (A)'] = 1.0
        self.properties['Initial Voltage (V)'] = 0.0
        self.properties['Quantization Step (V)'] = 1e-4

    def get_engine(self, nodes):

        return LimNode(nodes, self.name,
                       c=self.properties['Capacitance (F)'],
                       g=self.properties['Conductance (S)'],
                       h=self.properties['Current (A)'],
                       v0=self.properties['Initial Voltage (V)'],
                       dq=self.properties['Quantization Step (V)'])


class LimGndBlock(sb.Block):

    """Schematic graphical inteface for GRD device."""

    friendly_name = "LIM Ground"
    family = "QSS"
    label = "G"
    engine = LimGround

    symbol = sb.Symbol()

    # lead:
    symbol.lines.append(((60, 40), (60, 60)))

    # ground lines:
    symbol.lines.append(((45, 60), (75, 60)))
    symbol.lines.append(((52, 69), (68, 69)))
    symbol.lines.append(((58, 78), (62, 78)))

    def __init__(self, name):

        # init super:
        sb.Block.__init__(self, name, LimGround, is_ground=True, label_visible=False)

        # port:
        self.ports['ground'] = sb.Port(self, 0, (60, 40), is_ground=True)

    def get_engine(self, nodes):

        return LimGround(nodes, self.name)
