"""Current Scope Device.

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


class CurrentSensor(inter.MNADevice, inter.CurrentSensor):

    def __init__(self, nodes, **parameters):
        inter.MNADevice.__init__(self, nodes, 0, **parameters)

    def connect(self):
        nplus, nminus, current_node = self.nodes
        self.port2node = {0: self.get_node_index(nplus),
                          1: self.get_node_index(nminus),
                          2: self.get_node_index(current_node)}

    def start(self, dt):
        self.jac[0, 2] = 1.0
        self.jac[1, 2] = -1.0
        self.jac[2, 0] = 1.0
        self.jac[2, 1] = -1.0

    def get_current_node(self):
        return self.port2node[2], -1.0


class CurrentSensorBlock(sb.Block):
    """Schematic graphical inteface for IScope device."""
    friendly_name = "Current Sensor"
    family = "Meters"
    label = "I"
    engine = CurrentSensor

    symbol = sb.Symbol()

    # lines:
    symbol.lines.append(((80, 40), (80, 70)))
    symbol.lines.append(((60, 80), (100, 80)))

    # plus:
    symbol.lines.append(((60, 53), (60, 63)))
    symbol.lines.append(((55, 58), (65, 58)))

    # circle
    symbol.circles.append((75, 70, 10, 20))

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name, None)

        # port:
        self.ports['positive'] = sb.Port(self, 0, (60, 80))
        self.ports['negative'] = sb.Port(self, 1, (100, 80))
        self.ports['current node'] = sb.Port(self, 2, (80, 40))

    def get_engine(self, nodes):
        self.engine = CurrentSensor(nodes)
        return self.engine
