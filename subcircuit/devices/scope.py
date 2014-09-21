"""Generic Scope Device.

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
import wx



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
        n1, n2, n3, n4, n5, nn = self.nodes
        self.port2node = {0: self.get_node_index(n1),
                          1: self.get_node_index(n2),
                          2: self.get_node_index(n3),
                          3: self.get_node_index(n4),
                          4: self.get_node_index(n5),
                          5: self.get_node_index(nn)}

    def update(self):
        pass

    def start(self, dt):
        pass

    def step(self, dt, t):
        pass

    def post_step(self, dt, t):
        v1 = self.get_across(0, 5)
        v2 = self.get_across(1, 5)
        v3 = self.get_across(2, 5)
        v4 = self.get_across(3, 5)
        v5 = self.get_across(4, 5)
        self.time.append(t)
        self.data1.append(v1)
        self.data2.append(v2)
        self.data3.append(v3)
        self.data4.append(v4)
        self.data5.append(v5)


class Scope5Block(sb.Block):
    """Schematic graphical inteface for V Scope 3ph device."""
    friendly_name = "Generic Scope (5 port)"
    family = "Meters"
    label = "Scope"
    engine = Scope5
    color1 = wx.Colour(255, 80, 80)
    color2 = wx.Colour(80, 80, 255)
    color3 = wx.Colour(80, 255, 80)
    color4 = wx.Colour(255, 200, 0)
    color5 = wx.Colour(220, 220, 220)

    def __init__(self, name):
        # init super:
        sb.Block.__init__(self, name, None, is_signal_device=True)
        self.size = (160, 120)
        self.margin = 12

        # port:
        self.ports['1'] = sb.Port(self, 0, (0, 20))
        self.ports['2'] = sb.Port(self, 1, (0, 40))
        self.ports['3'] = sb.Port(self, 2, (0, 60))
        self.ports['4'] = sb.Port(self, 3, (0, 80))
        self.ports['5'] = sb.Port(self, 4, (0, 100))
        self.ports['N'] = sb.Port(self, 5, (80, 120))

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

            all = values1 + values2 + values3 + values4 + values5

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

            for t, v1 in zip(times[::stride], values1[::stride]):
                plot_curve1.append((t * tscale + toffset, v1 * vscale + voffset))

            for t, v2 in zip(times[::stride], values2[::stride]):
                plot_curve2.append((t * tscale + toffset, v2 * vscale + voffset))

            for t, v3 in zip(times[::stride], values3[::stride]):
                plot_curve3.append((t * tscale + toffset, v3 * vscale + voffset))

            for t, v4 in zip(times[::stride], values4[::stride]):
                plot_curve4.append((t * tscale + toffset, v4 * vscale + voffset))

            for t, v5 in zip(times[::stride], values5[::stride]):
                plot_curve5.append((t * tscale + toffset, v5 * vscale + voffset))

            self.plot_curves.append((plot_curve1, Scope5Block.color1))
            self.plot_curves.append((plot_curve2, Scope5Block.color2))
            self.plot_curves.append((plot_curve3, Scope5Block.color3))
            self.plot_curves.append((plot_curve4, Scope5Block.color4))
            self.plot_curves.append((plot_curve5, Scope5Block.color5))

    def get_engine(self, nodes):
        if len(nodes) == 0:
            nodes += [0, 0, 0, 0, 0, 0]
        if len(nodes) == 1:
            nodes += [0, 0, 0, 0, 0]
        elif len(nodes) == 2:
            nodes += [0, 0, 0, 0]
        elif len(nodes) == 3:
            nodes += [0, 0, 0]
        elif len(nodes) == 4:
            nodes += [0, 0]
        elif len(nodes) == 5:
            nodes += [0]
        self.engine = Scope5(nodes)
        return self.engine

