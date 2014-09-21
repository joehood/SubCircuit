"""Voltage Scope Device.

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

import subcircuit.sandbox as sb
import subcircuit.interfaces as inter
import subcircuit.stimuli as stim


class I(inter.MNADevice):
    """A SPICE Current source or current sensor."""

    def __init__(self, nodes, value, resistance=0.0, **parameters):

        """TODO
        """
        inter.MNADevice.__init__(self, nodes, 0, **parameters)

        self.stimulus = None
        if isinstance(value, inter.Stimulus):
            self.stimulus = value
            self.stimulus.device = self
        else:
            self.value = value

        self.resistance = resistance

    def connect(self):
        nplus, nminus = self.nodes
        self.port2node = {0: self.get_node_index(nplus),
                          1: self.get_node_index(nminus)}

    def start(self, dt):

        g = 0.0
        if self.resistance > 0.0:
            g = 1.0 / self.resistance

        self.jac[0, 0] = g
        self.jac[0, 1] = -g
        self.jac[1, 0] = -g
        self.jac[1, 1] = g

        current = 0.0
        if self.stimulus:
            current = self.stimulus.start(dt)
        elif self.value:
            current = self.value

        self.bequiv[0] = current
        self.bequiv[1] = -current

    def step(self, dt, t):
        """Step the current source.
        """
        if self.stimulus:
            current = self.stimulus.step(dt, t)
        else:
            current = self.value

        self.bequiv[0] = current
        self.bequiv[1] = -current


class IBlock(sb.Block):
    """Schematic graphical inteface for V device."""
    friendly_name = "Current Source (DC)"
    family = "Sources"
    label = "I"
    engine = I

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name, I)

        # ports:
        self.ports['positive'] = sb.Port(self, 0, (60, 0))
        self.ports['negative'] = sb.Port(self, 1, (60, 100))

        # properties:
        self.properties['Current (A)'] = 1.0

        # leads:
        self.lines.append(((60, 0), (60, 25)))
        self.lines.append(((60, 75), (60, 100)))

        # arrow:
        self.lines.append(((60, 65), (60, 35)))
        self.lines.append(((55, 45), (60, 35), (65, 45)))

        # circle
        self.circles.append((60, 50, 25))

    def get_engine(self, nodes):
        return I(nodes, self.properties['Current (A)'])