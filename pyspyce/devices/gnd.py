"""GND (Ground) device."""


import pyspyce.sandbox as sb


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


