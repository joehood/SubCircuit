"""R (resistor or semiconductor resistor) device.

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

import subcircuit.interfaces as inter
import subcircuit.sandbox as sb


class R(inter.MNADevice):
    """Engine for SPICE R (resistor or semiconductor resistor) device."""

    def __init__(self, nodes, value,
                 rmodel=None, l=None, w=None, temp=None, **parameters):

        """General form:
        RXXXXXXX N1 N2 VALUE
        Examples:
        R1 1 2 100
        RC1 12 17 1K
        N1 and N2 are the two element nodes. VALUE is the resistance (in ohms)
        and may be positive or negative but not zero.

        Semiconductor Resistors:
        General form:
        RXXXXXXX N1 N2 <VALUE> <MNAME> <L=LENGTH> <W=WIDTH> <TEMP=T>

        Examples:
        RLOAD 2 10 10K
        RMOD 3 7 RMODEL L=10u W=1u
        """
        inter.MNADevice.__init__(self, nodes, 0, **parameters)
        self.value = value
        self.rmodel = rmodel
        self.l = l
        self.w = w
        self.temp = temp

    def connect(self):
        nplus, nminus = self.nodes
        self.port2node = {0: self.get_node_index(nplus),
                          1: self.get_node_index(nminus)}

    def update(self):
        if self.value:  # if non-zero:
            g = 1.0 / self.value
        else:
            g = 1.0E12  # approximate short circuit for 0-resistance

        self.jac[0, 0] = g
        self.jac[0, 1] = -g
        self.jac[1, 0] = -g
        self.jac[1, 1] = g

    def start(self, dt):
        self.update()

    def step(self, dt, t):
        """Do nothing here. Linear and time-invariant device."""
        pass


class RBlock(sb.Block):
    """Schematic graphical inteface for R device."""
    friendly_name = "Resistor"
    family = "Elementary"
    label = "R"
    engine = R

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name)

        # ports:
        self.ports['positive'] = sb.Port(self, 0, (60, 0))
        self.ports['negative'] = sb.Port(self, 1, (60, 100))

        # properties:
        self.properties['Resistance (R)'] = 1.0

        # resistor shape:
        self.lines.append(((60, 0), (60, 20), (45, 25), (75, 35), (45, 45),
                           (75, 55), (45, 65), (75, 75), (60, 80), (60, 100)))

    def get_engine(self, nodes):
        return R(nodes, self.properties['Resistance (R)'])

