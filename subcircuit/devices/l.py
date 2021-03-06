"""L (inductor) device.

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

import math

import subcircuit.interfaces as inter
import subcircuit.sandbox as sb


class L(inter.MNADevice, inter.CurrentSensor):
    """SPICE Inductor Device"""

    def __init__(self, nodes, value, ic=None, res=0.0, **parameters):
        """
        General form:
        LYYYYYYY N+ N- VALUE <IC=INCOND>
        Examples:
        LLINK 42 69 1UH
        LSHUNT 23 51 10U IC=15.7MA
        N+ and N- are the positive and negative element nodes, respectively. VALUE is the
        inductance in Henries.
        The (optional) initial condition is the initial (time-zero) value of inductor
        current (in Amps) that flows from N+, through the inductor, to N-. Note that the
        initial conditions (if any) apply only if the UIC option is specified on the
        .TRAN analysis line.
        """
        self.linkable = False

        if len(nodes) == 2:
            inter.MNADevice.__init__(self, nodes, 1, **parameters)

        elif len(nodes) == 3:
            inter.MNADevice.__init__(self, nodes, 0, **parameters)
            self.linkable = True

        self.value = value
        self.ic = ic
        self.res = res

    def connect(self):
        if self.linkable:
            nplus, nminus, link = self.nodes
            self.port2node = {0: self.get_node_index(nplus),
                              1: self.get_node_index(nminus),
                              2: self.get_node_index(link)}
        else:
            nplus, nminus = self.nodes
            internal = "{0}_int".format(self.name)
            self.port2node = {0: self.get_node_index(nplus),
                              1: self.get_node_index(nminus),
                              2: self.create_internal(internal)}

    def start(self, dt):
        self.jac[0, 2] = 1.0
        self.jac[1, 2] = -1.0
        self.jac[2, 0] = 1.0
        self.jac[2, 1] = -1.0
        self.jac[2, 2] = -(self.res + self.value / dt)

    def step(self,  dt, t):
        inductor_current = self.get_across_history(2)
        self.bequiv[2] = -self.value / dt * inductor_current

    def get_current_node(self):
        return self.port2node[2], 1.0


class LBlock(sb.Block):
    """Schematic graphical inteface for L device."""
    friendly_name = "Inductor"
    family = "Elementary"
    label = "L"
    engine = L

    symbol = sb.Symbol()

    # leads:
    symbol.lines.append(((60, 0), (60, 20)))
    symbol.lines.append(((60, 80), (60, 100)))

    # coils (x, y, r, ang0, ang1, clockwise)
    ang1 = math.pi * 0.5
    ang2 = 3.0 * math.pi * 0.5
    symbol.arcs.append((60, 30, 10, ang1, ang2, True))
    symbol.arcs.append((60, 50, 10, ang1, ang2, True))
    symbol.arcs.append((60, 70, 10, ang1, ang2, True))

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name, L)

        # ports:
        self.ports['positive'] = sb.Port(self, 0, (60, 0))
        self.ports['negative'] = sb.Port(self, 1, (60, 100))

        # properties:
        self.properties['Inductance (H)'] = 0.1



    def get_engine(self, nodes):
        return L(nodes, self.properties['Inductance (H)'])



class LLinkBlock(sb.Block):
    """Schematic graphical inteface for L device."""
    friendly_name = "Inductor (Linkable)"
    family = "Elementary"
    label = "L"
    engine = L

    symbol = sb.Symbol()

    # leads:
    symbol.lines.append(((60, 0), (60, 20)))
    symbol.lines.append(((60, 80), (60, 100)))

    # coils (x, y, r, ang0, ang1, clockwise)
    ang1 = math.pi * 0.5
    ang2 = 3.0 * math.pi * 0.5
    symbol.arcs.append((60, 30, 10, ang1, ang2, False))
    symbol.arcs.append((60, 50, 10, ang1, ang2, False))
    symbol.arcs.append((60, 70, 10, ang1, ang2, False))

    # mag link bar:
    symbol.lines.append(((80, 20), (80, 80)))

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name, L)

        # ports:
        self.ports['positive'] = sb.Port(self, 0, (60, 0))
        self.ports['negative'] = sb.Port(self, 1, (60, 100))
        self.ports['link'] = sb.Port(self, 1, (80, 20))

        # properties:
        self.properties['Inductance (H)'] = 0.1

    def get_engine(self, nodes):
        return L(nodes, self.properties['Inductance (H)'])