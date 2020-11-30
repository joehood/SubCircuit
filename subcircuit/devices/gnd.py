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

    symbol = sb.Symbol()

    # lead:
    symbol.lines.append(((60, 40), (60, 55)))

    # ground lines:
    symbol.lines.append(((45, 55), (75, 55)))
    symbol.lines.append(((52, 64), (68, 64)))
    symbol.lines.append(((58, 73), (62, 73)))

    def __init__(self, name):

        # init super:
        sb.Block.__init__(self, name, None, is_ground=True, label_visible=False)

        # port:
        self.ports['ground'] = sb.Port(self, 0, (60, 40), is_ground=True)

    def get_engine(self, nodes):

        raise Exception("GND Block has no engine.")


