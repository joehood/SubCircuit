"""GND (Ground) device.

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


class GndBlock(sb.Block):
    """Schematic graphical inteface for GRD device."""
    friendly_name = "Ground"
    family = "Elementary"
    label = "G"
    engine = None

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name, None, is_ground=True)

        # port:
        self.ports['ground'] = sb.Port(self, 0, (60, 0), is_ground=True)

        # lead:
        self.lines.append(((60, 0), (60, 15)))

        # ground lines:
        self.lines.append(((45, 15), (75, 15)))
        self.lines.append(((52, 24), (68, 24)))
        self.lines.append(((58, 33), (62, 33)))

    def get_engine(self, nodes):
        raise Exception("GND Block has no engine.")


