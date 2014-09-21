"""Subcircuit interface for schematic development and simulation control."""

from __future__ import print_function, division
import pickle
import os
import sys
import math
from copy import deepcopy as clone
from collections import OrderedDict as ODict

import wx
import wx.aui as aui

import subcircuit.netlist as net
import subcircuit.interfaces as inter
import subcircuit.sandbox as sb
import subcircuit.gui as gui
import subcircuit.loader as load


# region CONSTANTS

ICONFILE = "subcircuit.ico"
DEF_SCHEM_NAME = "cir{0}"

# endregion


# region globals:

engines = {}
blocks = {}

# endregion


#region Classes

class PropertyGetter(gui.PropertyDialog):
    def __init__(self, parent, caption, properties, size=(300, 300)):
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
        self.SetMinSize(size)

        self.propgrid.Bind(wx.EVT_KILL_FOCUS, self.on_kill_focus)

        self.result = wx.ID_CANCEL

    @classmethod
    def update_properties(cls, parent, caption, properties):
        propdlg = PropertyGetter(parent, caption, properties)

        if propdlg.ShowModal() == wx.ID_OK:
            for key, value in propdlg.properties.items():
                if key in properties:
                    type_ = type(value)
                    if type_ is type(properties[key]):
                        properties[key] = value
        return properties

    def on_kill_focus(self, event):
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
                except (ValueError, KeyError) as e:
                    pass

    def on_grid_update(self, event):
        self.update()

    def OnClose(self, event):
        self.update()
        self.result = wx.ID_OK
        self.Destroy()


class SchematicWindow(wx.Panel):
    def __init__(self, parent, schematic=None, name=""):

        self.path = ""

        if schematic:
            self.schematic = schematic
        else:
            self.schematic = sb.Schematic("Cir1")

        if name:
            self.schematic.name = name

        self.name = schematic.name
        self.blocks = schematic.blocks
        self.connectors = schematic.connectors
        self.sim_settings = schematic.sim_settings

        # init super:
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour(sb.BG_COLOR)

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

        self.pen = wx.Pen(sb.DEVICE_COLOR, sb.LINE_WIDTH)
        self.pen_hover = wx.Pen(sb.HOVER_COLOR, sb.HOVER_WIDTH)
        self.pen_select = wx.Pen(sb.SELECT_COLOR, sb.SELECT_WIDTH)
        self.pen_ghost = wx.Pen(sb.GHOST_COLOR, sb.LINE_WIDTH)
        self.brush = wx.Brush(sb.DEVICE_COLOR)
        self.brush_hover = wx.Brush(sb.HOVER_COLOR)
        self.brush_select = wx.Brush(sb.SELECT_COLOR)
        self.brush_ghost = wx.Brush(sb.GHOST_COLOR)
        self.pen.Cap = wx.CAP_ROUND
        self.pen_hover.Cap = wx.CAP_ROUND
        self.pen_select.Cap = wx.CAP_ROUND

        # drawing:
        self.SetDoubleBuffered(True)
        self.gc = None
        self.dc = None

        # state:
        self.netlist = None
        self.selected_objects = []
        self.hit_objects = []
        self.hit_blocks = []
        self.hit_ports = []
        self.hit_fields = []
        self.hit_knees = []
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
        self.mode = sb.Mode.STANDBY

    def on_size(self, event):
        pass

    def on_dclick(self, event):
        self.update_position(event)
        self.update_hit_objects((self.x, self.y))

        if self.hit_fields:
            field = self.hit_fields[0]
            old = field.properties['text']

            properties = PropertyGetter.update_properties(self,
                                                          'Label',
                                                          field.properties)
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
            PropertyGetter.update_properties(self, label, block.properties)

    def select_object(self, obj):
        obj.selected = True
        if not obj in self.selected_objects:
            self.selected_objects.append(obj)

        if isinstance(obj, sb.Segment):
            obj.connector.selected = True
            self.selected_objects.append(obj.connector)

    def deselect_object(self, obj):
        obj.selected = False
        if obj in self.selected_objects:
            self.selected_objects.remove(obj)

    def start_connector(self, connection):

        self.select_object(connection)
        connector = sb.Connector(connection)
        self.add_connector(connector)
        connection.add_connector(connector)
        self.active_connector = connector

        if isinstance(connection, sb.Port):
            self.active_connector.add_port(connection)
        elif isinstance(connection, sb.KneePoint):
            self.active_connector.add_knee(connection)

    def end_connector(self, connection):

        self.active_connector.add_segment(connection)
        self.active_connector.partial = False
        self.deselect_object(connection)
        connection.add_connector(self.active_connector)

        if isinstance(connection, sb.Port):
            self.active_connector.add_port(connection)
        elif isinstance(connection, sb.KneePoint):
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
        try:
            self.x0, self.y0 = event.GetLogicalPosition(self.dc)
        except Exception as e:
            pass

        self.x0_object, self.y0_object = self.x0, self.y0

        # get updated position:
        self.update_position(event)
        pt = self.x, self.y

        # get context:
        ctrl = event.ControlDown()
        shft = event.ShiftDown()

        # determine hit objects:
        self.update_hit_objects(pt)
        self.remove_hover_all()

        # STATE MACHINE:

        if self.mode == sb.Mode.STANDBY:

            if self.top_obj:

                if not(ctrl or shft):
                    self.deselect_all()

                if isinstance(self.top_obj, sb.Segment):
                    self.select_object(self.top_obj.connector)
                else:
                    self.select_object(self.top_obj)

            else:
                self.deselect_all()

        elif self.mode == sb.Mode.ADD_BLOCK:

            self.ghost.is_ghost = False
            self.ghost = None
            self.mode = sb.Mode.STANDBY
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

        if self.mode == sb.Mode.STANDBY:

            if self.top_obj:

                multi_select = ctrl or shft or len(self.selected_objects) > 1

                if isinstance(self.top_obj, (sb.Block, sb.BlockLabel)):
                    if not multi_select:
                        self.deselect_all()
                    self.select_object(self.top_obj)

                if isinstance(self.top_obj, sb.KneePoint):
                    if self.top_obj.selected:
                        self.start_connector(self.top_obj)
                        self.mode = sb.Mode.CONNECT
                    else:
                        if not multi_select:
                            self.deselect_all()
                        self.select_object(self.top_obj)

                elif isinstance(self.top_obj, sb.ConnectionPoint):
                    self.start_connector(self.top_obj)
                    self.mode = sb.Mode.CONNECT

            else:
                self.deselect_all()

        elif self.mode == sb.Mode.CONNECT:

            if self.ghost_knee_segment:
                seg = self.ghost_knee_segment
                connector = seg.connector
                knee = seg.ghost_knee
                connector.split_segment(seg, knee)
                self.end_connector(knee)
                self.ghost_knee_segment.ghost_knee = None
                self.ghost_knee_segment = None
                self.mode = sb.Mode.STANDBY

            elif self.hit_connection_points:
                connection = self.hit_connection_points[0]
                self.end_connector(connection)
                self.mode = sb.Mode.STANDBY

            else:
                knee = sb.KneePoint(self.active_connector, spt)
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
        # ctrl = event.ControlDown()
        # shft = event.ShiftDown()

        # see what's hit:
        self.update_hit_objects(pt)
        self.remove_hover_all()

        if self.mode == sb.Mode.STANDBY:

            if self.top_obj:
                if isinstance(self.top_obj, sb.Segment):
                    connector = self.top_obj.connector
                    knee = sb.KneePoint(connector, spt)
                    connector.split_segment(self.top_obj, knee)
                elif isinstance(self.top_obj, sb.KneePoint):
                    connector = self.top_obj.connectors[0]
                    connector.remove_knee(self.top_obj)
            else:
                # context menu goes here...
                self.deselect_all()

        if self.mode == sb.Mode.CONNECT:

            if self.hit_connection_points:
                connection = self.hit_connection_points[0]
                self.end_connector(connection)
                self.set_hover(connection)
                self.mode = sb.Mode.STANDBY

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
        if sb.SNAP_TO_GRID:
            spt = self.snap(pt)

        # determine context:
        dragging = event.Dragging()
        leftdown = event.LeftIsDown()
        rightdown = event.RightIsDown()

        # determine hit objects:
        self.update_hit_objects(pt)
        self.remove_hover_all()

        # STATE MACHINE:

        if self.mode == sb.Mode.CONNECT:

            x, y = spt

            if sb.ORTHO_CONNECTORS:
                x0, y0 = self.active_connector.get_last_point()
                if abs(x - x0) > abs(y - y0):
                    y = y0
                else:
                    x = x0

            self.active_connector.end = (x, y)

            if self.top_obj:
                if not isinstance(self.top_obj, sb.Port) and self.hit_segments:
                    seg = self.hit_segments[0]
                    connector = seg.connector
                    if not connector is self.active_connector:
                        hpt = seg.closest_hit_point
                        if hpt:
                            hpt = self.snap(hpt)
                            if seg.ghost_knee:
                                seg.ghost_knee.position = hpt
                            else:
                                knee = sb.KneePoint(seg.connector, hpt)
                                seg.ghost_knee = knee
                                self.ghost_knee_segment = seg

            elif self.ghost_knee_segment:
                self.ghost_knee_segment.ghost_knee = None

        if self.mode == sb.Mode.ADD_BLOCK:

            self.ghost.position = spt

        elif self.mode == sb.Mode.STANDBY:

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
            if isinstance(obj, sb.Connector):
                for knee in obj.knees:
                    knee.translate((dx, dy))
        #self.auto_connect()

    def move_selection_by(self, delta):
        for obj in self.selected_objects:
            obj.translate(delta)
        #self.auto_connect()

    def on_scroll(self, event):
        self.update_position(event)
        rot = event.GetWheelRotation()
        self.scale += rot * self.scale_factor * 0.1
        self.scale = max(0.5, self.scale)
        self.update_position(event)
        self.Refresh()

    def on_key_up(self, event):

        code = event.GetKeyCode()

        if code == wx.WXK_ESCAPE:
            if self.mode == sb.Mode.CONNECT and self.active_connector:
                self.connectors.remove(self.active_connector)
                self.active_connector = None
                self.mode = sb.Mode.STANDBY
            self.deselect_all()

        elif code == wx.WXK_DELETE or code == wx.WXK_BACK:

            # delete selected objects:

            for obj in self.selected_objects:
                if isinstance(obj, sb.Block):
                    to_del = None
                    for name, block in self.blocks.items():
                        if obj is block:
                            to_del = name
                    if to_del:
                        del self.blocks[to_del]
                elif isinstance(obj, sb.Connector):
                    self.connectors.remove(obj)
                    for block in self.blocks.values():
                        for port in block.ports.values():
                            if obj in port.connectors:
                                port.connectors.remove(obj)
                    for connector in self.connectors:
                        for connection in connector.get_connectoin_points():
                            if obj in connection.connectors:
                                connection.connectors.remove(obj)
                elif isinstance(obj, sb.KneePoint):
                    connector = obj.connectors[0]
                    connector.remove_knee(obj)

            self.deselect_all()

        # navigation:

        elif code == wx.WXK_UP or code == wx.WXK_NUMPAD_UP:
            self.move_selection_by((0, -sb.MOVE_DELTA))

        elif code == wx.WXK_DOWN or code == wx.WXK_NUMPAD_DOWN:
            self.move_selection_by((0, sb.MOVE_DELTA))

        elif code == wx.WXK_LEFT or code == wx.WXK_NUMPAD_LEFT:
            self.move_selection_by((-sb.MOVE_DELTA, 0))

        elif code == wx.WXK_RIGHT or code == wx.WXK_NUMPAD_RIGHT:
            self.move_selection_by((sb.MOVE_DELTA, 0))

        # rotate:
        elif code == ord('R'):
            if self.mode == sb.Mode.ADD_BLOCK:
                self.ghost.rotate(90)
            elif self.mode == sb.Mode.STANDBY:
                for obj in self.selected_objects:
                    if isinstance(obj, sb.Block):
                        obj.rotate(90)

        # flip horizontal:
        elif code == ord('H'):
            if self.mode == sb.Mode.ADD_BLOCK:
                self.ghost.flip_horizontal()
            elif self.mode == sb.Mode.STANDBY:
                for obj in self.selected_objects:
                    if isinstance(obj, sb.Block):
                        obj.flip_horizontal()

        # flip vertical:
        elif code == ord('V'):
            if self.mode == sb.Mode.ADD_BLOCK:
                self.ghost.flip_vertical()
            elif self.mode == sb.Mode.STANDBY:
                for obj in self.selected_objects:
                    if isinstance(obj, sb.Block):
                        obj.flip_vertical()

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

        # get the block definition from the global block dict:
        cls = blocks[type_]
        label = cls.label

        if not type_:
            type_ = sb.DEF_DEVICE

        if not name:
            i = 1
            key = "{0}{1}".format(label, i)
            i = 1
            while key in self.blocks:
                i += 1
                key = "{0}{1}".format(label, i)
        else:
            i = 0
            key = name
            while key in self.blocks:
                i += 1
                key = "{0}{1}".format(name, i)

        # great the instance as the "ghost" to be placed on the schematic:
        self.ghost = cls(key)

        self.mode = sb.Mode.ADD_BLOCK
        self.blocks[key] = self.ghost
        self.ghost.is_ghost = True
        self.ghost.translate((-50, -50))  # center mouse on device
        self.SetFocus()

    def draw_grid(self, gc):
        spacing = sb.GRID_SIZE
        extension = 1000.0
        w, h = gc.GetSize()
        w += extension
        h += extension
        ver = int(w / spacing)
        hor = int(h / spacing)
        pen = wx.Pen(sb.GRID_COLOR, sb.GRID_WIDTH)
        pen.Cap = wx.CAP_BUTT
        gc.SetPen(pen)
        for i in range(ver):
            offset = i * spacing - extension / 2
            gc.StrokeLine(offset, 0 - extension / 2, offset, h)
        for i in range(hor):
            offset = i * spacing - extension / 2
            gc.StrokeLine(0 - extension / 2, offset, w, offset)

    @staticmethod
    def get_bounding(path):
        rect = path.GetBox()
        x, y = rect.GetLeftTop()
        w, h = rect.GetSize()
        bounding = (x, y, w, h)
        center = rect.GetCentre()
        return bounding, center

    @staticmethod
    def snap(position):
        if position:
            x, y = position
            dx = x % sb.GRID_SIZE
            dy = y % sb.GRID_SIZE
            if dx > sb.GRID_SIZE / 2:
                x += sb.GRID_SIZE - dx
            else:
                x -= dx
            if dy > sb.GRID_SIZE / 2:
                y += sb.GRID_SIZE - dy
            else:
                y -= dy
            return x, y
        else:
            return None

    def consolidate_connection_points(self):
        pass

    def auto_connect(self):
        tol = sb.GRID_SIZE / 2

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
        connector = sb.Connector(pt1)
        self.add_connector(connector)
        connection1.add_connector(connector)
        connector.start_connection_point = connection1

        if isinstance(connection1, sb.Port):
            connector.add_port(connection1)
        elif isinstance(connection1, sb.KneePoint):
            connector.add_knee(connection1)

        connection2.add_connector(connector)
        end = connection2.center

        if isinstance(connection2, sb.Port):
            connector.add_port(connection2)
        elif isinstance(connection2, sb.KneePoint):
            connector.add_knee(connection2)

        connector.end_connection_point = connection2
        connector.end = end

        connection1.add_connector(connector)
        connection2.add_connector(connector)

    def draw_block(self, block, gc):

        font = wx.Font(sb.FONT_SIZE, wx.FONTFAMILY_DEFAULT,
                       wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False,
                       "Courier 10 Pitch")

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

        if block.hor_flip:
            matrix.Scale(-1.0, 1.0)

        if block.ver_flip:
            matrix.Scale(1.0, -1.0)

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
            y0 = y + r * math.sin(ang1)
            path.MoveToPoint((x0, y0))
            path.AddArc(x, y, r, ang1, ang2, clockwise)

        path.Transform(matrix)
        gc.StrokePath(path)

        block.bounding_rects[0], block.center = self.get_bounding(path)

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
                    color = sb.DEVICE_COLOR
                pen = wx.Pen(color, 1)
                path = gc.CreatePath()
                gc.SetPen(pen)
                path.MoveToPoint(curve[0])
                for point in curve[1:]:
                    x2, y2 = point
                    path.AddLineToPoint(x2, y2)
                path.Transform(matrix)
                gc.StrokePath(path)


        for key, field in block.fields.items():

            if block.is_ghost:
                gf = gc.CreateFont(font, sb.GHOST_COLOR)

            elif field.selected or block.selected:
                gf = gc.CreateFont(font, sb.SELECT_COLOR)

            elif field.hover or block.hover:
                gf = gc.CreateFont(font, sb.HOVER_COLOR)

            else:
                gf = gc.CreateFont(font, sb.DEVICE_COLOR)

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
                gf = gc.CreateFont(font, sb.GHOST_COLOR)
                force_show = True

            elif block.selected:
                gc.SetPen(self.pen_select)
                gc.SetBrush(self.brush_select)
                gf = gc.CreateFont(font, sb.SELECT_COLOR)
                force_show = True

            elif port.selected:
                gc.SetPen(self.pen)
                gc.SetBrush(self.brush)
                gf = gc.CreateFont(font, sb.DEVICE_COLOR)
                force_show = True

            elif port.hover:
                gc.SetPen(self.pen_select)
                gc.SetBrush(self.brush_select)
                gf = gc.CreateFont(font, sb.HOVER_COLOR)
                force_show = True

            elif block.hover:
                gc.SetPen(self.pen_hover)
                gc.SetBrush(self.brush_hover)
                gf = gc.CreateFont(font, sb.HOVER_COLOR)
                force_show = True

            else:
                gc.SetPen(self.pen)
                gc.SetBrush(self.brush)
                gf = gc.CreateFont(font, sb.DEVICE_COLOR)
                force_show = False

            for connector in port.connectors:
                for seg in connector.segments:
                    if seg.selected:
                        gc.SetPen(self.pen_select)
                        gc.SetBrush(self.brush_select)
                        gf = gc.CreateFont(font, sb.SELECT_COLOR)
                        force_show = True

                    elif seg.hover:
                        gc.SetPen(self.pen_hover)
                        gc.SetBrush(self.brush_hover)
                        gf = gc.CreateFont(font, sb.HOVER_COLOR)
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

            if knee is not None:

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

                    (x, y), r, m = (self.snap(knee), sb.PORT_RADIUS,
                                    sb.PORT_HIT_MARGIN)

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
                (x, y), r = seg.ghost_knee.position, sb.PORT_RADIUS
                path.MoveToPoint(x, y)
                path.AddCircle(x, y, r)
                gc.FillPath(path)

    def draw(self, dc):
        self.dc = dc
        w, h = self.dc.GetSize()
        gc = wx.GraphicsContext.Create(self.dc)

        # translate:
        gc.Translate(self.dx, self.dy)

        # scale:
        gc.Scale(self.scale, self.scale)

        # grid:
        self.draw_grid(gc)

        if sb.SHOW_CROSSHAIR:
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
                    if not rect == (0, 0, 0, 0):
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
                for connector2 in connection.connectors:
                    grp.append(connector2)
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

        netlist = net.Netlist(self.name)

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

                if block.__class__.engine == engines["X"]:

                    netlist.device(block.name, block.get_engine(nodes,
                                                                netlist))
                else:

                    netlist.device(block.name, block.get_engine(nodes))

        return netlist


class StatusStream:
    def __init__(self, statusbar):
        self.statusbar = statusbar

    def write(self, string):
        if string.strip():
            self.statusbar.SetStatusText(string)


class MainFrame(gui.MainFrame):

    def __init__(self):

        # super:
        gui.MainFrame.__init__(self, None)

        # schematic setup:
        self.schematics = {}
        self.schcnt = 1
        self.active_schem = None

        # icon:
        icon = wx.Icon(ICONFILE, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        # additional bindings (others are in gui.py):
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSED, self.on_page_close,
                  self.ntb_main)
        self.Bind(aui.EVT__AUINOTEBOOK_TAB_RIGHT_DOWN, self.on_schem_context,
                  self.ntb_main)

        # add all loaded devices to the window:
        self.menu_blocks = wx.Menu()

        self.add_event_devices = {}

        blocks_by_family = {}

        for key, block in blocks.items():
            if not block.family in blocks_by_family:
                blocks_by_family[block.family] = {}
            blocks_by_family[block.family][key] = block

        for family, famblocks in blocks_by_family.items():
            sub_menu = wx.Menu()
            for key, block in famblocks.items():
                event_id = wx.NewId()
                item = wx.MenuItem(sub_menu, event_id, key)
                sub_menu.AppendItem(item)
                self.Bind(wx.EVT_MENU, self.on_add_device, id=event_id)
                self.add_event_devices[event_id] = key

            self.menu_blocks.AppendSubMenu(sub_menu, family)

        self.menu.Append(self.menu_blocks, "Blocks")

        # re-layout after adding menu:
        self.Layout()

        self.statusbar.SetStatusText("Ready")

        self.status_stream = StatusStream(self.statusbar)
        #sys.stdout = self.status_stream

    def new_schem(self, name=None):
        if not name:
            name = DEF_SCHEM_NAME.format(self.schcnt) + ".sch"
            unique = False
            while not unique:
                unique = True
                for schem in self.schematics:
                    if name == schem:
                        unique = False
                        break
                if not unique:
                    self.schcnt += 1
                    name = MainFrame.DEF_SCHEM_NAME.format(self.schcnt) + ".sch"
        self.schcnt += 1
        sch = sb.Schematic(name)
        schem = SchematicWindow(frame.ntb_main, sch)
        self.ntb_main.AddPage(schem, name, select=True)
        self.schematics[name] = schem
        self.active_schem = schem
        schem.path = None
        return schem

    def add_device(self, type_):
        if self.active_schem:
            self.active_schem.start_add(type_)
        else:
            msg = ("Cannot add device without a schematic. Create a new "
                   "schematic from Schematic > new, or load an existing "
                   "schematic from Schematic > open")

            wx.MessageBox(msg, "Add Device Error", parent=self)

    def save_schematic(self, schem, path):
        try:
            with open(path, 'w') as f:
                schem = clone(schem.schematic)
                # remove plot curves:
                for device in schem.blocks.values():
                    device.plot_curves = []
                pickle.dump(schem, f)
                wx.MessageBox("File saved to: [{0}]".format(path))
                pth, fil = os.path.split(path)
                self.ntb_main.SetPageText(self.ntb_main.GetSelection(), fil)
                self.active_schem.name = fil

        except Exception as e:
            wx.MessageBox("File save failed. {0}".format(e.message))

    def open_schematic(self, path):
        d, name = os.path.split(path)
        f = open(path)
        sch = pickle.load(f)
        sch.name = name
        sch.path = path
        schem = SchematicWindow(frame.ntb_main, sch)
        self.schematics[name] = schem
        self.active_schem = schem
        self.ntb_main.AddPage(schem, name, select=True)

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
                chans.append(inter.Voltage(int(v.strip())))

            for i in currents.split():
                chans.append(inter.Current(i.strip()))

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
            dlg = wx.FileDialog(self,
                                message="Save Schematic As",
                                defaultFile=name,
                                wildcard=".sch",
                                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                self.save_schematic(schem, path)

    def on_save(self, event):
        schem = None
        if self.active_schem:
            schem = self.active_schem
        elif self.schematics:
            schem = self.schematics[0]

        if schem:
            if schem.path:
                self.save_schematic(schem, schem.path)
            else:
                name = schem.name
                if len(name.split(".")) > 1:
                    name = "".join(name.split(".")[:-1])
                name += ".sch"
                dlg = wx.FileDialog(self,
                                    message="Save Schematic",
                                    defaultFile=name,
                                    wildcard=".sch",
                                    style=wx.FD_SAVE)
                if dlg.ShowModal() == wx.ID_OK:
                    path = dlg.GetPath()
                    self.save_schematic(schem, path)
                    schem.path = path

    def on_add_ground(self, event):
        self.add_device("GND")

    def on_add_device(self, event):
        type_ = self.add_event_devices[event.GetId()]
        self.add_device(type_)

    def on_setup(self, event):
        self.active_schem.sim_settings = PropertyGetter.update_properties(self,
                "Simulation Setup", self.active_schem.sim_settings)

    def on_run(self, event):
        self.run()

    def on_page_close(self, event):
        index = event.GetSelection()

    def on_schem_context(self, event):
        pass

# endregion


if __name__ == '__main__':

    blocks, engines = load.import_devices("devices")

    app = wx.App()
    frame = MainFrame()
    frame.SetSize((800, 600))
    frame.SetPosition((100, 100))
    frame.new_schem()

    # debug code:
    #frame.open_schematic("/Users/josephmhood/Documents/bjt1.sch")
    #frame.open_schematic("C:/Users/josephmhood/Desktop/Cir1.sch")
    #frame.run()

    if wx.Platform == "__WXMSW__":  # if we're running on windows:
        import ctypes
        myappid = 'josephmhood.subcircuit.v01'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    frame.Show()
    app.MainLoop()