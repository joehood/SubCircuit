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

from subcircuit.mathutils.lti import TransferFunction
import subcircuit.interfaces as inter
import subcircuit.sandbox as sb
import numpy as np
import sympy
from sympy.parsing.sympy_parser import parse_expr as parse
from subcircuit.mathutils.pprint import equ2bmp


operator_subs = ((u"^", "**"),  # exp
                 (u"\u00D7", "*"),  # mult dot
                 (u"\u00B7", "*"))  # mult x


def sub_params(expr, parameters):
    for key in sorted(parameters, key=len, reverse=True):
        expr = expr.replace(key, str(parameters[key]))
    return expr


def sub_operators(expr):
    for char, symchar in operator_subs:
        expr = expr.replace(char, symchar)
    return expr


class TF(inter.SignalDevice):
    def __init__(self, nodes, equation=None, **parameters):
        inter.SignalDevice.__init__(self, nodes, **parameters)

        self.equation = equation
        if not self.equation:
            self.equation = "1 / (s + 1)"

        self.tf = None
        self.tf = TransferFunction(self.equation.lower())

    def connect(self):
        if len(self.nodes) == 2:
            input, output = self.nodes
            self.port2node = {0: self.get_node_index(input),
                              1: self.get_node_index(output)}

    def update(self):
        pass

    def start(self, dt):
        self.tf.reset(dt)

    def step(self, dt, t):
        input = self.get_port_value(0)
        output = self.tf.step(input, dt, t)[0][0]
        self.set_port_value(1, output)

    def post_step(self, dt, t):
        pass


class TFBlock(sb.Block):
    """Schematic graphical interface for State Space device."""
    friendly_name = "Transfer Function"
    family = "LTI Blocks"
    label = "TF"
    engine = TF

    symbol = sb.Symbol()
    # rects:
    main_rect = symbol.add_rrect(0, 0, 80, 60, corners_only=True)

    def __init__(self, name):
        sb.Block.__init__(self, name, None, is_signal_device=True)

        self.ports["input"] = sb.Port(self, 0, (0, 30), sb.PortDirection.IN,
                                      block_edge=sb.Alignment.W,
                                      anchored_rect=TFBlock.main_rect,
                                      anchored_align=sb.Alignment.W)

        self.ports["output"] = sb.Port(self, 1, (80, 30),
                                       sb.PortDirection.OUT,
                                       block_edge=sb.Alignment.E,
                                       anchored_rect=TFBlock.main_rect,
                                       anchored_align=sb.Alignment.E)

        self.equation = self.add_equation("1 / (s + 1)", (60, 60), 16,
                                          sb.Alignment.CENTER,
                                          TFBlock.main_rect,
                                          sb.Alignment.CENTER)

        self.properties["H(s)"] = "omega_0 / (s + omega_0)"
        self.properties["Parameters"] = "omega_0"
        self.properties["Parameter Values"] = "100.0"
        self.properties["Sympy Expression"] = ""
        self.bmp = None
        self.equation = None
        self.design_update()

        # debug:
        tf = self.get_engine((0, 1))

    def design_update(self):
        self.equation = self.properties["H(s)"]
        self.bmp = equ2bmp(self.equation)

    def end(self):
        pass

    def get_engine(self, nodes):
        equstr = self.properties["H(s)"]
        keys = self.properties["Parameters"].split(" ")
        values = self.properties["Parameter Values"].split(" ")

        parameters = {}

        for key, value in zip(keys, values):
            try:
                parameters[key] = float(value)
            except:
                pass

        self.parameters = parameters

        equstr = sub_params(equstr, parameters)
        equstr = sub_operators(equstr)

        self.properties["Sympy Expression"] = equstr

        return TF(nodes, equstr, **parameters)
