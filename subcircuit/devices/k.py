"""K (mutual inductance) Device.

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


class K(inter.MNADevice):
    def __init__(self, l1name, l2name, value, **parameters):
        """
        Coupled (Mutual) Inductors

        General form:
        KXXXXXXX LYYYYYYY LZZZZZZZ VALUE
        Examples:
        K43 LAA LBB 0.999
        KXFRMR L1 L2 0.87
        LYYYYYYY and LZZZZZZZ are the names of the two coupled inductors, and VALUE is
        the coefficient of coupling, K, which must be greater than 0 and less than or
        equal to 1. Using the 'dot' convention, place a 'dot' on the first node of each
        inductor.
        """
        inter.MNADevice.__init__(self, [0, 0], 0, **parameters)
        self.value = value
        self.l1name = l1name
        self.l2name = l2name
        self.L1 = None
        self.L2 = None
        self.mutual = None

    def connect(self):
        inductor1 = self.netlist.devices[self.l1name]
        inductor2 = self.netlist.devices[self.l2name]
        self.L1 = inductor1.value
        self.L2 = inductor2.value
        self.mutual = self.value * math.sqrt(self.L1 * self.L2)
        node1, k = inductor1.get_current_node()
        node2, k = inductor2.get_current_node()
        self.port2node = {0: node1,
                          1: node2}

    def start(self, dt):
        self.jac[0, 1] = -self.mutual / dt
        self.jac[1, 0] = -self.mutual / dt

    def step(self,  dt, t):
        current1 = self.get_across_history(0)
        current2 = self.get_across_history(1)
        self.bequiv[0] = self.mutual / dt * current2
        self.bequiv[1] = self.mutual / dt * current1


class Mut(inter.MNADevice):
    def __init__(self, nodes, value, **parameters):
        """
        Coupled (Mutual) Inductors

        General form:
        KXXXXXXX LYYYYYYY LZZZZZZZ VALUE
        Examples:
        K43 LAA LBB 0.999
        KXFRMR L1 L2 0.87
        LYYYYYYY and LZZZZZZZ are the names of the two coupled inductors, and VALUE is
        the coefficient of coupling, K, which must be greater than 0 and less than or
        equal to 1. Using the 'dot' convention, place a 'dot' on the first node of each
        inductor.
        """
        inter.MNADevice.__init__(self, nodes, 0, **parameters)
        self.mutual = value

    def connect(self):
        npos, nneg = self.nodes
        self.port2node = {0: self.get_node_index(npos),
                          1: self.get_node_index(nneg)}

    def start(self, dt):
        self.jac[0, 1] = -self.mutual / dt
        self.jac[1, 0] = -self.mutual / dt

    def step(self,  dt, t):
        current1 = self.get_across_history(0)
        current2 = self.get_across_history(1)
        self.bequiv[0] = self.mutual / dt * current2
        self.bequiv[1] = self.mutual / dt * current1


class MutBlock(sb.Block):
    """Schematic graphical inteface for R device."""
    friendly_name = "Mutual Inductance (Linkable)"
    family = "Elementary"
    label = "MUT"
    engine = Mut

    symbol = sb.Symbol()

    symbol.lines.append(((60, 20), (60, 35)))
    symbol.lines.append(((60, 65), (60, 80)))
    symbol.rects.append((45, 35, 30, 30, 2))

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name)

        # ports:
        self.ports['inductor link 1'] = sb.Port(self, 0, (60, 20))
        self.ports['inductor link 2'] = sb.Port(self, 1, (60, 80))

        # properties:
        self.properties['Mutual Inductance'] = 0.01

    def get_engine(self, nodes):
        return Mut(nodes, self.properties['Mutual Inductance'])
