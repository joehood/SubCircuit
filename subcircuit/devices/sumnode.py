"""V (independant voltage source) device.

Copyright 2014 Joe Hood

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

from subcircuit.mathutils.lti import StateSpace
import subcircuit.interfaces as inter
import subcircuit.sandbox as sb
import numpy as np
import sympy
from sympy.parsing.sympy_parser import parse_expr as parse
from subcircuit.mathutils.pprint import equ2bmp


class Sum(inter.SignalDevice):

    def __init__(self, nodes, signs=None, **parameters):

        inter.SignalDevice.__init__(self, nodes, **parameters)

        if not signs:
            self.signs = [1, 1, -1]
        else:
            self.signs = signs

    def connect(self):
        if len(self.nodes) == 4:
            output, input1, input2, input3 = self.nodes
            self.port2node = {0: self.get_node_index(output),
                              1: self.get_node_index(input1),
                              2: self.get_node_index(input2),
                              3: self.get_node_index(input3)}

    def update(self):
        pass

    def start(self, dt):
        pass

    def step(self, dt, t):

        sign1, sign2, sign3 = self.signs

        in1 = self.get_port_value(1)
        in2 = self.get_port_value(2)
        in3 = self.get_port_value(3)

        output = in1 * sign1 + in2 * sign2 + in3 * sign3

        self.set_port_value(0, output)

    def post_step(self, dt, t):
        pass


class SumNode(sb.Block):

    """Schematic graphical interface for Sum device."""

    friendly_name = "Sum Node"
    family = "Signal Sources"
    label = "S"
    engine = Sum

    symbol = sb.Symbol()
    symbol.circles.append((60, 60, 20))

    symbol.add_field(u"\u03a3", (60, 60), 25, sb.Alignment.CENTER)

    symbol.add_field(u"+", (45, 35), 18, sb.Alignment.CENTER, visible=False)
    
    symbol.add_field(u"+", (30, 50), 18, sb.Alignment.CENTER, visible=False)
    
    symbol.add_field(u"+", (45, 85), 18, sb.Alignment.CENTER, visible=False)

    def __init__(self, name):

        sb.Block.__init__(self, name, None, is_signal_device=True,
                          label_visible=False)

        self.ports["output"] = sb.Port(self, 0, (80, 60),
                                       sb.PortDirection.OUT,
                                       block_edge=sb.Alignment.E)

        self.ports["input1"] = sb.Port(self, 1, (60, 40),
                                       sb.PortDirection.IN,
                                       block_edge=sb.Alignment.N)

        self.ports["input2"] = sb.Port(self, 2, (40, 60),
                                       sb.PortDirection.IN,
                                       block_edge=sb.Alignment.W)

        self.ports["input3"] = sb.Port(self, 3, (60, 80),
                                       sb.PortDirection.IN,
                                       block_edge=sb.Alignment.S)

        self.properties["Signs"] = "1 1 -1"

        self.signs = [1, 1, -1]

    def design_update(self):

        self.signs = [float(x) for x in self.properties["Signs"].split(" ")]

        sign1, sign2, sign3 = self.signs

        if self.ports["input1"].connected:
            self.fields[1].visible = True
            if sign1 == 1:
                self.fields[1].text = "+"
            elif sign1 == -1:
                self.fields[1].text = "_"
            else:
                self.fields[1].text = "?"
        else:
            self.fields[1].visible = False

        if self.ports["input2"].connected:
            self.fields[2].visible = True
            if sign2 == 1:
                self.fields[2].text = "+"
            elif sign2 == -1:
                self.fields[2].text = "_"
            else:
                self.fields[2].text = "?"
        else:
            self.fields[2].visible = False

        if self.ports["input3"].connected:
            self.fields[3].visible = True
            if sign3 == 1:
                self.fields[3].text = "+"
            elif sign3 == -1:
                self.fields[3].text = "_"
            else:
                self.fields[3].text = "?"
        else:
            self.fields[3].visible = False

    def end(self):
        pass

    def get_engine(self, nodes):

        return Sum(nodes, self.signs)
