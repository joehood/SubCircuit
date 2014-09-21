"""E (Voltage controlled voltage source) Device.

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


class E(inter.MNADevice, inter.CurrentSensor):
    """A SPICE E (VCVS) device."""

    def __init__(self, nodes, value=1.0, limit=None, **parameters):

        """Create a new SPICE E (VCVS) device.

        :param name: Name of device. Must be unique within the subcircuit
        :param nodes: node connections sequence
        :param value: Either fixed value or transfer function table
        Examples:
        value=10.0  # fixed value
        value=Table((-1, 0), (0, 0), (0.0001, 1))  # lookup table
        TODO: add stimulus option.
        :param kwargs: Additional keyword arguments
        :return: New E instance

        General form:

            EXXXXXXX N+ N- NC+ NC- VALUE

        Examples:

            E1 2 3 14 1 2.0
        N+ is the positive node, and N- is the negative node. NC+ and NC- are
        the positive and negative controlling nodes, respectively. VALUE is the
        voltage gain.

        """
        inter.MNADevice.__init__(self, nodes, 1, **parameters)

        self.gain = None
        self.table = None

        if isinstance(value, float) or isinstance(value, int):
            self.gain = float(value)

        elif isinstance(value, inter.Table):
            self.table = value

        self.subckt = None
        self.limit = limit

    def connect(self):
        ncp, ncm, np, nm = self.nodes
        self.port2node = {0: self.get_node_index(ncp),
                          1: self.get_node_index(ncm),
                          2: self.get_node_index(np),
                          3: self.get_node_index(nm),
                          4: self.create_internal("{0}_int".format(self.name))}

    def start(self, dt):
        """Define the initial VCVS jacobian stamp."""

        if self.gain:
            k = self.gain
        else:
            k = 0.0

        self.jac[2, 4] = -1.0
        self.jac[3, 4] = 1.0
        self.jac[4, 0] = k
        self.jac[4, 2] = -1.0
        self.jac[4, 3] = 1.0
        self.jac[4, 1] = -k

    def step(self, dt, t):
        """TODO Doc"""

        if self.table:
            vc = self.get_across(2, 3)
            k = self.table.output(vc)  # get gain for this control voltage

            if self.limit and not vc == 0.0:
                if vc * k > self.limit:
                    k = self.limit / vc
                if vc * k < -self.limit:
                    k = -self.limit / vc

            self.jac[4, 0] = k
            self.jac[4, 1] = -k

    def get_current_node(self):
        """Return the current node."""
        return self.nodes[4], 1.0


class EBlock(sb.Block):
    """Schematic graphical inteface for E device."""
    friendly_name = "Voltage Controlled Voltage Source"
    family = "Dependant Sources"
    label = "E"
    engine = E

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name)

        # ports:
        self.ports['control positive'] = sb.Port(self, 0, (20, 40))
        self.ports['control negative'] = sb.Port(self, 1, (20, 60))
        self.ports['positive'] = sb.Port(self, 2, (60, 0))
        self.ports['negative'] = sb.Port(self, 3, (60, 100))

        # properties:
        self.properties['Gain value or (time, value) pairs'] = 1.0

        # leads:
        self.lines.append(((60, 0), (60, 25)))
        self.lines.append(((60, 75), (60, 100)))

        self.lines.append(((20, 40), (45, 40)))
        self.lines.append(((20, 60), (45, 60)))

        # plus:
        self.lines.append(((60, 33), (60, 43)))
        self.lines.append(((55, 38), (65, 38)))

        # diamond:
        self.lines.append(((60, 25), (85, 50), (60, 75), (35, 50),
                           (60, 25)))


    def get_engine(self, nodes):
        return E(nodes, self.properties['Gain value or (time, value) pairs'])

