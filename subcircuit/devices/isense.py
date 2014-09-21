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

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name, None)

        # port:
        self.ports['positive'] = sb.Port(self, 0, (60, 160))
        self.ports['negative'] = sb.Port(self, 1, (100, 160))
        self.ports['current node'] = sb.Port(self, 2, (80, 120))

        # lines:
        self.lines.append(((80, 120), (80, 150)))
        self.lines.append(((60, 160), (100, 160)))

        # plus:
        self.lines.append(((60, 133), (60, 143)))
        self.lines.append(((55, 138), (65, 138)))

        # circle
        self.circles.append((75, 150, 10, 20))


    def get_engine(self, nodes):
        self.engine = CurrentSensor(nodes)
        return self.engine
