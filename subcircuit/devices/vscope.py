"""Voltage Scope Device."""

import subcircuit.sandbox as sb
import subcircuit.interfaces as inter
import wx


class VScope(inter.SignalDevice):
    def __init__(self, nodes, **parameters):
        inter.SignalDevice.__init__(self, nodes, **parameters)
        self.time = []
        self.data = []

    def connect(self):
        npos, nneg = self.nodes
        self.port2node = {0: self.get_node_index(npos),
                          1: self.get_node_index(nneg)}

    def update(self):
        pass

    def start(self, dt):
        pass
        # tmax = self.netlist.simulator.tmax
        # n = tmax / dt
        # self.time = np.zeros(n)
        # self.data = np.zeros(n)

    def step(self, dt, t):
        pass

    def post_step(self, dt, t):
        v = self.get_across(0, 1)
        self.time.append(t)
        self.data.append(v)


class VScope3(inter.SignalDevice):
    def __init__(self, nodes, **parameters):
        inter.SignalDevice.__init__(self, nodes, **parameters)
        self.time = []
        self.data1 = []
        self.data2 = []
        self.data3 = []

    def connect(self):
        n1, n2, n3, nn = self.nodes
        self.port2node = {0: self.get_node_index(n1),
                          1: self.get_node_index(n2),
                          2: self.get_node_index(n3),
                          3: self.get_node_index(nn)}

    def update(self):
        pass

    def start(self, dt):
        pass

    def step(self, dt, t):
        pass

    def post_step(self, dt, t):
        v1 = self.get_across(0, 3)
        v2 = self.get_across(1, 3)
        v3 = self.get_across(2, 3)
        self.time.append(t)
        self.data1.append(v1)
        self.data2.append(v2)
        self.data3.append(v3)


class VScopeBlock(sb.Block):
    """Schematic graphical inteface for V Scope device."""
    friendly_name = "Voltage Scope"
    family = "Meters"
    label = "Scope"
    engine = VScope

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name, None, is_signal_device=True)
        self.size = (160, 120)
        self.margin = 12

        # port:
        self.ports['positive'] = sb.Port(self, 0, (0, 60))
        self.ports['negative'] = sb.Port(self, 1, (80, 120))

        # rects:
        (w, h), m = self.size, self.margin

        # rects:
        (w, h), m = self.size, self.margin
        self.rects.append(((0, 0, w, h, 5), (sb.DEVICE_COLOR, sb.SCOPE_BG)))
        window = m, m, w - m * 2, h - m * 2, 1
        self.rects.append((window, (sb.SCOPE_FG, sb.SCOPE_FG)))

    def end(self):
        times = self.engine.time
        values = self.engine.data

        n = len(times)

        npoints = 1000
        stride = int(n / npoints)
        stride = max(stride, 2)

        (w, h), m = self.size, self.margin

        if max(times) > 0.0:
            tscale = (w - m * 2.0) / max(times)
            toffset = m

            range_ = max(values) - min(values)

            mid = min(values) + range_ * 0.5

            vscale = 1.0
            if range_ > 0.0:
                vscale = -(h - m * 4.0) / range_

            self.margin = 12

            voffset = -(mid * vscale - m * 5)

            # path:
            plot_curve = []
            for t, v in zip(times[::stride], values[::stride]):
                plot_curve.append((t * tscale + toffset, v * vscale + voffset))

            self.plot_curves = []
            self.plot_curves.append((plot_curve, sb.SCOPE_CURVE))

    def get_engine(self, nodes):
        if len(nodes) == 1:
            nodes += [0]  # if only one connection, ground neg lead
        self.engine = VScope(nodes)
        return self.engine


class VScope3Block(sb.Block):
    """Schematic graphical inteface for V Scope 3ph device."""
    friendly_name = "Voltage Scope (3ph)"
    family = "Meters"
    label = "Scope"
    engine = VScope3

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name, None, is_signal_device=True)
        self.size = (160, 120)
        self.margin = 12

        # port:
        self.ports['A'] = sb.Port(self, 0, (0, 40))
        self.ports['B'] = sb.Port(self, 1, (0, 60))
        self.ports['C'] = sb.Port(self, 2, (0, 80))
        self.ports['N'] = sb.Port(self, 3, (80, 120))

        # rects:
        (w, h), m = self.size, self.margin

        # rects:
        (w, h), m = self.size, self.margin
        self.rects.append(((0, 0, w, h, 5), (sb.DEVICE_COLOR, sb.SCOPE_BG)))
        window = m, m, w - m * 2, h - m * 2, 1
        self.rects.append((window, (sb.SCOPE_FG, sb.SCOPE_FG)))

    def end(self):
        times = self.engine.time
        values1 = self.engine.data1
        values2 = self.engine.data2
        values3 = self.engine.data3

        n = len(times)

        npoints = 1000
        stride = int(n / npoints)
        stride = max(stride, 2)

        (w, h), m = self.size, self.margin

        if max(times) > 0.0:
            tscale = (w - m * 2.0) / max(times)
            toffset = m

            all = values1 + values2 + values3

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

            for t, v1 in zip(times[::stride], values1[::stride]):
                plot_curve1.append((t * tscale + toffset, v1 * vscale + voffset))

            for t, v2 in zip(times[::stride], values2[::stride]):
                plot_curve2.append((t * tscale + toffset, v2 * vscale + voffset))

            for t, v3 in zip(times[::stride], values3[::stride]):
                plot_curve3.append((t * tscale + toffset, v3 * vscale + voffset))

            self.plot_curves.append((plot_curve1, wx.Colour(255, 100, 100)))
            self.plot_curves.append((plot_curve2, wx.Colour(100, 255, 100)))
            self.plot_curves.append((plot_curve3, wx.Colour(100, 100, 255)))

    def get_engine(self, nodes):
        if len(nodes) == 1:
            nodes += [0, 0, 0]
        if len(nodes) == 2:
            nodes += [0, 0]
        if len(nodes) == 3:
            nodes += [0]
        self.engine = VScope3(nodes)
        return self.engine

