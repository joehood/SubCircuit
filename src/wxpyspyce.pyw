from __future__ import print_function, division
import pickle
import os
from collections import OrderedDict as ODict

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

BG_COLOR = wx.Colour(0, 0, 0)
GRID_COLOR = wx.Colour(30, 30, 30)
DEVICE_COLOR = wx.Colour(130, 130, 130)
SELECT_COLOR = wx.Colour(255, 255, 255)
HOVER_COLOR = wx.Colour(255, 255, 255)

LINE_WIDTH = 3
SELECT_WIDTH = 6
HOVER_WIDTH = 3
GRID_SIZE = 10
GRID_WIDTH = 1
SHOW_CROSSHAIR = False
MOVE_DELTA = GRID_SIZE
GHOST_COLOR = GRID_COLOR
DEF_DEVICE = "R"
FONT_SIZE = 20
ORTHO_CONNECTORS = True
CONNECTOR_HIT_MARGIN = 10
PORT_HIT_MARGIN = 10
PORT_RADIUS = 4

# endregion
class Orientation:
    NONE = 0
    VERTICAL = 1
    HORIZONTAL = 2

class SchematicObject(object):
    def __init__(self):
        self.position = 0, 0
        self.rotation = 0
        self.hor_flip = False
        self.ver_flip = False
        self.scale = 1.0
        self.selected = False
        self.center = (0, 0)
        self.hover = False
        self.selected = False
        self.bounding_rects = [(0, 0, 0, 0)]

    def translate(self, delta):
        x, y = self.position
        dx, dy = delta
        self.position = x + dx, y + dy
        if self.bounding_rects:
            for i, (x, y, w, h) in enumerate(self.bounding_rects):
                self.bounding_rects[i] = (x + dx, y + dx, w, h)

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
    def __init__(self):
        SchematicObject.__init__(self)


class Port(ConnectionPoint):
    def __init__(self, block, index, position, is_ground=False):
        ConnectionPoint.__init__(self)
        self.index = index
        self.node = None
        self.position = position
        self.connectors = []
        self.block = block
        self.radius = PORT_RADIUS
        self.hit_margin = PORT_HIT_MARGIN
        self.connected = False
        self.is_ground = is_ground

    def __str__(self):
        return "{0}:{1}".format(self.block, self.index)

    def __repr__(self):
        return str(self)


class Joint(ConnectionPoint):
    def __init__(self):
        ConnectionPoint.__init__(self)
        self.port = None
        self.segment = None
        self.connector = None
        self.fixed = False


class Segment(SchematicObject):
    def __init__(self):
        SchematicObject.__init__(self)
        self.joints = []
        self.line = (0, 0, 0, 0)
        self.orientation = Orientation.NONE


class Connector(SchematicObject):
    def __init__(self, start):
        SchematicObject.__init__(self)

        self.start = start
        self.end = start
        self.partial = True
        self.knees = []
        self.ports = []
        self.joints = []
        self.end_connection_point = None
        self.start_connection_point = None
        self.segments = []


    def add_port(self, port):
        self.ports.append(port)
        port.connected = True

    def add_knee(self, point):
        self.knees.append(point)

    def __str__(self):
        s = ""
        for port in self.ports:
            s += str(port) + "-"
        return s.rstrip("-")

    def __repr__(self):
        return str(self)


class BlockField(SchematicObject):
    def __init__(self, name, text, position=(0, 0)):
        SchematicObject.__init__(self)
        self.name = name
        self.text = text
        self.position = position


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

        self.fields['name'] = BlockField('name', name)

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
        self.ports['positive'] = Port(self, 0, (50, 0))
        self.ports['negative'] = Port(self, 1, (50, 100))

        # properties:
        self.properties['Resistance (R)'] = 1.0

        # resistor shape:
        self.lines.append(((50, 0), (50, 20), (35, 25), (65, 35), (35, 45),
                           (65, 55), (35, 65), (65, 75), (50, 80), (50, 100)))

    def get_engine(self, nodes):
        return R(nodes, self.properties['Resistance (R)'])


class CBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, C)

        # ports:
        self.ports['positive'] = Port(self, 0, (50, 0))
        self.ports['negative'] = Port(self, 1, (50, 100))

        # properties:
        self.properties['Capacitance (F)'] = 0.1

        # leads:
        self.lines.append(((50, 0), (50, 40)))
        self.lines.append(((50, 60), (50, 100)))

        # plates:
        self.lines.append(((30, 40), (70, 40)))
        self.lines.append(((30, 60), (70, 60)))

    def get_engine(self, nodes):
        return C(nodes, self.properties['Capacitance (F)'])


class LBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, L)

        # ports:
        self.ports['positive'] = Port(self, 0, (50, 0))
        self.ports['negative'] = Port(self, 1, (50, 100))

        # properties:
        self.properties['Inductance (H)'] = 0.1

        # leads:
        self.lines.append(((50, 0), (50, 20)))
        self.lines.append(((50, 80), (50, 100)))

        # coils (x, y, r, ang0, ang1, clockwise)
        ang1 = -math.pi * 0.5
        ang2 = math.pi * 0.5
        self.arcs.append((50, 30, 10, ang1, ang2, True))
        self.arcs.append((50, 50, 10, ang1, ang2, True))
        self.arcs.append((50, 70, 10, ang1, ang2, True))

    def get_engine(self, nodes):
        return L(nodes, self.properties['Inductance (H)'])


class VBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, V)

        # ports:
        self.ports['positive'] = Port(self, 0, (50, 0))
        self.ports['negative'] = Port(self, 1, (50, 100))

        # properties:
        self.properties['Voltage (V)'] = 1.0

        # leads:
        self.lines.append(((50, 0), (50, 25)))
        self.lines.append(((50, 75), (50, 100)))

        # plus:
        self.lines.append(((50, 33), (50, 43)))
        self.lines.append(((45, 38), (55, 38)))

        # circle
        self.circles.append((50, 50, 25))

    def get_engine(self, nodes):
        return V(nodes, self.properties['Voltage (V)'])


class VSinBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, V)

        # ports:
        self.ports['positive'] = Port(self, 0, (50, 0))
        self.ports['negative'] = Port(self, 1, (50, 100))

        # properties:
        self.properties['Voltage Offset (V)'] = 0.0
        self.properties['Voltage Amplitude (V)'] = 1.0
        self.properties['Frequency (Hz)'] = 60.0
        self.properties['Delay (s)'] = 0.0
        self.properties['Damping factor (1/s)'] = 0.0
        self.properties['Phase (rad)'] = 0.0

        # leads:
        self.lines.append(((50, 0), (50, 25)))
        self.lines.append(((50, 75), (50, 100)))

        # plus:
        self.lines.append(((50, 33), (50, 43)))
        self.lines.append(((45, 38), (55, 38)))

        # circle
        self.circles.append((50, 50, 25))

        # sine:
        a1 = math.pi * 1.0
        a2 = math.pi * 0.0
        self.arcs.append((43, 58, 7, a1, a2, True))
        self.arcs.append((57, 58, 7, -a1, -a2, False))

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
        self.ports['anode'] = Port(self, 0, (50, 100))
        self.ports['cathode'] = Port(self, 1, (50, 0))

        # properties:
        self.properties['Isat (I)'] = 1.0E-9
        self.properties['Vt (V)'] = 25.85e-3

        # leads:
        self.lines.append(((50, 0), (50, 37)))
        self.lines.append(((50, 63), (50, 100)))

        # diode symbol:
        self.lines.append(((50, 37), (32, 63), (68, 63), (50, 37)))
        self.lines.append(((32, 37), (68, 37)))


    def get_engine(self, nodes):
        return D(nodes)


class GndBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, None, is_ground=True)

        # port:
        self.ports['ground'] = Port(self, 0, (50, 0), is_ground=True)

        # lead:
        self.lines.append(((50, 0), (50, 15)))

        # ground lines:
        self.lines.append(((35, 15), (65, 15)))
        self.lines.append(((42, 24), (58, 24)))
        self.lines.append(((48, 33), (52, 33)))

    def get_engine(self, nodes):
        raise Exception("GND Block has no engine.")


class VScopeBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, None, is_signal_device=True)
        self.size = (200, 100)
        self.margin = 12

        # port:
        self.ports['positive'] = Port(self, 0, (0, 50))
        self.ports['negative'] = Port(self, 1, (100, 100))

        # rects:
        (w, h), m = self.size, self.margin
        self.rects.append((0, 0, w, h, 5))

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

            voffset = -(mid * vscale - m * 4)

            # path:
            plot_curve = []
            for t, v in zip(times[::stride], values[::stride]):
                plot_curve.append((t * tscale + toffset, v * vscale + voffset))

            self.plot_curves = []
            self.plot_curves.append(plot_curve)

            window = (m, m), (w - m, m), (w - m, h - m), (m, h - m), (m, m)
            self.plot_curves.append(window)

    def get_engine(self, nodes):
        self.engine = VScope(nodes)
        return self.engine


class IScopeBlock(Block):
    def __init__(self, name):
        # init super:
        Block.__init__(self, name, None)
        self.size = (200, 120)
        self.margin = 12

        # port:
        self.ports['positive'] = Port(self, 0, (50, 120))
        self.ports['negative'] = Port(self, 1, (150, 120))

        # rects:
        (w, h), m = self.size, self.margin
        self.rects.append((0, 0, w, h, 5))

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
            self.plot_curves.append(plot_curve)

            window = (m, m), (w - m, m), (w - m, h - m), (m, h - m), (m, m)
            self.plot_curves.append(window)

    def get_engine(self, nodes):
        self.engine = IScope(nodes)
        return self.engine


# device type name to class mapping:
DEVICELIB = dict(R=RBlock, C=CBlock, L=LBlock, V=VBlock,
                 VSin=VSinBlock, D=DBlock, GND=GndBlock,
                 VScope=VScopeBlock, IScope=IScopeBlock)


class Mode(object):
    DISARMED = 0
    STANDBY = 1
    CONNECT = 2
    MOVE = 3
    EDIT = 4
    ADD_DEVICE = 5
    ADD_JOINT = 6


class PropertyDialog(gui.PropertyDialog):
    def __init__(self, parent, properties):
        self.armed = False
        gui.PropertyDialog.__init__(self, parent)
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

    def on_grid_update(self, event):
        if self.armed:
            for i in range(self.n):
                type_ = self.types[i]
                key = self.keys[i]
                value = self.propgrid.GetCellValue(i, 0)
                try:
                    self.properties[key] = type_(value)
                except:
                    pass


def update_properties(parent, properties):
    propdlg = PropertyDialog(parent, properties)

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
        self.Bind(wx.EVT_PAINT, self.draw)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_scroll)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_dclick)

        # drawing context:
        self.gc = None
        self.dc = None

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

        # block management:
        self.selected_objects = []
        self.ghost = None
        self.new_counter = 1

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

        # mode management:
        self.mode = Mode.STANDBY

        # connection management:
        self.active_connector = None
        self.active_joint = None
        self.active_joint_conn = None

        # solution management:
        self.netlist = None

    def update_position(self, event):
        self.x, self.y = event.GetLogicalPosition(self.dc)
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

    def on_dclick(self, event):
        self.update_position(event)
        pt = self.x, self.y
        block = None
        for name, blk in self.blocks.items():
            if blk.hittest(pt):
                block = blk
                break
        if block:
            block.properties = update_properties(self, block.properties)

    def on_left_up(self, event):
        self.drug = False

        if self.mode == Mode.ADD_DEVICE:
            self.ghost.is_ghost = False
            self.ghost = None
            self.mode = Mode.STANDBY
            self.x0_object = 0.0
            self.y0_object = 0.0

        self.Refresh()

    def on_left_down(self, event):

        self.x0, self.y0 = event.GetLogicalPosition(self.dc)
        self.x0_object, self.y0_object = self.x0, self.y0
        self.update_position(event)
        pt = self.x, self.y
        ctrl = event.ControlDown()
        shft = event.ShiftDown()
        drag = event.Dragging()

        if self.mode == Mode.STANDBY:
            port_hit = False
            block_hit = False
            field_hit = False
            connector_hit = False
            for name, block in self.blocks.items():
                for name, field in block.fields.items():
                    if field.hittest(pt):
                        if field.selected:
                            field.selected = False
                            self.selected_objects.remove(field)
                        else:
                            field.selected = True
                            field_hit = True
                        if not (ctrl or shft):
                            self.selected_objects = []
                        self.selected_objects.append(field)
                    elif not (ctrl or shft):
                        field.selected = False

                for name, port in block.ports.items():
                    if port.hittest(pt) and not field_hit:
                        port_hit = True
                        port.selected = True
                        self.mode = Mode.CONNECT
                        port_pt = port.center
                        connector = Connector(port_pt)
                        connector.add_port(port)
                        port.connectors.append(connector)
                        connector.start_connection_point = port
                        self.connectors.append(connector)
                        self.active_connector = connector
                    else:
                        port.selected = False
                if block.hittest(pt) and not port_hit and not field_hit:
                    if block.selected:
                        block.selected = False
                        self.selected_objects.remove(block)
                    else:
                        block.selected = True
                        block_hit = True
                        if not (ctrl or shft):
                            self.selected_objects = []
                        self.selected_objects.append(block)
                elif not (ctrl or shft):
                    block.selected = False

            for connector in self.connectors:
                if (connector.hittest(pt) and not block_hit
                                          and not port_hit
                                          and not field_hit):
                    connector.selected = True
                    connector_hit = True
                    if not (ctrl or shft):
                        self.selected_objects = []
                    self.selected_objects.append(connector)
                    self.mode = Mode.ADD_JOINT
                    self.active_joint = Joint()
                    for segment in connector.segments:
                        if segment.hittest(pt):
                            x1, y1, x2, y2 = segment.line
                            xs, ys = self.snap(pt)
                            if x1 == x2:
                                self.active_joint.position = x1, ys
                            else:
                                self.active_joint.position = xs, y1
                    self.active_joint_conn = connector
                    connector.joints.append(self.active_joint)

                elif not (ctrl or shft):
                    connector.selected = False

            if not (port_hit or block_hit or field_hit or connector_hit):
                self.deselect_all()

        elif self.mode == Mode.CONNECT:
            port_hit = False
            for name, block in self.blocks.items():
                for name, port in block.ports.items():
                    if port.hittest(pt):
                        port_hit = True
                        port.selected = False
                        port.connectors.append(self.active_connector)
                        self.active_connector.start_connection_point.selected = False
                        self.mode = Mode.STANDBY
                        port_pt = port.center
                        self.active_connector.end = port_pt
                        self.active_connector.add_port(port)
                        self.active_connector.end_connection_point = port
                        self.active_connector = None
            if not port_hit:
                self.active_connector.add_knee(pt)

        elif self.mode == Mode.ADD_DEVICE:
            pass

        elif self.mode == Mode.ADD_JOINT:
            if self.active_joint_conn.hittest(pt):
                pt2 = pt
                for segment in self.active_joint_conn.segments:
                    if segment.hittest(pt):
                        x1, y1, x2, y2 = segment.line
                        xs, ys = self.snap(pt)
                        if x1 == x2:
                            self.active_joint.position = x1, ys
                            pt2 = x1, ys
                        else:
                            self.active_joint.position = xs, y1
                            pt2 = xs, y1
                        break

                connector = Connector(pt2)
                connector.end = pt2
                self.connectors.append(connector)
                connector.start_connection_point = self.active_joint
                connector.joints.append(self.active_joint)
                connector.hover = True
                self.active_connector = connector

                self.active_joint.fixed = True
                self.active_joint_conn.selected = False
                self.active_joint_conn = None
                self.active_joint.selected = True
                self.active_joint = None

                self.mode = Mode.CONNECT

        self.Refresh()

    def on_motion(self, event):
        self.update_position(event)
        pt = self.x, self.y
        drag = event.Dragging()
        left = event.LeftIsDown()

        if self.mode == Mode.ADD_DEVICE:
            self.ghost.position = self.snap(pt)

        else:
            if drag and left:
                if self.selected_objects:
                    dx_object = (event.x - self.x0_object) / self.scale
                    dy_object = (event.y - self.y0_object) / self.scale
                    self.x0_object = event.x
                    self.y0_object = event.y
                    for obj in self.selected_objects:
                        obj.translate((dx_object, dy_object))
                else:
                    self.dx += (event.x - self.x0)
                    self.dy += (event.y - self.y0)
                    self.x0 = event.x
                    self.y0 = event.y

            else:  # moving but not dragging (hovering):
                if self.mode == Mode.ADD_JOINT:
                    if self.active_joint_conn.hittest(pt):
                        for segment in self.active_joint_conn.segments:
                            if segment.hittest(pt):
                                x1, y1, x2, y2 = segment.line
                                xs, ys = self.snap(pt)
                                if x1 == x2:
                                    self.active_joint.position = x1, ys
                                else:
                                    self.active_joint.position = xs, y1

                    else:
                        self.active_joint_conn.joints.remove(self.active_joint)
                        self.active_joint_conn = None
                        self.active_joint = None
                        self.mode = Mode.STANDBY
                else:
                    if self.mode == Mode.CONNECT:
                        port_hit = False
                        for block in self.blocks.values():
                            for port in block.ports.values():
                                if port.hittest(pt):
                                    port.hover = True
                                    port_hit = True
                                else:
                                    port.hover = False
                        self.active_connector.end = self.snap(pt)

                    else:
                        port_hit = False
                        conn_hit = False
                        block_hit = False
                        field_hit = False
                        for block in self.blocks.values():
                            for name, field in block.fields.items():
                                if field.hittest(pt):
                                    field.hover = True
                                    field_hit = True
                                else:
                                    field.hover = False
                            for port in block.ports.values():
                                if port.hittest(pt) and not field_hit:
                                    port.hover = True
                                    port_hit = True
                                else:
                                    port.hover = False
                            if (block.hittest(pt) and not port_hit
                                    and not field_hit):
                                block.hover = True
                                block_hit = True
                            else:
                                block.hover = False

                        for connector in self.connectors:
                            if (connector.hittest(pt) and not block_hit
                                                      and not port_hit
                                                      and not field_hit):
                                conn_hit = True

                                if connector.selected:
                                    if not self.mode == Mode.ADD_JOINT:
                                        self.mode = Mode.ADD_JOINT
                                        self.active_joint = Joint()
                                        self.active_joint_conn = connector
                                        connector.joints.append(self.active_joint)
                                    for segment in connector.segments:
                                        if segment.hittest(pt):
                                            x1, y1, x2, y2 = segment.line
                                            xs, ys = self.snap(pt)
                                            if x1 == x2:
                                                self.active_joint.position = x1, ys
                                            else:
                                                self.active_joint.position = xs, y1

                                else:
                                    connector.hover = True
                            else:
                                connector.hover = False

                        if not conn_hit and self.mode == Mode.ADD_JOINT:
                            self.mode = Mode.STANDBY



        self.Refresh()

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

        elif code == wx.WXK_UP or code == wx.WXK_NUMPAD_UP:
            for obj in self.selected_objects:
                obj.translate((0, -MOVE_DELTA))

        elif code == wx.WXK_DOWN or code == wx.WXK_NUMPAD_DOWN:
            for obj in self.selected_objects:
                obj.translate((0, MOVE_DELTA))

        elif code == wx.WXK_LEFT or code == wx.WXK_NUMPAD_LEFT:
            for obj in self.selected_objects:
                obj.translate((-MOVE_DELTA, 0))

        elif code == wx.WXK_RIGHT or code == wx.WXK_NUMPAD_RIGHT:
            for obj in self.selected_objects:
                obj.translate((MOVE_DELTA, 0))

        elif code == ord('R'):
            if self.mode == Mode.ADD_DEVICE:
                self.ghost.rotate(90)

        self.Refresh()

    def on_right_down(self, event):
        pass

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
        x, y = position
        dx = x % GRID_SIZE
        dy = y % GRID_SIZE
        if dx > GRID_SIZE:
            x += dx - GRID_SIZE
        else:
            x -= dx
        if dy > GRID_SIZE:
            y += dy - GRID_SIZE
        else:
            y -= dy

        return x, y

    def render_block(self, block, gc):

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

        for rect in block.rects:
            path.AddRoundedRectangle(*rect)

        for circle in block.circles:
            path.AddCircle(*circle)

        for arc in block.arcs:
            x, y, r, ang1, ang2, clockwise = arc
            x0 = x + r * math.cos(ang1)
            y0 = y + r * math.sin(ang2)
            path.MoveToPoint((x0, y0))
            path.AddArc(x, y, r, ang1, ang2, clockwise)

        path.Transform(matrix)
        gc.StrokePath(path)

        if block.plot_curves:
            pen = wx.Pen(DEVICE_COLOR, 1)
            path2 = gc.CreatePath()
            gc.SetPen(pen)
            for curve in block.plot_curves:
                path2.MoveToPoint(curve[0])
                for point in curve[1:]:
                    x2, y2 = point
                    path2.AddLineToPoint(x2, y2)
            path2.Transform(matrix)
            gc.StrokePath(path2)

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
            gc.DrawText(field.text, xt, yt)
            w, h, d, e = gc.GetFullTextExtent(field.text)
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
                if connector.selected:
                    gc.SetPen(self.pen_select)
                    gc.SetBrush(self.brush_select)
                    gf = gc.CreateFont(font, SELECT_COLOR)
                    force_show = True

                elif connector.hover:
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
                gc.StrokePath(path)
                gc.FillPath(path)

            path = gc.CreatePath()
            path.AddRectangle(x - r - m, y - r - m, (r + m) * 2, (r + m) * 2)
            path.Transform(matrix)
            port.bounding_rects[0], port.center = self.get_bounding(path)

    def render_connector(self, connector, gc):

        connector.start = connector.start_connection_point.center
        if connector.end_connection_point:
            connector.end = connector.end_connection_point.center

        if connector.selected:
            gc.SetPen(self.pen_select)
            gc.SetBrush(self.brush_select)
        elif connector.hover:
            gc.SetPen(self.pen_hover)
            gc.SetBrush(self.brush_hover)
        else:
            gc.SetPen(self.pen)
            gc.SetBrush(self.brush)

        path = gc.CreatePath()
        points = []

        path.MoveToPoint(connector.start)
        points.append(connector.start)

        if ORTHO_CONNECTORS:
            x1, y1 = connector.start
            for knee in connector.knees:
                x2, y2 = self.snap(knee)

                path.AddLineToPoint(x1, y2)
                points.append((x1, y2))

                path.AddLineToPoint(x2, y2)
                points.append((x2, y2))

                x1, y1 = x2, y2

            x2, y2 = connector.end
            path.AddLineToPoint(x1, y2)
            points.append((x1, y2))

        else:
            for knee in connector.knees:
                x2, y2 = self.snap(knee)
                path.AddLineToPoint(x2, y2)
                points.append((x2, y2))

        path.AddLineToPoint(connector.end)
        points.append(connector.end)

        gc.StrokePath(path)

        connector.bounding_rects = []
        connector.segments = []

        if points:
            m = CONNECTOR_HIT_MARGIN
            x1, y1 = points[0]
            for x2, y2 in points[1:]:
                x, y = min(x1, x2), min(y1, y2)
                w, h = max(x1, x2) - x, max(y1, y2) - y
                box = x - m, y - m, w + m * 2, h + m * 2

                segments = Segment()
                segments.line = (x1, y1, x2, y2)
                segments.bounding_rects[0] = box

                if x1 == x2:
                    segments.orientation = Orientation.VERTICAL
                else:
                    segments.orientation = Orientation.HORIZONTAL

                connector.segments.append(segments)
                connector.bounding_rects.append(box)

                x1, y1 = x2, y2

        # draw joints:
        path = gc.CreatePath()
        for joint in connector.joints:
            (x, y), r, m = joint.position, PORT_RADIUS, PORT_HIT_MARGIN
            path.MoveToPoint(x, y)
            path.AddCircle(x, y, r)
            joint.bounding_rects[0] = (x-r-m, y-r-m, (r+m)*2, (r+m)*2)
            joint.center = (x, y)
        gc.StrokePath(path)
        gc.FillPath(path)

    def draw(self, event):

        # get context:
        self.dc = wx.PaintDC(self)
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
        for connector in self.connectors:
            self.render_connector(connector, gc)

        for name, block in self.blocks.items():
            self.render_block(block, gc)

    def build_netlist(self):

        groups = [[], ]

        for connector in self.connectors:
            start = connector.start_connection_point
            end = connector.end_connection_point

            istart = -1
            iend = -1

            if start.is_ground or end.is_ground:
                if start not in groups[0]:
                    groups[0].append(start)
                if end not in groups[0]:
                    groups[0].append(end)

            for i, group in enumerate(groups):
                if start in group:
                    istart = i
                if end in group:
                    iend = i

            if istart < 0 and iend < 0:
                groups.append([start, end])

            elif istart < 0 and iend >= 0:
                groups[iend].append(start)

            elif istart >= 0 and iend < 0:
                groups[istart].append(end)

            elif istart >= 0 and iend >= 0:
                if istart == 0:
                    groups[0].extend(groups[iend][:])
                    del groups[iend]
                elif iend == 0:
                    groups[0].extend(groups[istart][:])
                    del groups[istart]
                else:
                    groups[istart].extend(groups[iend][:])
                    del groups[iend]

        for i, group in enumerate(groups):
            st = set(group)
            groups[i] = list(st)

        # now add all unconnected ports to ground group:
        for block in self.blocks.values():
            for port in block.ports.values():
                found = False
                for group in groups:
                    if port in group:
                        found = True
                        break
                if not found:
                    groups[0].append(port)

        netlist = Netlist(self.name)

        for name, block in self.blocks.items():
            if not block.is_ground:
                nodemap = {}
                for key, port in block.ports.items():
                    for i, group in enumerate(groups):
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

    def on_add_iscope(self, event):
        self.add_gadget("IScope")

    def on_setup(self, event):
        self.active_schem.sim_settings = update_properties(self,
                                                           self.active_schem.sim_settings)

    def on_run(self, event):
        self.run()

    def on_page_close(self, event):
        index = event.GetSelection()


# region Main:

if __name__ == '__main__':
    app = wx.App()
    frame = MainFrame()
    frame.SetSize((800, 600))
    frame.SetPosition((100, 100))
    frame.new_schem()

    #frame.open_schematic("/Users/josephmhood/Documents/Cir1.sch")
    #frame.run()

    frame.Show()
    app.MainLoop()

    # endregion