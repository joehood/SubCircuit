from __future__ import print_function, division
import pickle
import os
from collections import OrderedDict as ODict
import math

import wx

from pyspyce import *
from interfaces import *
import gui


# region Constants

# BG_COLOR = wx.Colour(40, 120, 40)
# GRID_COLOR = wx.Colour(60, 140, 60)
# DEVICE_COLOR = wx.Colour(200, 200, 200)
# SELECT_COLOR = wx.Colour(255, 255, 255)
# HOVER_COLOR = wx.Colour(255, 255, 255)

# BG_COLOR = wx.Colour(0, 0, 0)
# GRID_COLOR = wx.Colour(30, 30, 30)
# DEVICE_COLOR = wx.Colour(130, 130, 130)
# SELECT_COLOR = wx.Colour(255, 255, 255)
# HOVER_COLOR = wx.Colour(255, 255, 255)

BG_COLOR = wx.Colour(230, 255, 230)
GRID_COLOR = wx.Colour(200, 230, 200)
DEVICE_COLOR = wx.Colour(0, 0, 0)
SELECT_COLOR = wx.Colour(0, 0, 0)
HOVER_COLOR = wx.Colour(0, 0, 0)
GHOST_COLOR = wx.Colour(220, 220, 220)
                        
LINE_WIDTH = 1
SELECT_WIDTH = 3
HOVER_WIDTH = 2
GRID_SIZE = 20
GRID_WIDTH = 1
SHOW_CROSSHAIR = False
MOVE_DELTA = GRID_SIZE
DEF_DEVICE = "R"
FONT_SIZE = 14
ORTHO_CONNECTORS = False
CONNECTOR_HIT_MARGIN = 10
PORT_HIT_MARGIN = 10
PORT_RADIUS = 3
SNAP_TO_GRID = True

# endregion


# region Notes
"""

State:

start
  |
  v
DISARMED
  |
  v
after init
  |
  v
STANDBY

CONNECT

ADD_DEVICE




"""
# endregion


class Mode(object):
    DISARMED = 0
    STANDBY = 1
    CONNECT = 3
    SELECTION = 4
    MOVE = 5
    EDIT = 6
    ADD_DEVICE = 7


class Orientation:
    NONE = 0
    VERTICAL = 1
    HORIZONTAL = 2


class SchematicObject(object):
    zorder = 0
    def __init__(self):
        self.position = 0, 0
        self.rotation = 0
        self.hor_flip = False
        self.ver_flip = False
        self.scale = 1.0
        self.selected = False
        self.center = (0, 0)
        self.hover = False
        self.bounding_rects = [(0, 0, 0, 0)]
        self.zorder = SchematicObject.zorder
        SchematicObject.zorder += 1

    def translate(self, delta):
        x, y = self.position
        dx, dy = delta
        self.position = x + dx, y + dy
        if self.bounding_rects:
            for i, (x, y, w, h) in enumerate(self.bounding_rects):
                self.bounding_rects[i] = (x + dx, y + dx, w, h)
        x, y = self.center
        self.center = x + dx, y + dy

    def rotate(self, angle):
        self.rotation += angle

    def hittest(self, point):
        x, y = point
        hit = False
        for rect in self.bounding_rects:
            x1, y1, w, h = rect
            x2 = x1 + w
            y2 = y1 + h
            if x1 < x < x2 and y1 < y < y2:
                hit = True
                break
        return hit


class ConnectionPoint(SchematicObject):
    def __init__(self, connector):
        SchematicObject.__init__(self)
        self.connectors = []
        if connector:
            self.add_connector(connector)
        self.radius = PORT_RADIUS
        self.hit_margin = PORT_HIT_MARGIN
        self.connected = False

    def add_connector(self, connector):
        if connector not in self.connectors:
            self.connectors.append(connector)
    def __getitem__(self, key):
        if isinstance(self, KneePoint):
            return self.position[key]
        else:
            return self.center[key]


class Port(ConnectionPoint):
    def __init__(self, block, index, position, is_ground=False):
        ConnectionPoint.__init__(self, None)
        self.index = index
        self.node = None
        self.position = position
        self.block = block
        self.is_ground = is_ground

    def translate(self, delta):
        pass

    def __str__(self):
        return "{0}_{1}".format(self.block, self.index)

    def __repr__(self):
        return str(self)


class KneePoint(ConnectionPoint):
    def __init__(self, connector, position):
        ConnectionPoint.__init__(self, connector)
        self.position = position
        self.segments = None
        self.center = position


class Segment(SchematicObject):
    def __init__(self, connector, connection1, connection2):
        SchematicObject.__init__(self)
        self.connector = connector
        self.connection1 = connection1
        self.connection2 = connection2
        self.orientation = Orientation.NONE
        self.closest_hit_point = None
        self.ghost_knee = None

    def __getitem__(self, key):
        connections = self.connection1, self.connection2
        return connections[key]

    def hittest(self, point):
        pt1, pt2 = self
        if pt1 and pt2:
            pt, dis = distance((pt1, pt2), point)
            self.closest_hit_point = pt
            if dis <= CONNECTOR_HIT_MARGIN:
                return True
            else:
                return False
        else:
            return False


class Connector(SchematicObject):
    def __init__(self, connection):
        SchematicObject.__init__(self)
        self.start = connection.center
        self.end = self.start
        self.partial = True
        self.knees = []
        self.ports = []
        self.end_connection_point = None
        self.start_connection_point = connection
        self.segments = []
        self.active_connection = connection
        connection.add_connector(self)

    def add_port(self, port):
        if not port in self.ports:
            self.ports.append(port)
            port.add_connector(self)
            port.connected = True

    def add_knee(self, knee):
        if not knee in self.knees:
            self.knees.append(knee)
            knee.add_connector(self)
            knee.connected = True

    def get_connectoin_points(self):
        return self.knees + self.ports

    def add_segment(self, connection):
        segment = Segment(self, self.active_connection, connection)
        self.segments.append(segment)
        if isinstance(connection, KneePoint):
            self.add_knee(connection)
        elif isinstance(connection, Port):
            self.add_port(connection)
        connection.add_connector(self)
        self.active_connection = connection

    def split_segment(self, segment, connection):
        if segment in self.segments:
            connection1 = segment.connection1
            segment2 = Segment(self, connection1, connection)
            segment.connection1 = connection
            i = self.segments.index(segment)
            self.segments.insert(i, segment2)
            self.add_knee(connection)
            connection.add_connector(self)

    def remove_knee(self, knee):
        for i, segment in enumerate(self.segments):
            if segment.connection2 is knee:
                segment.connection2 = self.segments[i+1].connection2
                self.segments.remove(self.segments[i+1])
                self.knees.remove(knee)
                break

    def get_last_point(self):
        if self.segments:
            (x1, y1), (x2, y2) = self.segments[-1]
            return (x2, y2)
        else:
            return self.start

    def translate(self, delta):
        x1, y1 = self.start
        x2, y2 = self.end
        dx, dy = delta
        self.start = x1 + dx, y1 + dy
        self.end = x2 + dx, y2 + dy
        for knee in self.knees:
            knee.translate(delta)

    def __str__(self):
        s = "("
        for port in self.ports:
            s += str(port) + "-"
        return s.rstrip("-") + ")"

    def __repr__(self):
        return str(self)


class BlockLabel(SchematicObject):
    def __init__(self, name, text, position):
        SchematicObject.__init__(self)
        self.name = name
        self.position = position
        self.properties = dict(text=text)

    def get_text(self):
        return self.properties["text"]


class Block(SchematicObject):
    def __init__(self, name, engine=None, is_ground=False,
                 is_signal_device=True):
        SchematicObject.__init__(self)
        self.name = name
        self.is_circuit_element = is_signal_device
        self.is_ghost = False
        self.is_ground = is_ground
        self.engine = engine

        self.ports = ODict()
        self.properties = ODict()
        self.outputs = ODict()
        self.lines = []
        self.plot_curves = []
        self.rects = []
        self.circles = []
        self.arcs = []
        self.fields = ODict()

        self.nominal_size = (100, 100)

        label = BlockLabel('name', name, (-20, 0))
        self.fields['name'] = label

    def get_engine(self, nodes):
        raise NotImplementedError()

    def end(self):
        pass

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)


class RBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, R)

        # ports:
        self.ports['positive'] = Port(self, 0, (60, 0))
        self.ports['negative'] = Port(self, 1, (60, 100))

        # properties:
        self.properties['Resistance (R)'] = 1.0

        # resistor shape:
        self.lines.append(((60, 0), (60, 20), (45, 25), (75, 35), (45, 45),
                           (75, 55), (45, 65), (75, 75), (60, 80), (60, 100)))

    def get_engine(self, nodes):
        return R(nodes, self.properties['Resistance (R)'])


class CBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, C)

        # ports:
        self.ports['positive'] = Port(self, 0, (60, 0))
        self.ports['negative'] = Port(self, 1, (60, 100))

        # properties:
        self.properties['Capacitance (F)'] = 0.1

        # leads:
        self.lines.append(((60, 0), (60, 40)))
        self.lines.append(((60, 60), (60, 100)))

        # plates:
        self.lines.append(((40, 40), (80, 40)))
        self.lines.append(((40, 60), (80, 60)))

    def get_engine(self, nodes):
        return C(nodes, self.properties['Capacitance (F)'])


class LBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, L)

        # ports:
        self.ports['positive'] = Port(self, 0, (60, 0))
        self.ports['negative'] = Port(self, 1, (60, 100))

        # properties:
        self.properties['Inductance (H)'] = 0.1

        # leads:
        self.lines.append(((60, 0), (60, 20)))
        self.lines.append(((60, 80), (60, 100)))

        # coils (x, y, r, ang0, ang1, clockwise)
        ang1 = -math.pi * 0.5
        ang2 = math.pi * 0.5
        self.arcs.append((60, 30, 10, ang1, ang2, True))
        self.arcs.append((60, 50, 10, ang1, ang2, True))
        self.arcs.append((60, 70, 10, ang1, ang2, True))

    def get_engine(self, nodes):
        return L(nodes, self.properties['Inductance (H)'])


class VBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, V)

        # ports:
        self.ports['positive'] = Port(self, 0, (60, 0))
        self.ports['negative'] = Port(self, 1, (60, 100))

        # properties:
        self.properties['Voltage (V)'] = 1.0

        # leads:
        self.lines.append(((60, 0), (60, 25)))
        self.lines.append(((60, 75), (60, 100)))

        # plus:
        self.lines.append(((60, 33), (60, 43)))
        self.lines.append(((55, 38), (65, 38)))

        # circle
        self.circles.append((60, 50, 25))

    def get_engine(self, nodes):
        return V(nodes, self.properties['Voltage (V)'])


class VSinBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, V)

        # ports:
        self.ports['positive'] = Port(self, 0, (60, 0))
        self.ports['negative'] = Port(self, 1, (60, 100))

        # properties:
        self.properties['Voltage Offset (V)'] = 0.0
        self.properties['Voltage Amplitude (V)'] = 1.0
        self.properties['Frequency (Hz)'] = 60.0
        self.properties['Delay (s)'] = 0.0
        self.properties['Damping factor (1/s)'] = 0.0
        self.properties['Phase (rad)'] = 0.0

        # leads:
        self.lines.append(((60, 0), (60, 25)))
        self.lines.append(((60, 75), (60, 100)))

        # plus:
        self.lines.append(((60, 33), (60, 43)))
        self.lines.append(((55, 38), (65, 38)))

        # circle
        self.circles.append((60, 50, 25))

        # sine:
        a1 = math.pi * 1.0
        a2 = math.pi * 0.0
        self.arcs.append((53, 58, 7, a1, a2, True))
        self.arcs.append((67, 58, 7, -a1, -a2, False))

    def get_engine(self, nodes):
        vo = self.properties['Voltage Offset (V)']
        va = self.properties['Voltage Amplitude (V)']
        freq = self.properties['Frequency (Hz)']
        td = self.properties['Delay (s)']
        theta = self.properties['Damping factor (1/s)']
        phi = self.properties['Phase (rad)']

        sine = Sin(vo, va, freq, td, theta, phi)
        return V(nodes, sine)


class DBlock(Block):
    def __init__(self, name):
        Block.__init__(self, name, D)

        # ports:
        self.ports['anode'] = Port(self, 0, (60, 100))
        self.ports['cathode'] = Port(self, 1, (60, 0))

        # properties:
        self.properties['Isat (I)'] = 1.0E-9
        self.properties['Vt (V)'] = 25.85e-3

        # leads:
        self.lines.append(((60, 0), (60, 37)))
        self.lines.append(((60, 63), (60, 100)))

        # diode symbol:
        self.lines.append(((60, 37), (42, 63), (78, 63), (60, 37)))
        self.lines.append(((42, 37), (78, 37)))

    def get_engine(self, nodes):
        return D(nodes)


class GndBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, None, is_ground=True)

        # port:
        self.ports['ground'] = Port(self, 0, (60, 0), is_ground=True)

        # lead:
        self.lines.append(((60, 0), (60, 15)))

        # ground lines:
        self.lines.append(((45, 15), (75, 15)))
        self.lines.append(((52, 24), (68, 24)))
        self.lines.append(((58, 33), (62, 33)))

    def get_engine(self, nodes):
        raise Exception("GND Block has no engine.")


class VScopeBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, None, is_signal_device=True)
        self.size = (160, 120)
        self.margin = 12

        # port:
        self.ports['positive'] = Port(self, 0, (0, 60))
        self.ports['negative'] = Port(self, 1, (80, 120))

        # rects:
        (w, h), m = self.size, self.margin
        
        # rects:
        (w, h), m = self.size, self.margin
        self.rects.append(((0, 0, w, h, 5), (wx.BLACK, wx.Colour(180, 180, 180))))

        window = m, m, w - m * 2, h - m * 2, 1
        self.rects.append((window, (wx.Colour(80, 80, 80), wx.Colour(255, 255, 255))))

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
            self.plot_curves.append((plot_curve, wx.Colour(200, 100, 100)))

            window = (m, m), (w - m, m), (w - m, h - m), (m, h - m), (m, m)
            self.plot_curves.append((window, None))

    def get_engine(self, nodes):
        if len(nodes) == 1:
            nodes += [0]  # if only one connection, ground neg lead
        self.engine = VScope(nodes)
        return self.engine


class VScope3Block(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, None, is_signal_device=True)
        self.size = (160, 120)
        self.margin = 12

        # port:
        self.ports['A'] = Port(self, 0, (0, 40))
        self.ports['B'] = Port(self, 1, (0, 60))
        self.ports['C'] = Port(self, 2, (0, 80))
        self.ports['N'] = Port(self, 3, (80, 120))

        # rects:
        (w, h), m = self.size, self.margin

        # rects:
        (w, h), m = self.size, self.margin
        self.rects.append(((0, 0, w, h, 5), (wx.BLACK, wx.Colour(180, 180, 180))))

        window = m, m, w - m * 2, h - m * 2, 1
        self.rects.append((window, (wx.Colour(80, 80, 80), wx.Colour(255, 255, 255))))

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

            self.plot_curves.append((plot_curve1, wx.Colour(200, 100, 100)))
            self.plot_curves.append((plot_curve2, wx.Colour(100, 200, 100)))
            self.plot_curves.append((plot_curve3, wx.Colour(100, 100, 200)))

            window = (m, m), (w - m, m), (w - m, h - m), (m, h - m), (m, m)
            self.plot_curves.append((window, None))

    def get_engine(self, nodes):
        if len(nodes) == 1:
            nodes += [0, 0, 0]
        if len(nodes) == 2:
            nodes += [0, 0]
        if len(nodes) == 3:
            nodes += [0]
        self.engine = VScope3(nodes)
        return self.engine


class IScopeBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, None)
        self.size = (160, 120)
        self.margin = 12

        # port:
        self.ports['positive'] = Port(self, 0, (60, 160))
        self.ports['negative'] = Port(self, 1, (100, 160))

        # lines:
        self.lines.append(((80, 120), (80, 150)))
        self.lines.append(((60, 160), (100, 160)))

        # plus:
        self.lines.append(((60, 133), (60, 143)))
        self.lines.append(((55, 138), (65, 138)))

        # circle
        self.circles.append((75, 150, 10, 20))

        # rects:
        (w, h), m = self.size, self.margin
        self.rects.append(((0, 0, w, h, 5), (wx.BLACK, wx.Colour(180, 180, 180))))

        window = m, m, w - m * 2, h - m * 2, 1
        self.rects.append((window, (wx.Colour(80, 80, 80), wx.Colour(255, 255, 255))))

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

            iscale = 1.0
            if range_ > 0.0:
                iscale = -(h - m * 4.0) / range_

            self.margin = 12

            ioffset = -(mid * iscale - m * 5)

            # path:
            plot_curve = []
            for t, i in zip(times[::stride], values[::stride]):
                plot_curve.append((t * tscale + toffset, i * iscale + ioffset))

            self.plot_curves = []
            self.plot_curves.append((plot_curve, wx.Colour(200, 100, 100)))



    def get_engine(self, nodes):
        self.engine = IScope(nodes)
        return self.engine


# device type name to class mapping:
DEVICELIB = dict(R=RBlock, C=CBlock, L=LBlock, V=VBlock,
                 VSin=VSinBlock, D=DBlock, GND=GndBlock,
                 VScope=VScopeBlock, VScope3=VScope3Block, IScope=IScopeBlock)


class PropertyDialog(gui.PropertyDialog):
    def __init__(self, parent, caption, properties):
        self.armed = False
        gui.PropertyDialog.__init__(self, parent)
        self.SetTitle(caption)
        self.types = []
        self.keys = []
        self.properties = properties
        self.n = len(self.properties)
        self.propgrid.InsertRows(0, self.n)
        for i, (name, value) in enumerate(self.properties.items()):
            type_ = type(value)
            self.types.append(type_)
            self.keys.append(name)
            self.propgrid.SetCellValue(i, 0, str(value))
            self.propgrid.SetRowLabelValue(i, str(name))
        self.armed = True
        self.szr_main.Fit(self)
        self.Layout()
        self.propgrid.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)


    def OnKillFocus(self, event):
        # Cell editor's grandparent, the grid GridWindow's parent, is the grid.
        self.propgrid.SaveEditControlValue()

    def update(self):
        if self.armed:
            for i in range(self.n):
                type_ = self.types[i]
                key = self.keys[i]
                value = self.propgrid.GetCellValue(i, 0)
                try:
                    self.properties[key] = type_(value)
                except:
                    pass

    def on_grid_update(self, event):
        self.update()

    def OnClose(self, event):
        self.update()
        self.result = wx.ID_OK
        self.Destroy()


def update_properties(parent, caption, properties):
    propdlg = PropertyDialog(parent, caption, properties)

    if propdlg.ShowModal() == wx.ID_OK:
        for key, value in propdlg.properties.items():
            if key in properties:
                type_ = type(value)
                if type_ is type(properties[key]):
                    properties[key] = value
    return properties


class Schematic(object):
    def __init__(self, name):
        self.name = name
        self.blocks = {}
        self.connectors = []
        self.sim_settings = {'dt': 0.01, 'tmax': 10.0, 'maxitr': 100,
                             'tol': 0.00001, 'voltages': "2", 'currents': "V1"}


class SchematicWindow(wx.Panel):
    def __init__(self, parent, schematic=None, name=""):

        self.path = ""

        if schematic:
            self.schematic = schematic
        else:
            self.schematic = Schematic("Cir1")

        if name:
            self.schematic.name = name

        self.name = schematic.name
        self.blocks = schematic.blocks
        self.connectors = schematic.connectors
        self.sim_settings = schematic.sim_settings

        # init super:
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour(BG_COLOR)

        # bindings:
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_scroll)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_dclick)
        self.Bind(wx.EVT_SIZE, self.on_size)

        # mouse movement management:
        self.drug = False
        self.x0 = 0.0
        self.y0 = 0.0
        self.x = 0.0
        self.y = 0.0
        self.dx = 0.0
        self.dy = 0.0
        self.x0_object = 0.0
        self.y0_object = 0.0
        self.scale = 1.0
        self.scale_factor = 0.01

        self.pen = wx.Pen(DEVICE_COLOR, LINE_WIDTH)
        self.pen_hover = wx.Pen(HOVER_COLOR, HOVER_WIDTH)
        self.pen_select = wx.Pen(SELECT_COLOR, SELECT_WIDTH)
        self.pen_ghost = wx.Pen(GHOST_COLOR, LINE_WIDTH)
        self.brush = wx.Brush(DEVICE_COLOR)
        self.brush_hover = wx.Brush(HOVER_COLOR)
        self.brush_select = wx.Brush(SELECT_COLOR)
        self.brush_ghost = wx.Brush(GHOST_COLOR)
        self.pen.Cap = wx.CAP_ROUND
        self.pen_hover.Cap = wx.CAP_ROUND
        self.pen_select.Cap = wx.CAP_ROUND

        # drawing:
        self.SetDoubleBuffered(True)
        self.gc = None

        # members:
        self.netlist = None
        self.selected_objects = []
        self.hit_objects = []
        self.hit_blocks = []
        self.hit_ports = []
        self.hit_fields = []
        self.hit_connectors = []
        self.hit_connection_points = []
        self.hit_segments = []
        self.ghost = None
        self.new_counter = 1
        self.active_connector = None
        self.dragged = False
        self.top_obj = None
        self.hover_objects = []
        self.ghost_knee_segment = None

        # arm the schematic:
        self.mode = Mode.STANDBY

    def on_size(self, event):
        pass

    def on_dclick(self, event):
        self.update_position(event)
        self.update_hit_objects((self.x, self.y))

        if self.hit_fields:
            field = self.hit_fields[0]
            old = field.properties['text']
            properties = update_properties(self, 'Label', field.properties)
            new = properties['text']
            if not old == new:
                if new in self.blocks:
                    field.properties['text'] = old
                else:
                    self.blocks[new] = self.blocks.pop(old)
                    self.blocks[new].name = new


        elif self.hit_blocks:
            block = self.hit_blocks[0]
            label = "Properties for {0}".format(str(block))
            update_properties(self, label, block.properties)

    def select_object(self, obj):
        obj.selected = True
        if not obj in self.selected_objects:
            self.selected_objects.append(obj)

        if isinstance(obj, Segment):
            obj.connector.selected = True
            self.selected_objects.append(obj.connector)

    def deselect_object(self, obj):
        obj.selected = False
        if obj in self.selected_objects:
            self.selected_objects.remove(obj)

    def start_connector(self, connection):

        self.select_object(connection)
        connector = Connector(connection)
        self.add_connector(connector)
        connection.add_connector(connector)
        self.active_connector = connector

        if isinstance(connection, Port):
            self.active_connector.add_port(connection)
        elif isinstance(connection, KneePoint):
            self.active_connector.add_knee(connection)

    def end_connector(self, connection):

        self.active_connector.add_segment(connection)
        self.active_connector.partial = False
        self.deselect_object(connection)
        connection.add_connector(self.active_connector)

        if isinstance(connection, Port):
            self.active_connector.add_port(connection)
        elif isinstance(connection, KneePoint):
            self.active_connector.add_knee(connection)

        self.active_connector = None

    def remove_hover_all(self):
        for obj in self.hover_objects:
            obj.hover = False
        self.hover_objects = []

    def set_hover(self, obj):
        obj.hover = True
        if not obj in self.hover_objects:
            self.hover_objects.append(obj)

    def clean_up(self):
        # clean up temporary objs after clicks are processed:
        for connector in self.connectors:
            for seg in connector.segments:
                seg.ghost_knee = None

    def on_left_up(self, event):

        # reset translation points:
        self.x0, self.y0 = event.GetLogicalPosition(self.dc)
        self.x0_object, self.y0_object = self.x0, self.y0

        # get updated position:
        self.update_position(event)
        pt = self.x, self.y
        spt = self.snap(pt)

        # get context:
        ctrl = event.ControlDown()
        shft = event.ShiftDown()

        # determine hit objects:
        self.update_hit_objects(pt)
        self.remove_hover_all()

        # STATE MACHINE:

        if self.mode == Mode.STANDBY:

            if self.top_obj:

                if not(ctrl or shft):
                    self.deselect_all()

                if isinstance(self.top_obj, Segment):
                    self.select_object(self.top_obj.connector)
                else:
                    self.select_object(self.top_obj)

            else:
                self.deselect_all()

        elif self.mode == Mode.ADD_DEVICE:

            self.ghost.is_ghost = False
            self.ghost = None
            self.mode = Mode.STANDBY
            self.x0_object = 0.0
            self.y0_object = 0.0

        self.Refresh()

    def on_left_down(self, event):

        # reset translation points:
        self.x0, self.y0 = event.GetLogicalPosition(self.dc)
        self.x0_object, self.y0_object = self.x0, self.y0

        # get updated position:
        self.update_position(event)
        pt = self.x, self.y
        spt = self.snap(pt)

        # get context:
        ctrl = event.ControlDown()
        shft = event.ShiftDown()

        # see what's hit:
        self.update_hit_objects(pt)
        self.remove_hover_all()

        # STATE MACHINE:

        if self.mode == Mode.STANDBY:

            if self.top_obj:

                multi_select = ctrl or shft or len(self.selected_objects) > 1

                if isinstance(self.top_obj, (Block, BlockLabel)):
                    if not multi_select:
                        self.deselect_all()
                    self.select_object(self.top_obj)


                if isinstance(self.top_obj, KneePoint):
                    if self.top_obj.selected:
                        self.start_connector(self.top_obj)
                        self.mode = Mode.CONNECT
                    else:
                        if not multi_select:
                            self.deselect_all()
                        self.select_object(self.top_obj)

                elif isinstance(self.top_obj, ConnectionPoint):
                    self.start_connector(self.top_obj)
                    self.mode = Mode.CONNECT

            else:
                self.deselect_all()


        elif self.mode == Mode.CONNECT:

            if self.ghost_knee_segment:
                seg = self.ghost_knee_segment
                connector = seg.connector
                knee = seg.ghost_knee
                connector.split_segment(seg, knee)
                self.end_connector(knee)
                self.ghost_knee_segment.ghost_knee = None
                self.ghost_knee_segment = None
                self.mode = Mode.STANDBY

            elif self.hit_connection_points:
                connection = self.hit_connection_points[0]
                self.end_connector(connection)
                self.mode = Mode.STANDBY

            else:
                knee = KneePoint(self.active_connector, spt)
                self.active_connector.add_segment(knee)

        self.clean_up()
        self.Refresh()

    def on_right_down(self, event):

        # reset translation points:
        self.x0, self.y0 = event.GetLogicalPosition(self.dc)
        self.x0_object, self.y0_object = self.x0, self.y0

        # get updated position:
        self.update_position(event)
        pt = self.x, self.y
        spt = self.snap(pt)

        # get context:
        ctrl = event.ControlDown()
        shft = event.ShiftDown()

        # see what's hit:
        self.update_hit_objects(pt)
        self.remove_hover_all()

        if self.mode == Mode.STANDBY:

            if self.top_obj:
                if isinstance(self.top_obj, Segment):
                    connector = self.top_obj.connector
                    knee = KneePoint(connector, spt)
                    connector.split_segment(self.top_obj, knee)
                elif isinstance(self.top_obj, KneePoint):
                    connector = self.top_obj.connectors[0]
                    connector.remove_knee(self.top_obj)
            else:
                # context menu goes here...
                self.deselect_all()

        if self.mode == Mode.CONNECT:

            if self.hit_connection_points:
                connection = self.hit_connection_points[0]
                self.end_connector(connection)
                self.set_hover(connection)
                self.mode = Mode.STANDBY

            else:
                self.deselect_all()

        self.clean_up()

        self.Refresh()

    def on_motion(self, event):
        """
        1st: get position and snapped position

        :type event: wx.MouseEvent
        :return: None
        """

        # get position:
        self.update_position(event)
        pt = self.x, self.y
        spt = pt
        if SNAP_TO_GRID:
            spt = self.snap(pt)

        # determine context:
        dragging = event.Dragging()
        leftdown = event.LeftIsDown()
        rightdown = event.RightIsDown()

        # determine hit objects:
        self.update_hit_objects(pt)
        self.remove_hover_all()

        # STATE MACHINE:

        if self.mode == Mode.CONNECT:

            x, y = spt

            if ORTHO_CONNECTORS:
                x0, y0 = self.active_connector.get_last_point()
                if abs(x - x0) > abs(y - y0):
                    y = y0
                else:
                    x = x0

            self.active_connector.end = (x, y)

            if self.hit_segments:
                seg = self.hit_segments[0]
                connector = seg.connector
                if not connector is self.active_connector:
                    hpt = seg.closest_hit_point
                    if hpt:
                        hpt = self.snap(hpt)
                        if seg.ghost_knee:
                            seg.ghost_knee.position = hpt
                        else:
                            knee = KneePoint(seg.connector, hpt)
                            seg.ghost_knee = knee
                            self.ghost_knee_segment = seg

            elif self.ghost_knee_segment:
                self.ghost_knee_segment.ghost_knee = None

        if self.mode == Mode.ADD_DEVICE:

            self.ghost.position = spt

        elif self.mode == Mode.STANDBY:

            if dragging and leftdown:

                if self.selected_objects:
                    self.translate_selection((event.x, event.y))
                else:
                     self.translate_schematic((event.x, event.y))

            elif self.top_obj:
                self.set_hover(self.top_obj)

        self.Refresh()

    def translate_schematic(self, offset):
        x, y = offset
        self.dx += (x - self.x0)
        self.dy += (y - self.y0)
        self.x0 = x
        self.y0 = y

    def translate_selection(self, new_pt):
        x, y = new_pt
        dx = (x - self.x0_object) / self.scale
        dy = (y - self.y0_object) / self.scale
        self.x0_object = x
        self.y0_object = y
        for obj in self.selected_objects:
            obj.translate((dx, dy))
            if isinstance(obj, Connector):
                for knee in obj.knees:
                    knee.translate((dx, dy))
        self.auto_connect()

    def move_selection_by(self, delta):
        for obj in self.selected_objects:
            obj.translate(delta)
        self.auto_connect()

    def on_scroll(self, event):
        self.update_position(event)
        rot = event.GetWheelRotation()
        self.scale += rot * self.scale_factor
        self.scale = max(0.5, self.scale)
        self.update_position(event)
        self.Refresh()

    def on_key_up(self, event):

        code = event.GetKeyCode()

        if code == wx.WXK_ESCAPE:
            if self.mode == Mode.CONNECT and self.active_connector:
                self.connectors.remove(self.active_connector)
                self.active_connector = None
                self.mode = Mode.STANDBY
            self.deselect_all()

        elif code == wx.WXK_DELETE or code == wx.WXK_BACK:

            # delete selected objects:

            for obj in self.selected_objects:
                if isinstance(obj, Block):
                    to_del = None
                    for name, block in self.blocks.items():
                        if obj is block:
                            to_del = name
                    if to_del:
                        del self.blocks[to_del]
                elif isinstance(obj, Connector):
                    self.connectors.remove(obj)
                    for block in self.blocks.values():
                        for port in block.ports.values():
                            if obj in port.connectors:
                                port.connectors.remove(obj)
                    for connector in self.connectors:
                        for connection in connector.get_connectoin_points():
                            if obj in connection.connectors:
                                connection.connectors.remove(obj)
                elif isinstance(obj, KneePoint):
                    connector = obj.connectors[0]
                    connector.remove_knee(obj)

            self.deselect_all()

        # navigation:

        elif code == wx.WXK_UP or code == wx.WXK_NUMPAD_UP:
            self.move_selection_by((0, -MOVE_DELTA))

        elif code == wx.WXK_DOWN or code == wx.WXK_NUMPAD_DOWN:
            self.move_selection_by((0, MOVE_DELTA))

        elif code == wx.WXK_LEFT or code == wx.WXK_NUMPAD_LEFT:
            self.move_selection_by((-MOVE_DELTA, 0))

        elif code == wx.WXK_RIGHT or code == wx.WXK_NUMPAD_RIGHT:
            self.move_selection_by((MOVE_DELTA, 0))

        # rotate:

        elif code == ord('R'):
            if self.mode == Mode.ADD_DEVICE:
                self.ghost.rotate(90)
            elif self.mode == Mode.STANDBY:
                for obj in self.selected_objects:
                    if isinstance(obj, Block):
                        obj.rotate(90)
        self.Refresh()

    def on_paint(self, event):
        self.dc = wx.PaintDC(self)
        self.draw(self.dc)

    def update_hit_objects(self, pt):

        self.hit_objects = []
        self.hit_connection_points = []

        self.top_obj = None

        hit_blocks = {}
        hit_ports = {}
        hit_fields = {}
        hit_segments = {}
        hit_knees = {}

        # determine everything that's hit:
        for block in self.blocks.values():
            if block.hittest(pt):
                hit_blocks[block.zorder] = block
            for port in block.ports.values():
                if port.hittest(pt):
                    hit_ports[port.zorder] = port
            for field in block.fields.values():
                if field.hittest(pt):
                    hit_fields[field.zorder] = field
        for connector in self.connectors:
            for segment in connector.segments:
                if segment.hittest(pt):
                    hit_segments[segment.zorder] = segment
            for knee in connector.knees:
                if knee:
                    if knee.hittest(pt):
                        hit_knees[knee.zorder] = knee


        # sort by zorder and dump into member lists:

        self.hit_ports = [obj for (z, obj) in
                          reversed(sorted(hit_ports.items()))]

        self.hit_blocks = [obj for (z, obj) in
                           reversed(sorted(hit_blocks.items()))]

        self.hit_fields = [obj for (z, obj) in
                           reversed(sorted(hit_fields.items()))]

        self.hit_segments = [obj for (z, obj) in
                             reversed(sorted(hit_segments.items()))]

        self.hit_knees = [obj for (z, obj) in
                               reversed(sorted(hit_knees.items()))]

        # the order these lists are added is key:

        self.hit_objects = (self.hit_fields +
                            self.hit_ports +
                            self.hit_blocks +
                            self.hit_knees +
                            self.hit_segments)

        self.hit_connection_points = (self.hit_ports + self.hit_knees)

        if self.hit_objects:
            self.top_obj = self.hit_objects[0]

    def update_position(self, event):
        self.x = event.GetX()
        self.y = event.GetY()
        self.x = (self.x - self.dx) / self.scale
        self.y = (self.y - self.dy) / self.scale

    def add_block(self, key, block, position):
        self.blocks[key] = block
        self.blocks[key].position = position

    def deselect_all(self):
        for obj in self.selected_objects:
            obj.selected = False
        self.selected_objects = []

    def start_add(self, type_=None, name=None):

        if not type_:
            type_ = DEF_DEVICE

        if not name:
            i = 1
            name = "{0}{1}".format(type_, i)
            while name in self.blocks:
                i += 1
                name = "{0}{1}".format(type_, i)

        self.ghost = DEVICELIB[type_](name)
        self.mode = Mode.ADD_DEVICE
        self.blocks[name] = self.ghost
        self.ghost.is_ghost = True
        self.ghost.translate((-50, -50))
        self.SetFocus()

    def draw_grid(self, gc):
        spacing = GRID_SIZE
        extension = 1000.0
        w, h = gc.GetSize()
        w += extension
        h += extension
        ver = int(w / spacing)
        hor = int(h / spacing)
        pen = wx.Pen(GRID_COLOR, GRID_WIDTH)
        pen.Cap = wx.CAP_BUTT
        gc.SetPen(pen)
        for i in range(ver):
            offset = i * spacing - extension / 2
            gc.StrokeLine(offset, 0 - extension / 2, offset, h)
        for i in range(hor):
            offset = i * spacing - extension / 2
            gc.StrokeLine(0 - extension / 2, offset, w, offset)

    def get_bounding(self, path):
        rect = path.GetBox()
        x, y = rect.GetLeftTop()
        w, h = rect.GetSize()
        bounding = (x, y, w, h)
        center = rect.GetCentre()
        return bounding, center

    def snap(self, position):
        if position:
            x, y = position
            dx = x % GRID_SIZE
            dy = y % GRID_SIZE
            if dx > GRID_SIZE / 2:
                x += GRID_SIZE - dx
            else:
                x -= dx
            if dy > GRID_SIZE / 2:
                y += GRID_SIZE - dy
            else:
                y -= dy
            return x, y
        else:
            return None

    def consolidate_connection_points(self):
        pass

    def auto_connect(self):
        tol = GRID_SIZE / 2

        # auto connect port to port:

        portmap = {}
        for block in self.blocks.values():
            for port in block.ports.values():
                x, y = port.center
                if (x, y) in portmap:
                    portmap[(x, y)].append(port)
                else:
                    portmap[(x, y)] = [port]

        for pt, ports in portmap.items():
            if len(ports) == 2:
                p1, p2 = ports
                connected = False
                for connector1 in p1.connectors:
                    for connector2 in p2.connectors:
                        if connector1 is connector2:
                            connected = True
                            break
                    if connected:
                        break
                if not connected:
                    self.add_auto_connector(p1, p2)

        # auto connect port to connector:

        for block in self.blocks.values():
            for port in block.ports.values():
                pass

    def add_connector(self, connector):
        if not connector in self.connectors:
            self.connectors.append(connector)

    def add_auto_connector(self, connection1, connection2):

        pt1 = connection1.center
        connector = Connector(pt1)
        self.add_connector(connector)
        connection1.add_connector(connector)
        connector.start_connection_point = connection1

        if isinstance(connection1, Port):
            connector.add_port(connection1)
        elif isinstance(connection1, KneePoint):
            connector.add_knee(connection1)

        connection2.add_connector(connector)
        end = connection2.center

        if isinstance(connection2, Port):
            connector.add_port(connection2)
        elif isinstance(connection2, KneePoint):
            connector.add_knee(connection2)

        connector.end_connection_point = connection2
        connector.end = end

        connection1.add_connector(connector)
        connection2.add_connector(connector)

    def draw_block(self, block, gc):

        font = wx.Font(FONT_SIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                       wx.FONTWEIGHT_BOLD, False, 'Courier 10 Pitch')

        if block.is_ghost:
            gc.SetPen(self.pen_ghost)
            gc.SetBrush(self.brush_ghost)

        elif block.selected:
            gc.SetPen(self.pen_select)
            gc.SetBrush(self.brush_select)

        elif block.hover:
            gc.SetPen(self.pen_hover)
            gc.SetBrush(self.brush_hover)

        else:
            gc.SetPen(self.pen)
            gc.SetBrush(self.brush)

        x, y = self.snap(block.position)
        rad = block.rotation * 0.0174532925
        matrix = gc.CreateMatrix()
        matrix.Translate(x, y)
        matrix.Rotate(rad)
        path = gc.CreatePath()

        for line in block.lines:
            path.MoveToPoint(line[0])
            for point in line[1:]:
                x2, y2 = point
                path.AddLineToPoint(x2, y2)

        hd_rects = []

        for rect in block.rects:
            if len(rect) == 2:
                hd_rects.append(rect)
            else:
                path.AddRoundedRectangle(*rect)

        for circle in block.circles:
            if len(circle) == 3:
                path.AddCircle(*circle)
            elif len(circle) == 4:
                path.AddEllipse(*circle)

        for arc in block.arcs:
            x, y, r, ang1, ang2, clockwise = arc
            x0 = x + r * math.cos(ang1)
            y0 = y + r * math.sin(ang2)
            path.MoveToPoint((x0, y0))
            path.AddArc(x, y, r, ang1, ang2, clockwise)

        path.Transform(matrix)
        gc.StrokePath(path)

        for rect, (stroke, fill) in hd_rects:
            path = gc.CreatePath()
            path.AddRoundedRectangle(*rect)
            path.Transform(matrix)
            if fill:
                gc.SetBrush(wx.Brush(fill))
                gc.FillPath(path)
            if stroke:
                gc.SetPen(wx.Pen(stroke, 1))
                gc.StrokePath(path)

        if block.plot_curves:

            for plot_curve in block.plot_curves:
                curve, color = plot_curve
                if not color:
                    color = DEVICE_COLOR
                pen = wx.Pen(color, 1)
                path = gc.CreatePath()
                gc.SetPen(pen)
                path.MoveToPoint(curve[0])
                for point in curve[1:]:
                    x2, y2 = point
                    path.AddLineToPoint(x2, y2)
                path.Transform(matrix)
                gc.StrokePath(path)

        block.bounding_rects[0], block.center = self.get_bounding(path)

        for key, field in block.fields.items():

            if block.is_ghost:
                gf = gc.CreateFont(font, GHOST_COLOR)

            elif field.selected or block.selected:
                gf = gc.CreateFont(font, SELECT_COLOR)

            elif field.hover or block.hover:
                gf = gc.CreateFont(font, HOVER_COLOR)

            else:
                gf = gc.CreateFont(font, DEVICE_COLOR)

            gc.SetFont(gf)

            x, y, w, h = block.bounding_rects[0]
            xo, yo = field.position
            xt, yt = x + xo, y + yo
            gc.DrawText(field.get_text(), xt, yt)
            w, h, d, e = gc.GetFullTextExtent(field.get_text())
            field.bounding_rects[0] = (xt, yt, w, h)
            field.center = (xt + w * 0.5, yt + h * 0.5)

        for name, port in block.ports.items():

            force_show = False

            if block.is_ghost:
                gc.SetPen(self.pen_ghost)
                gc.SetBrush(self.brush_ghost)
                gf = gc.CreateFont(font, GHOST_COLOR)
                force_show = True

            elif block.selected:
                gc.SetPen(self.pen_select)
                gc.SetBrush(self.brush_select)
                gf = gc.CreateFont(font, SELECT_COLOR)
                force_show = True

            elif port.selected:
                gc.SetPen(self.pen)
                gc.SetBrush(self.brush)
                gf = gc.CreateFont(font, DEVICE_COLOR)
                force_show = True

            elif port.hover:
                gc.SetPen(self.pen_select)
                gc.SetBrush(self.brush_select)
                gf = gc.CreateFont(font, HOVER_COLOR)
                force_show = True

            elif block.hover:
                gc.SetPen(self.pen_hover)
                gc.SetBrush(self.brush_hover)
                gf = gc.CreateFont(font, HOVER_COLOR)
                force_show = True

            else:
                gc.SetPen(self.pen)
                gc.SetBrush(self.brush)
                gf = gc.CreateFont(font, DEVICE_COLOR)
                force_show = False

            for connector in port.connectors:
                for seg in connector.segments:
                    if seg.selected:
                        gc.SetPen(self.pen_select)
                        gc.SetBrush(self.brush_select)
                        gf = gc.CreateFont(font, SELECT_COLOR)
                        force_show = True

                    elif seg.hover:
                        gc.SetPen(self.pen_hover)
                        gc.SetBrush(self.brush_hover)
                        gf = gc.CreateFont(font, HOVER_COLOR)
                        force_show = True


            gc.SetFont(gf)

            (x, y), r, m = port.position, port.radius, port.hit_margin
            path = gc.CreatePath()
            path.MoveToPoint(x, y)
            path.AddCircle(x, y, r)
            path.Transform(matrix)

            if len(port.connectors) > 1 or force_show:
                # gc.StrokePath(path)
                gc.FillPath(path)

            path = gc.CreatePath()
            path.AddRectangle(x - r - m, y - r - m, (r + m) * 2, (r + m) * 2)
            path.Transform(matrix)
            port.bounding_rects[0], port.center = self.get_bounding(path)

    def draw_connector(self, connector, gc):

        segment_hover = False
        segment_selected = False

        for segment in connector.segments:
            if segment.hover:
                segment_hover = True
            if segment.selected:
                segment_selected = True

        if segment_selected or connector.selected:
            gc.SetPen(self.pen_select)
            gc.SetBrush(self.brush_select)
        elif segment_hover:
            gc.SetPen(self.pen_hover)
            gc.SetBrush(self.brush_hover)
        else:
            gc.SetPen(self.pen)
            gc.SetBrush(self.brush)

        path = gc.CreatePath()
        path.MoveToPoint(connector.start_connection_point.center)

        for seg in connector.segments:
            p1, p2 = seg
            path.AddLineToPoint(self.snap(p2))

        if connector.partial:
            path.AddLineToPoint(*connector.end)

        gc.StrokePath(path)

        # draw knees:

        for knee in connector.knees:

            draw = False

            if knee.selected or segment_selected:
                gc.SetPen(self.pen_select)
                gc.SetBrush(self.brush_select)
                draw = True

            elif knee.hover or segment_hover:
                gc.SetPen(self.pen_hover)
                gc.SetBrush(self.brush_hover)
                draw = True

            if len(knee.connectors) > 1 or draw:
                path = gc.CreatePath()

                (x, y), r, m = self.snap(knee), PORT_RADIUS, PORT_HIT_MARGIN
                path.MoveToPoint(x, y)
                path.AddCircle(x, y, r)
                knee.bounding_rects[0] = (x-r-m, y-r-m, (r+m)*2, (r+m)*2)
                knee.center = (x, y)

                #gc.StrokePath(path)
                gc.FillPath(path)

        # draw ghost knee point:
        for seg in connector.segments:
            if seg.ghost_knee:
                path = gc.CreatePath()
                (x, y), r = seg.ghost_knee.position, PORT_RADIUS
                path.MoveToPoint(x, y)
                path.AddCircle(x, y, r)
                gc.FillPath(path)

    def draw(self, dc):
        w, h = self.dc.GetSize()
        gc = wx.GraphicsContext.Create(self.dc)

        # translate:
        gc.Translate(self.dx, self.dy)

        # scale:
        gc.Scale(self.scale, self.scale)

        # grid:
        self.draw_grid(gc)

        if SHOW_CROSSHAIR:
            path = gc.CreatePath()
            path.AddCircle(self.x, self.y, 5)
            gc.SetPen(wx.Pen(wx.Colour(100, 200, 100), 1))
            gc.SetBrush(wx.Brush(wx.Colour(100, 200, 100)))
            gc.FillPath(path)

        # schematic:
        for name, block in self.blocks.items():
            self.draw_block(block, gc)

        for connector in self.connectors:
            self.draw_connector(connector, gc)


        # debug: show hit boxes:

        ALL_BOXES = False
        ONE_BOX = True

        if ALL_BOXES:
            icolor = 0
            colors = [wx.Colour(200, 100, 100),
                      wx.Colour(100, 200, 100),
                      wx.Colour(100, 100, 200),
                      wx.Colour(150, 50, 50),
                      wx.Colour(50, 150, 50),
                      wx.Colour(50, 50, 150)]

            line_width = 2
            for obj in self.hit_objects:
                path = gc.CreatePath()
                for rect in obj.bounding_rects:
                    x, y, w, h = rect
                    path.AddRoundedRectangle(x, y, w, h, 2)
                gc.SetPen(wx.Pen(colors[icolor], line_width))
                gc.StrokePath(path)
                icolor += 1
                icolor = min(icolor, len(colors)-1)

        elif ONE_BOX:
            if self.top_obj:
                path = gc.CreatePath()
                for rect in self.top_obj.bounding_rects:
                    x, y, w, h = rect
                    path.AddRoundedRectangle(x, y, w, h, 2)
                gc.SetPen(wx.Pen(wx.Colour(200, 100, 100), 2))
                gc.StrokePath(path)

    def build_netlist(self):

        groups = [[], ]

        connector_groups = []

        # first, make groups of all the connected connectors
        connector_groups = []
        for connector in self.connectors:
            grp = []
            for connection in connector.get_connectoin_points():
                for connector in connection.connectors:
                    grp.append(connector)
            grp = list(set(grp))
            connector_groups.append(grp)

        combine = 1

        while combine:
            combine = None
            for i in range(len(connector_groups)-1):
                for j in range(i+1, len(connector_groups)):
                    for connector1 in connector_groups[i]:
                        for connector2 in connector_groups[j]:
                            if connector1 is connector2:
                                combine = (i, j)
                                break
                        if combine:
                            break
                    if combine:
                        break
                if combine:
                    break

            if combine:
                i, j = combine
                connector_groups[i] += connector_groups[j]
                del connector_groups[j]

        for i, grp in enumerate(connector_groups):
            connector_groups[i] = list(set(grp))

        a = 6

        # now build port groups:

        port_groups = [[], ]

        for connector_group in connector_groups:
            is_ground = False
            port_group = []
            for connector in connector_group:
                for port in connector.ports:
                    port_group.append(port)
                    if port.is_ground:
                        is_ground = True
            port_group = list(set(port_group))
            if is_ground:
                port_groups[0] += port_group
            else:
                port_groups.append(port_group)

        netlist = Netlist(self.name)

        for name, block in self.blocks.items():
            if not block.is_ground:
                nodemap = {}
                for key, port in block.ports.items():
                    for i, group in enumerate(port_groups):
                        if port in group:
                            nodemap[port.index] = i
                sort = sorted(nodemap.items())
                nodes = []
                for k, v in sort:
                    nodes.append(v)
                netlist.device(block.name, block.get_engine(nodes))

        return netlist


class MainFrame(gui.MainFrame):
    DEF_NAME = "Cir{0}"

    def __init__(self):
        gui.MainFrame.__init__(self, None)
        self.schematics = {}
        self.schcnt = 1
        self.active_schem = None

    def new_schem(self, name=None):
        if not name:
            name = MainFrame.DEF_NAME.format(self.schcnt)
        sch = Schematic(name)
        schem = SchematicWindow(frame.ntb_main, sch)
        self.ntb_main.AddPage(schem, name, select=True)
        self.schcnt += 1
        self.schematics[name] = schem
        self.active_schem = schem
        return schem

    def add_device(self, type_):
        if self.active_schem:
            self.active_schem.start_add(type_)

    def save_schematic(self, schem, path):
        try:
            with open(path, 'w') as f:
                schem = clone(schem.schematic)
                # remove plot curves:
                for device in schem.blocks.values():
                    device.plot_curves = []
                pickle.dump(schem, f)
                wx.MessageBox("File saved to: [{0}]".format(path))
        except Exception as e:
            wx.MessageBox("File save failed. {0}".format(e.message))

    def open_schematic(self, path):
        d, name = os.path.split(path)
        f = open(path)
        sch = pickle.load(f)
        sch.name = name
        schem = SchematicWindow(frame.ntb_main, sch)
        self.schematics[name] = schem
        self.active_schem = schem
        self.ntb_main.AddPage(schem, name)

    def run(self):
        if self.active_schem:
            netlist = self.active_schem.build_netlist()

            settings = self.active_schem.sim_settings

            dt = settings['dt']
            tmax = settings['tmax']
            maxitr = settings['maxitr']
            tol = settings['tol']
            voltages = settings['voltages']
            currents = settings['currents']

            netlist.trans(dt, tmax)

            for block in self.active_schem.blocks.values():
                block.end()

            chans = []

            for v in voltages.split():
                chans.append(Voltage(int(v.strip())))

            for i in currents.split():
                chans.append(Current(i.strip()))

            netlist.plot(*chans)

            self.active_schem.Refresh()

    def add_gadget(self, type_):
        if self.active_schem:
            self.active_schem.start_add(type_)

    def on_new_schem(self, event):
        self.new_schem()

    def on_open(self, event):
        dlg = wx.FileDialog(self, message="Save Schematic",
                            defaultFile="",
                            wildcard="*.sch",
                            style=(wx.FD_OPEN |
                                   wx.FD_MULTIPLE |
                                   wx.FD_FILE_MUST_EXIST))

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.open_schematic(path)

    def on_save_as(self, event):
        schem = None
        if self.active_schem:
            schem = self.active_schem
        elif self.schematics:
            schem = self.schematics[0]

        if schem:
            name = schem.name.split(".")[0]
            name = "{0}.sch".format(name)
            dlg = wx.FileDialog(self, message="Save Schematic",
                                defaultFile=name,
                                wildcard="*.sch",
                                style=wx.FD_SAVE)

            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                self.save_schematic(schem, path)
                schem.path = path

    def on_save(self, event):
        schem = None
        if self.active_schem:
            schem = self.active_schem
        elif self.schematics:
            schem = self.schematics[0]

        if schem:
            if schem.path:
                self.save_schematic(schem, schem.path)

    def on_add_ground(self, event):
        self.add_device("GND")

    def on_add_R(self, event):
        self.add_device("R")

    def on_add_L(self, event):
        self.add_device("L")

    def on_add_C(self, event):
        self.add_device("C")

    def on_add_V(self, event):
        self.add_device("V")

    def on_add_VSin(self, event):
        self.add_device("VSin")

    def on_add_VPulse(self, event):
        self.add_device("VPulse")

    def on_add_VPwl(self, event):
        self.add_device("VPwl")

    def on_add_I(self, event):
        self.add_device("I")

    def on_add_D(self, event):
        self.add_device("D")

    def on_add_vscope(self, event):
        self.add_gadget("VScope")

    def on_add_vscope3(self, event):
        self.add_gadget("VScope3")

    def on_add_iscope(self, event):
        self.add_gadget("IScope")

    def on_setup(self, event):
        self.active_schem.sim_settings = update_properties(self,
                "Simulation Setup", self.active_schem.sim_settings)

    def on_run(self, event):
        self.run()

    def on_page_close(self, event):
        index = event.GetSelection()


def distance(line, point):
    (cx, cy), ((ax, ay), (bx, by)) = point, line
    r_num = (cx - ax) * (bx - ax) + (cy - ay) * (by - ay)
    r_den = (bx - ax) * (bx - ax) + (by - ay) * (by - ay)
    if r_den > 0.0:
        r = r_num / r_den
        px, py = ax + r * (bx - ax), ay + r * (by - ay)
        s = ((ay - cy) * (bx - ax) - (ax - cx) * (by - ay) ) / r_den

        xx = px
        yy = py

        if (r >= 0) and (r <= 1):
            dseg = abs(s) * math.sqrt(r_den)
        else:
            dist1 = (cx - ax) * (cx - ax) + (cy - ay) * (cy - ay)
            dist2 = (cx - bx) * (cx - bx) + (cy - by) * (cy - by)
            if dist1 < dist2:
                xx = ax
                yy = ay
                dseg = math.sqrt(dist1)
            else:
                xx = bx
                yy = by
                dseg = math.sqrt(dist2)
        return (xx, yy), dseg
    else:
        return point, float('inf')


# region Main:

if __name__ == '__main__':
    app = wx.App()
    frame = MainFrame()
    frame.SetSize((800, 600))
    frame.SetPosition((100, 100))
    #frame.new_schem()

    frame.open_schematic("/Users/josephmhood/Documents/Cir1.sch")
    #frame.open_schematic("C:/Users/josephmhood/Desktop/Cir1.sch")
    #frame.run()

    frame.Show()
    app.MainLoop()

    # endregion