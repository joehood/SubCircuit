"""Generic Scope Device.
"""

import wx

import subcircuit.sandbox as sb
import subcircuit.interfaces as inter


class Scope(inter.SignalDevice):

    def __init__(self, nodes, **parameters):

        inter.SignalDevice.__init__(self, nodes, **parameters)
        self.time = []
        self.data = []

    def connect(self):

        n1 = self.nodes[0]
        self.port2node = {0: self.get_node_index(n1)}

    def update(self):

        pass

    def start(self, dt):

        pass

    def step(self, dt, t):

        pass

    def post_step(self, dt, t):

        self.time.append(t)
        self.data.append(self.get_port_value(0))


class Scope5(inter.SignalDevice):

    def __init__(self, nodes, **parameters):

        inter.SignalDevice.__init__(self, nodes, **parameters)

        self.time = []
        self.data1 = []
        self.data2 = []
        self.data3 = []
        self.data4 = []
        self.data5 = []

    def connect(self):

        n1, n2, n3, n4, n5 = self.nodes

        self.port2node = {0: self.get_node_index(n1),
                          1: self.get_node_index(n2),
                          2: self.get_node_index(n3),
                          3: self.get_node_index(n4),
                          4: self.get_node_index(n5)}

    def update(self):

        pass

    def start(self, dt):

        pass

    def step(self, dt, t):

        pass

    def post_step(self, dt, t):

        self.time.append(t)

        self.data1.append(self.get_port_value(0))
        self.data2.append(self.get_port_value(1))
        self.data3.append(self.get_port_value(2))
        self.data4.append(self.get_port_value(3))
        self.data5.append(self.get_port_value(4))


class Scope5Block(sb.Block):

    """Schematic graphical inteface for V Scope 3ph device."""

    friendly_name = "Generic Scope (5 port)"
    family = "Meters"
    label = "Scope"
    engine = Scope5

    color1 = wx.Colour(255, 80, 80)
    color2 = wx.Colour(120, 120, 255)
    color3 = wx.Colour(80, 255, 80)
    color4 = wx.Colour(255, 200, 0)
    color5 = wx.Colour(220, 220, 220)

    size = (162, 122)

    symbol = sb.Symbol()

    # rects:
    symbol.rects.append((0, 0, 160, 120, 5))
    symbol.rects.append((12, 12, 136, 96, 1))

    def __init__(self, name):

        sb.Block.__init__(self, name, None, is_signal_device=True)

        self.size = (160, 120)
        self.margin = 12

        # ports:
        self.ports['input1'] = sb.Port(self, 0, (0, 20),
                                       sb.PortDirection.IN, sb.Alignment.W)

        self.ports['input2'] = sb.Port(self, 1, (0, 40),
                                       sb.PortDirection.IN, sb.Alignment.W)

        self.ports['input3'] = sb.Port(self, 2, (0, 60),
                                       sb.PortDirection.IN, sb.Alignment.W)

        self.ports['input4'] = sb.Port(self, 3, (0, 80),
                                       sb.PortDirection.IN, sb.Alignment.W)

        self.ports['input5'] = sb.Port(self, 4, (0, 100),
                                       sb.PortDirection.IN, sb.Alignment.W)

        # rects:
        (w, h), m = self.size, self.margin

        # rects:
        (w, h), m = self.size, self.margin
        self.rects.append(((0, 0, w, h, 5), (sb.DEVICE_COLOR, sb.SCOPE_BG)))
        window = m + 4, m, w - m * 2 - 4, h - m * 2, 1
        self.rects.append((window, (sb.SCOPE_FG, sb.SCOPE_FG)))

        self.rects.append(((5, 17, 6, 6, 3), (None, Scope5Block.color1)))
        self.rects.append(((5, 37, 6, 6, 3), (None, Scope5Block.color2)))
        self.rects.append(((5, 57, 6, 6, 3), (None, Scope5Block.color3)))
        self.rects.append(((5, 77, 6, 6, 3), (None, Scope5Block.color4)))
        self.rects.append(((5, 97, 6, 6, 3), (None, Scope5Block.color5)))

    def end(self):

        w, h = self.size
        self.rects.append((0, 0, w, h, 5))

        times = self.engine.time
        values1 = self.engine.data1
        values2 = self.engine.data2
        values3 = self.engine.data3
        values4 = self.engine.data4
        values5 = self.engine.data5

        n = len(times)

        npoints = 1000
        stride = int(n / npoints)
        stride = max(stride, 2)

        (w, h), m = self.size, self.margin

        if max(times) > 0.0:
            tscale = (w - m * 2.0 - 4) / max(times)
            toffset = m + 4

            include1 = not (max(values1) == min(values1) == 0)
            include2 = not (max(values2) == min(values2) == 0)
            include3 = not (max(values3) == min(values3) == 0)
            include4 = not (max(values4) == min(values4) == 0)
            include5 = not (max(values5) == min(values5) == 0)

            all = []

            if include1:
                all += values1

            if include2:
                all += values2

            if include3:
                all += values3

            if include4:
                all += values4

            if include5:
                all += values5

            if not all:
                all.append(0)

            range_ = max(all) - min(all)

            mid = min(all) + range_ * 0.5

            vscale = 1.0
            if range_ > 0.0:
                vscale = -(h - m * 4.0) / range_

            self.margin = 12

            voffset = -(mid * vscale - m * 5)

            self.plot_curves = []

            # path:
            plot_curve1 = []
            plot_curve2 = []
            plot_curve3 = []
            plot_curve4 = []
            plot_curve5 = []

            if include1:
                for t, v1 in zip(times[::stride], values1[::stride]):
                    plot_curve1.append((t * tscale + toffset,
                                        v1 * vscale + voffset))
                self.plot_curves.append((plot_curve1, Scope5Block.color1))

            if include2:
                for t, v2 in zip(times[::stride], values2[::stride]):
                    plot_curve2.append((t * tscale + toffset,
                                        v2 * vscale + voffset))
                self.plot_curves.append((plot_curve2, Scope5Block.color2))

            if include3:
                for t, v3 in zip(times[::stride], values3[::stride]):
                    plot_curve3.append((t * tscale + toffset,
                                        v3 * vscale + voffset))
                self.plot_curves.append((plot_curve3, Scope5Block.color3))

            if include4:
                for t, v4 in zip(times[::stride], values4[::stride]):
                    plot_curve4.append((t * tscale + toffset,
                                        v4 * vscale + voffset))
                self.plot_curves.append((plot_curve4, Scope5Block.color4))

            if include5:
                for t, v5 in zip(times[::stride], values5[::stride]):
                    plot_curve5.append((t * tscale + toffset,
                                        v5 * vscale + voffset))
                self.plot_curves.append((plot_curve5, Scope5Block.color5))

    def get_engine(self, nodes):

        if len(nodes) == 0:
            nodes += [0, 0, 0, 0, 0]
        if len(nodes) == 1:
            nodes += [0, 0, 0, 0]
        elif len(nodes) == 2:
            nodes += [0, 0, 0]
        elif len(nodes) == 3:
            nodes += [0, 0]
        elif len(nodes) == 4:
            nodes += [0]
        self.engine = Scope5(nodes)
        return self.engine


class ScopeBlock(sb.Block):

    """Schematic graphical interface for Scope device."""

    friendly_name = "Generic Scope"
    family = "Meters"
    label = "Scope"
    engine = Scope
    color = wx.Colour(255, 80, 80)

    size = (162, 122)

    symbol = sb.Symbol()

    # rects:
    symbol.rects.append((0, 0, 160, 120, 5))
    symbol.rects.append((12, 12, 136, 96, 1))

    def __init__(self, name):

        # init super:
        sb.Block.__init__(self, name, None, is_signal_device=True)
        self.size = (160, 120)
        self.margin = 12

        # port:
        self.ports['input'] = sb.Port(self, 0, (0, 60),
                                      sb.PortDirection.IN, sb.Alignment.W)

        # rects:
        (w, h), m = self.size, self.margin

        # rects:
        (w, h), m = self.size, self.margin
        self.rects.append(((0, 0, w, h, 5), (sb.DEVICE_COLOR, sb.SCOPE_BG)))
        window = m + 4, m, w - m * 2 - 4, h - m * 2, 1
        self.rects.append((window, (sb.SCOPE_FG, sb.SCOPE_FG)))

    def end(self):

        w, h = self.size
        self.rects.append((0, 0, w, h, 5))

        times = self.engine.time
        values = self.engine.data

        n = len(times)

        npoints = 1000
        stride = int(n / npoints)
        stride = max(stride, 2)

        (w, h), m = self.size, self.margin

        if max(times) > 0.0:

            tscale = (w - m * 2.0 - 4) / max(times)
            toffset = m + 4

            range_ = max(values) - min(values)

            mid = min(values) + range_ * 0.5

            scale = 1.0
            if range_ > 0.0:
                scale = -(h - m * 4.0) / range_

            self.margin = 12

            offset = -(mid * scale - m * 5)

            self.plot_curves = []

            # path:
            plot_curve = []

            for t, value in zip(times[::stride], values[::stride]):
                plot_curve.append((t * tscale + toffset, value * scale + offset))

            self.plot_curves.append((plot_curve, ScopeBlock.color))

    def get_engine(self, nodes):

        self.engine = Scope(nodes)
        return self.engine