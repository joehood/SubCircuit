"""Subcircuit interface for schematic development and simulation control.

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

from __future__ import print_function, division
import pickle
import os
import sys
import math
import bdb
from copy import deepcopy as clone
from collections import OrderedDict as ODict

import wx
import wx.aui as aui
import wx.stc as stc
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure
from wx.py.editwindow import EditWindow as PyEdit
from wx.py.shell import Shell as PyShell

import subcircuit.netlist as net
import subcircuit.interfaces as inter
import subcircuit.sandbox as sb
import subcircuit.gui as gui
import subcircuit.loader as load
import subcircuit.model.param as param
from subcircuit.mathutils.pprint import equ2bmp


# region CONSTANTS

ICONFILE = "subcircuit.ico"
DEF_SCHEM_NAME = "cir{0}"

DEF_SIM_SETTINGS = ODict()
DEF_SIM_SETTINGS["dt"] = 0.001
DEF_SIM_SETTINGS["tmax"] = 0.1
DEF_SIM_SETTINGS["maxitr"] = 200
DEF_SIM_SETTINGS["tol"] = 0.00001
DEF_SIM_SETTINGS["voltages"] = ""
DEF_SIM_SETTINGS["currents"] = ""

DEF_DEVICE = "Resistor"

# endregion


# region globals:

engines = {}
blocks = {}
schematics = {}
active_schematic = None
is_windows = True

# endregion


#region Classes

class Debugger(bdb.Bdb):
    def __init__(self):
        bdb.Bdb.__init__(self)

        def user_line(self, frame):
            self.interaction(frame)

        def user_exception(self, frame, info):
            self.interaction(frame, info)

        def interaction(self, frame, info=None):
            code, lineno = frame.f_code, frame.f_lineno
            filename = code.co_filename
            basename = os.path.basename(filename)
            message = "%s:%s" % (basename, lineno)
            if code.co_name != "?":
                message = "%s: %s()" % (message, code.co_name)
            print(message)
            # sync_source_line()
            if frame and filename[:1] + filename[-1:] != "<>" and os.path.exists(filename):
                if self.gui:
                    # we may be in other thread (i.e. debugging web2py)
                    # wx.PostEvent(self.gui, DebugEvent(filename, lineno))
                    pass

            # wait user events:
            self.waiting = True
            self.frame = frame
            try:
                while self.waiting:
                    wx.YieldIfNeeded()
            finally:
                self.waiting = False
            self.frame = None


class ScriptEditor(PyEdit):
    """Subcircuit Editor"""

    def __init__(self, parent, id, script):
        """Create a new Subcircuit editor window.
        Adds to parent, and load script."""
        PyEdit.__init__(self, parent, id)
        if script:
            self.AddText(open(script).read())
        self.setDisplayLineNumbers(True)


class Interactive(PyShell):
    """Subcircuit interactive window."""

    def __init__(self, parent, id, debugger):
        """ """
        PyShell.__init__(self, parent, id)
        self.debugger = debugger

    def debug(self, code, wrkdir):
        """ """
        # save sys.stdout
        oldsfd = sys.stdin, sys.stdout, sys.stderr
        try:
            # redirect standard streams
            sys.stdin, sys.stdout, sys.stderr = self.interp.stdin, self.interp.stdout, self.interp.stderr

            sys.path.insert(0, wrkdir)

            # update the interpreter window:
            self.write('\n')

            self.debugger.run(code, locals=self.interp.locals)

            self.prompt()

        finally:
            # set the title back to normal
            sys.stdin, sys.stdout, sys.stderr = oldsfd


class PlotPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.figure = Figure()
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()

    def draw(self):
        for curve in self.curves:
            xdata, ydata, label = curve
            self.axes.plot(xdata, ydata)

    def set_data(self, curves):
        self.curves = curves


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


class BlockDropTarget(wx.TextDropTarget):
    def __init__(self, parent):
        wx.TextDropTarget.__init__(self)
        self.schematic_window = parent

    def OnDropText(self, x, y, name):
        name = self.strip_non_ascii(name).strip( )
        self.schematic_window.start_add(name, position=(x, y))
        self.schematic_window.Refresh()
        return True

    def strip_non_ascii(self, s):

        legal_chars = ([32, 40, 41, 45, 46, 58, 91, 93, 95] +
                       list(range(48, 58)) +
                       list(range(65, 91)) +
                       list(range(97, 123)))

        ascii = [c for c in s if ord(c) in legal_chars]
        return ''.join(ascii)


class SchematicWindow(wx.Panel):

    def __init__(self, parent, schematic=None, name=""):

        self.parent = parent

        self.path = ""

        if schematic:
            self.schematic = schematic
        else:
            self.schematic = sb.Schematic("Cir1")
            self.schematic.sim_settings = DEF_SIM_SETTINGS

        if name:
            self.schematic.name = name

        self.name = schematic.name
        self.blocks = schematic.blocks
        self.connectors = schematic.connectors
        self.sim_settings = schematic.sim_settings

        # init super:
        wx.Panel.__init__(self, parent)

        # set drop target so blocks can be dropped:
        self.SetDropTarget(BlockDropTarget(self))

        # must do this for double buffering:
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

        # schemetic affine matrix state:
        self.scale = 1.0
        self.rotation = 0.0
        self.translation = (0.0, 0.0)

        # during schematic/object drag. Note that this is reset after the
        # drag operation is complete.
        self.drag_translation = (0.0, 0.0)
        self.last_position = (0.0, 0.0)
        self.current_position = (0.0, 0.0)
        self.last_mouse_position = (0.0, 0.0)

        # for some reason mac needs higher mouse scroll (zoom) sensitivity
        if is_windows:
            self.scroll_sensitivity = 0.001
        else:
            self.scroll_sensitivity = 0.01

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
        if is_windows:
            self.SetDoubleBuffered(True)
        else:
            # note: don't double buffer for MAC, happens automatically
            # If you do, it will be triple-buffered and slower
            pass

        # state:
        self.netlist = None
        self.selected_objects = []
        self.active_handle = None
        self.hit_objects = []
        self.hit_blocks = []
        self.hit_ports = []
        self.hit_labels = []
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

        self.deselect_all(clean=True)

        self.netlist = None

        #if defined(__WXGTK__)

        self.SetCursor(wx.CROSS_CURSOR)

    def on_size(self, event):
        pass

    def on_dclick(self, event):
        x, y = self.logical_position(event.x, event.y)
        self.update_hit_objects((x, y))

        if self.hit_labels:
            label = self.hit_labels[0]
            old = label.properties['text']

            properties = PropertyGetter.update_properties(self,
                                                          'Label',
                                                          label.properties)
            new = properties['text']
            if not old == new:
                if new in self.blocks:
                    label.properties['text'] = old
                else:
                    self.blocks[new] = self.blocks.pop(old)
                    self.blocks[new].name = new

        elif self.hit_blocks:
            block = self.hit_blocks[0]
            label = "Properties for {0}".format(str(block))
            PropertyGetter.update_properties(self, label, block.properties)
            block.design_update()

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
            if connection.direction == sb.PortDirection.INOUT:
                self.active_connector.is_directional = False
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

        # get updated position:
        pt = self.logical_position(event.x, event.y)
        spt = pt
        if sb.SNAP_TO_GRID:
            spt = self.snap(pt)

        self.update_hit_objects(pt)

        # get key-down context:
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

        elif self.mode == sb.Mode.HANDLE:

            if self.active_handle:
                self.active_handle = None

            self.mode = sb.Mode.STANDBY

        elif self.mode == sb.Mode.ADD_BLOCK:

            self.ghost.is_ghost = False
            self.ghost = None
            self.mode = sb.Mode.STANDBY
            self.x0_object = 0.0
            self.y0_object = 0.0

        self.SetCursor(wx.Cursor(wx.CURSOR_CROSS))
        self.last_mouse_position = (event.x, event.y)
        self.last_position = spt
        self.Refresh()

    def on_left_down(self, event):

        # get updated position:
        pt = self.logical_position(event.x, event.y)
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

                elif isinstance(self.top_obj, sb.KneePoint):
                    if self.top_obj.selected:
                        self.start_connector(self.top_obj)
                        self.mode = sb.Mode.CONNECT
                    else:
                        if not multi_select:
                            self.deselect_all()
                        self.select_object(self.top_obj)

                elif isinstance(self.top_obj, sb.Handle):
                    if not multi_select:
                        self.deselect_all()
                        self.select_object(self.top_obj)
                        self.active_handle = self.top_obj
                        self.drag_translation = (0, 0)
                        self.last_position = pt
                        self.mode = sb.Mode.HANDLE

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

        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.last_mouse_position = (event.x, event.y)
        self.last_position = spt
        self.clean_up()
        self.Refresh()

    def end_floating_connector(self, pt):

        connection = sb.KneePoint(self.active_connector, pt)
        self.end_connector(connection)
        self.set_hover(connection)

    def on_right_down(self, event):

        # get updated position:
        pt = self.logical_position(event.x, event.y)
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
                self.end_floating_connector(spt)
                self.mode = sb.Mode.STANDBY
                self.deselect_all()

        self.last_mouse_position = (event.x, event.y)
        self.last_position = spt
        self.clean_up()
        self.Refresh()

    def on_motion(self, event):
        """
        1st: get position and snapped position

        :type event: wx.MouseEvent
        :return: None
        """

        # get position:
        pt = self.logical_position(event.x, event.y)
        spt = pt
        if sb.SNAP_TO_GRID:
            spt = self.snap(pt)

        x, y = spt

        # determine context:
        dragging = event.Dragging()
        leftdown = event.LeftIsDown()
        rightdown = event.RightIsDown()

        # determine hit objects:
        self.update_hit_objects(pt)
        self.remove_hover_all()

        # STATE MACHINE:

        if self.mode == sb.Mode.CONNECT:

            if sb.ORTHO_CONNECTORS:
                x0, y0 = self.active_connector.get_last_point()
                if abs(x - x0) > abs(y - y0):
                    y = y0
                else:
                    x = x0

            self.active_connector.end = (x, y)

            if self.top_obj:

                if (not isinstance(self.top_obj, sb.Port) and
                        self.hit_segments):

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
                self.ghost_knee_segment = None

        elif self.mode == sb.Mode.HANDLE:

            if self.active_handle and dragging:
                x0, y0 = self.last_position
                xm, ym = spt
                dx = xm - x0
                dy = ym - y0
                rect = self.active_handle.rect
                rect.move_handle(self.active_handle, (dx, dy))

        elif self.mode == sb.Mode.ADD_BLOCK:

            self.ghost.position = (x - 60, y - 60)

        elif self.mode == sb.Mode.STANDBY:

            if dragging and leftdown:

                if self.selected_objects:
                    self.drag_selection((event.x, event.y))
                else:
                     self.drag_schemetic((event.x, event.y))

            elif self.top_obj:
                self.set_hover(self.top_obj)

        self.last_mouse_position = (event.x, event.y)
        self.last_position = spt
        self.Refresh()

    def drag_schemetic(self, new_point):
        x, y = new_point
        x0, y0 = self.last_mouse_position
        dx, dy = (x - x0), (y - y0)
        xtrans, ytrans = self.translation
        self.translation = (xtrans + dx, ytrans + dy)

    def drag_selection(self, new_point):
        x, y = new_point
        x0, y0 = self.last_mouse_position
        dx = (x - x0) / self.scale
        dy = (y - y0) / self.scale
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

    def zoom(self, delta, center):

        scale0 = self.scale

        xc0, yc0 = self.logical_position(*center)

        self.scale += delta

        self.scale = max(sb.MIN_SCALE_FACTOR, self.scale)
        self.scale = min(sb.MAX_SCALE_FACTOR, self.scale)

        if not scale0 == self.scale:

            xc1, yc1 = self.logical_position(*center)

            xtrans, ytrans = self.translation
            xtrans += (xc1 - xc0) * self.scale
            ytrans += (yc1 - yc0) * self.scale
            self.translation = (xtrans, ytrans)

            self.Refresh()

    def on_scroll(self, event):
        delta = event.GetWheelRotation() * self.scroll_sensitivity
        self.zoom(delta, (event.x, event.y))

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
                        for connection in connector.get_connection_points():
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
        hit_handles = {}
        hit_ports = {}
        hit_labels = {}
        hit_segments = {}
        hit_knees = {}

        # determine everything that's hit:
        for block in self.blocks.values():
            if block.hittest(pt):
                hit_blocks[block.zorder] = block
            for port in block.ports.values():
                if port.hittest(pt):
                    hit_ports[port.zorder] = port
            for label in block.labels.values():
                if label.hittest(pt):
                    hit_labels[label.zorder] = label
            for rrect in block.rrects:
                for handle in rrect.handles.values():
                    if handle.hittest(pt):
                        hit_handles[handle.zorder] = handle
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

        self.hit_handles = [obj for (z, obj) in
                            reversed(sorted(hit_handles.items()))]

        self.hit_blocks = [obj for (z, obj) in
                           reversed(sorted(hit_blocks.items()))]

        self.hit_labels = [obj for (z, obj) in
                           reversed(sorted(hit_labels.items()))]

        self.hit_segments = [obj for (z, obj) in
                             reversed(sorted(hit_segments.items()))]

        self.hit_knees = [obj for (z, obj) in
                          reversed(sorted(hit_knees.items()))]

        # the order these lists are added is key:

        self.hit_objects = (self.hit_labels +
                            self.hit_ports +
                            self.hit_handles +
                            self.hit_blocks +
                            self.hit_knees +
                            self.hit_segments)

        self.hit_connection_points = (self.hit_ports + self.hit_knees)

        if self.hit_objects:
            self.top_obj = self.hit_objects[0]

    def logical_position(self, xmouse, ymouse):
        dx, dy = self.translation
        xschem = (xmouse - dx) / self.scale
        yschem = (ymouse - dy) / self.scale
        logical_position = (xschem, yschem)
        return logical_position

    def add_block(self, key, block, position):
        self.blocks[key] = block
        self.blocks[key].position = position

    def deselect_all(self, clean=False):

        for obj in self.selected_objects:
            obj.selected = False

        if clean:
            for block in self.blocks.values():
                block.selected = False
                for port in block.ports.values():
                    port.selected = False
            for connector in self.connectors:
                connector.selected = False
                for seg in connector.segments:
                    seg.selected = False
                for knee in connector.knees:
                    knee.selected = False

        self.selected_objects = []

    def start_add(self, type_=None, name=None, position=(0, 0)):

        # get the block definition from the global block dict:
        cls = blocks[type_]
        label = cls.label

        x0, y0 = position

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
        self.ghost.translate((x0 - 60, y0 - 60))
        self.SetFocus()

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
            dx = x % sb.GRID_MINOR
            dy = y % sb.GRID_MINOR
            if dx > sb.GRID_MINOR / 2:
                x += sb.GRID_MINOR - dx
            else:
                x -= dx
            if dy > sb.GRID_MINOR / 2:
                y += sb.GRID_MINOR - dy
            else:
                y -= dy
            return x, y
        else:
            return None

    def consolidate_connection_points(self):
        pass

    def auto_connect(self):
        tol = sb.GRID_MINOR / 2

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

    def draw(self, dc):

        # get logical position:
        x, y = self.last_position

        # create a graphics context from the drawing context this will help
        # us automatically manage scaling, translation and rotation:
        gc = wx.GraphicsContext.Create(self.dc)

        # translate gc:
        gc.Translate(*self.translation)

        # scale gc (always keep x and y scale synchronized):
        gc.Scale(self.scale, self.scale)

        # rotate gc:
        gc.Rotate(self.rotation)

        # render grid:
        self.draw_grid(gc)

        # shows position of the mouse as seen by the gc (for debugging):
        if sb.SHOW_MOUSE_POSITION:
            path = gc.CreatePath()
            path.AddCircle(x, y, 5)
            gc.SetBrush(wx.Brush(wx.Colour(100, 200, 100)))
            gc.FillPath(path)

        # render blocks:
        for name, block in self.blocks.items():
            self.draw_block(block, gc)

        # render connectors"
        for connector in self.connectors:
            self.draw_connector(connector, gc)

        # TODO: render primatives and drawings


        # this routine will render the hit boxes, either for all hit objects
        # or just the top hit object (for debugging)

        ALL_OBJECTS = False
        TOP_OBJECT = True

        if ALL_OBJECTS:
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

        elif TOP_OBJECT:
            if self.top_obj:
                path = gc.CreatePath()
                for rect in self.top_obj.bounding_rects:
                    if not rect == (0, 0, 0, 0):
                        x, y, w, h = rect
                        path.AddRoundedRectangle(x, y, w, h, 2)
                gc.SetPen(wx.Pen(wx.Colour(200, 100, 100), 2))
                gc.StrokePath(path)

    def draw_grid(self, gc):
        spacing = sb.GRID_MINOR
        w, h = gc.GetSize()
        dx, dy = self.translation
        pen = wx.Pen(sb.GRID_COLOR, sb.GRID_WIDTH)
        gc.SetPen(pen)

        x0, y0 = 0.0, 0.0

        w, h = w * 2.0, h * 2.0

        w -= w % spacing

        h -= h % spacing

        x, y = x0, y0

        path = gc.CreatePath()

        path.MoveToPoint(x0, y0 - h)
        while x <= (w - x0):
            path.AddLineToPoint(x, h - y0)
            x += spacing
            path.MoveToPoint(x, y0 - h)

        x = x0
        path.MoveToPoint(x0, y0 - h)
        while x >= -(w - x0):
            path.AddLineToPoint(x, h - y0)
            x -= spacing
            path.MoveToPoint(x, y0 - h)

        path.MoveToPoint(x0 - w, y0)
        while y <= (h - y0):
            path.AddLineToPoint(w - x0, y)
            y += spacing
            path.MoveToPoint(x0 - w, y)

        y = y0
        path.MoveToPoint(x0 - w, y0)
        while y >= -(h - y0):
            path.AddLineToPoint(w - x0, y)
            y -= spacing
            path.MoveToPoint(x0 - w, y)

        gc.StrokePath(path)

    def draw_block(self, block, gc):

        xb, yb = block.position

        font = wx.Font(sb.FONT_SIZE, wx.FONTFAMILY_ROMAN,
                       wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL)

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

        # main symbol path:

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

        for rrect in block.rrects:
            path.AddRectangle(rrect.x, rrect.y, rrect.w, rrect.h)

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

        # end main symbol path

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

        for key, label in block.labels.items():

            if block.is_ghost:
                gf = gc.CreateFont(font, sb.GHOST_COLOR)

            elif label.selected or block.selected:
                gf = gc.CreateFont(font, sb.SELECT_COLOR)

            elif label.hover or block.hover:
                gf = gc.CreateFont(font, sb.HOVER_COLOR)

            else:
                gf = gc.CreateFont(font, sb.DEVICE_COLOR)

            gc.SetFont(gf)

            x, y, w, h = block.bounding_rects[0]
            xo, yo = label.position
            xt, yt = x + xo, y + yo
            gc.DrawText(label.get_text(), xt, yt)
            w, h, d, e = gc.GetFullTextExtent(label.get_text())
            label.bounding_rects[0] = (xt, yt, w, h)
            label.center = (xt + w * 0.5, yt + h * 0.5)

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
                gc.SetPen(self.pen_select)
                gc.SetBrush(self.brush_select)
                gf = gc.CreateFont(font, sb.DEVICE_COLOR)
                force_show = True

            elif port.hover:
                gc.SetPen(self.pen_hover)
                gc.SetBrush(self.brush_hover)
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

            if port.anchored_rect:
                rect = port.anchored_rect
                xr0, yr0, wr0, hr0 = rect.x0, rect.y0, rect.w0, rect.h0
                xr, yr, wr, hr = rect.x, rect.y, rect.w, rect.h

                if port.anchored_align == sb.Alignment.W:
                    y *= (hr / hr0)
                    x += (xr - xr0)

                elif port.anchored_align == sb.Alignment.E:
                    x += (xr - xr0) + (wr - wr0)
                    y *= (hr / hr0)

                x, y = self.snap((x, y))

            path = gc.CreatePath()

            arrow_rotation = 0.0

            if port.direction == sb.PortDirection.INOUT:  # electrical port

                path.MoveToPoint(x, y)
                path.AddCircle(x, y, r)
            
            elif port.direction == sb.PortDirection.IN:  # signal port

                if port.block_edge == sb.Alignment.E:
                    arrow_rotation = 0.0

                elif port.block_edge == sb.Alignment.W:
                    arrow_rotation = sb.PI

                elif port.block_edge == sb.Alignment.N:
                    arrow_rotation = -sb.PI_OVER_TWO

                elif port.block_edge == sb.Alignment.S:
                    arrow_rotation = sb.PI_OVER_TWO

            elif port.direction == sb.PortDirection.OUT:

                if port.block_edge == sb.Alignment.E:
                    arrow_rotation = sb.PI

                elif port.block_edge == sb.Alignment.W:
                    arrow_rotation = 0.0

                elif port.block_edge == sb.Alignment.N:
                    arrow_rotation = sb.PI_OVER_TWO

                elif port.block_edge == sb.Alignment.S:
                    arrow_rotation = -sb.PI_OVER_TWO


            if port.direction in (sb.PortDirection.IN, sb.PortDirection.OUT):

                arrow_angle = sb.PI_OVER_FOUR
                arrow_size = 10

                ang0 = arrow_rotation - arrow_angle
                ang1 = arrow_rotation + arrow_angle

                x0 = x + arrow_size * math.cos(ang0)
                y0 = y + arrow_size * math.sin(ang0)
                x1 = x + arrow_size * math.cos(ang1)
                y1 = y + arrow_size * math.sin(ang1)

                path.MoveToPoint(x0, y0)
                path.AddLineToPoint(x, y)
                path.AddLineToPoint(x1, y1)

            # transform this path to the blocks affine matrix:
            path.Transform(matrix)

            if len(port.connectors) > 1 or force_show:

                if (port.direction == sb.PortDirection.IN
                   or port.direction == sb.PortDirection.OUT):
                    gc.StrokePath(path)
                else:
                    gc.FillPath(path)

            path.Destroy()

            path = gc.CreatePath()
            path.MoveToPoint(x, y)
            path.AddRectangle(x - r - m, y - r - m, (r + m) * 2, (r + m) * 2)
            path.Transform(matrix)
            port.bounding_rects[0], port.center = self.get_bounding(path)
            path.Destroy()

        for rrect in block.rrects:

            for handle in rrect.handles.values():

                force_show = False

                if block.is_ghost:
                    gc.SetPen(self.pen_ghost)
                    gc.SetBrush(self.brush_ghost)
                    force_show = True

                elif block.selected:
                    gc.SetPen(self.pen_select)
                    gc.SetBrush(self.brush_select)
                    force_show = True

                elif handle.selected:
                    gc.SetPen(self.pen_select)
                    gc.SetBrush(self.brush_select)
                    force_show = True

                elif handle.hover:
                    gc.SetPen(self.pen_select)
                    gc.SetBrush(self.brush_select)
                    force_show = True

                elif block.hover:
                    gc.SetPen(self.pen_hover)
                    gc.SetBrush(self.brush_hover)
                    force_show = True

                else:
                    gc.SetPen(self.pen)
                    gc.SetBrush(self.brush)
                    force_show = False

                path = gc.CreatePath()

                x, y = handle.position
                s, m = sb.HANDLE_SIZE, sb.HANDLE_HIT_MARGIN

                # draw handle square:

                path = gc.CreatePath()
                path.MoveToPoint(x, y)
                path.AddRectangle(x - s/2, y - s/2, s, s)
                path.Transform(matrix)

                if force_show:
                    # gc.StrokePath(path)
                    gc.FillPath(path)

                path.Destroy()

                # create hit-testing box:

                path = gc.CreatePath()

                path.AddRectangle(x - s/2 - m, y - s/2 - m,
                                  (s/2 + m) * 2, (s/2 + m) * 2)

                path.Transform(matrix)
                handle.bounding_rects[0], handle.center = self.get_bounding(path)
                path.Destroy()

        for field in block.fields:

            font = wx.Font(field.size, wx.FONTFAMILY_ROMAN,
                           wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False)

            gcfont = gc.CreateFont(font, sb.DEVICE_COLOR)
            gc.SetFont(gcfont)

            xb, yb = self.snap(block.position)
            xf, yf = field.position

            if field.rect_anchor:
                if field.rect_align == sb.Alignment.CENTER:
                    xf = xf * field.rect_anchor.w / field.rect_anchor.w0
                    yf = yf * field.rect_anchor.h / field.rect_anchor.h0
                    xf = xf + field.rect_anchor.x0 + field.rect_anchor.x
                    yf = yf + field.rect_anchor.y0 + field.rect_anchor.y

            xt, yt = xb + xf, yb + yf

            w, h, d, e = gc.GetFullTextExtent(field.text)

            if field.align == sb.Alignment.NW:
                pass

            elif field.align == sb.Alignment.N:
                xt -= w / 2

            elif field.align == sb.Alignment.NE:
                xt -= w

            elif field.align == sb.Alignment.W:
                yt -= h / 2

            elif field.align == sb.Alignment.CENTER:
                xt -= w / 2
                yt -= h / 2

            elif field.align == sb.Alignment.E:
                xt -= w
                yt -= h / 2

            elif field.align == sb.Alignment.SW:
                yt -= h

            elif field.align == sb.Alignment.S:
                xt -= w / 2
                yt -= h

            elif field.align == sb.Alignment.SE:
                xt -= w
                yt -= h

            gc.DrawText(field.text, xt, yt)

            field.bounding_rects[0] = (xt, yt, w, h)
            field.center = (xt + w * 0.5, yt + h * 0.5)

        for ratio in block.ratios:

            # font = wx.Font(ratio.size, wx.FONTFAMILY_DEFAULT,
            #                wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False,
            #                "Courier 10 Pitch")
            #
            # gcfont = gc.CreateFont(font, sb.DEVICE_COLOR)
            # gc.SetFont(gcfont)

            xb, yb = self.snap(block.position)
            xf, yf = ratio.position

            if ratio.rect_anchor:
                if ratio.rect_align == sb.Alignment.CENTER:
                    xf = xf * ratio.rect_anchor.w / ratio.rect_anchor.w0
                    yf = yf * ratio.rect_anchor.h / ratio.rect_anchor.h0
                    xf = xf + ratio.rect_anchor.x0 + ratio.rect_anchor.x
                    yf = yf + ratio.rect_anchor.y0 + ratio.rect_anchor.y


            bmp = block.bmp

            m = 5

            we, he = bmp.GetSize()

            xr, yr = ratio.rect_anchor.x, ratio.rect_anchor.y
            wr, hr = ratio.rect_anchor.w, ratio.rect_anchor.h

            we2 = min(we, wr - m * 2)
            he *= (we2 / we)
            he2 = min(he, hr - m * 2)
            we2 *= (he2 / he)

            if ratio.align == sb.Alignment.CENTER:
                xf = xb + wr / 2 - we2 / 2
                yf = yb + hr / 2 - he2 / 2

            gc.DrawBitmap(bmp, xf, yf, we2, he2)

            # num = unicode_print(ratio.numerator)
            # den = unicode_print(ratio.denominator)
            #
            # wn, hn, dn, en = gc.GetFullTextExtent(num)
            # wd, hd, dd, ed = gc.GetFullTextExtent(den)

            # xn, yn = xb + xf, yb + yf
            #
            # xd, yd = xb + xf, yb + hn * 2 + yf
            #
            # if ratio.align == sb.Alignment.NW:
            #     pass
            #
            # elif ratio.align == sb.Alignment.N:
            #     xn -= wn / 2
            #     xd -= wd / 2
            #
            # elif ratio.align == sb.Alignment.NE:
            #     xn -= wn
            #     xd -= wd
            #
            # elif ratio.align == sb.Alignment.W:
            #     yn -= hn / 2
            #     yd -= hd / 2
            #
            # elif ratio.align == sb.Alignment.CENTER:
            #     xn -= wn / 2
            #     yn -= hn / 2
            #     xd -= wd / 2
            #     yd -= hd / 2
            #
            # elif ratio.align == sb.Alignment.E:
            #     xn -= wn
            #     yn -= hn / 2
            #     xd -= wd
            #     yd -= hd / 2
            #
            # elif ratio.align == sb.Alignment.SW:
            #     yn -= hn
            #     yd -= hd
            #
            # elif ratio.align == sb.Alignment.S:
            #     xn -= wn / 2
            #     yn -= hn
            #     xd -= wd / 2
            #     yd -= hd
            #
            # elif ratio.align == sb.Alignment.SE:
            #     xn -= wn
            #     yn -= hn
            #     xd -= wd
            #     yd -= hd

            # gc.DrawText(num, xn, yn - hn)
            # gc.DrawText(den, xd, yd - hn)
            # yline = yn + 0.5 * hn
            # xline1 = min(xn, xd)
            # xline2 = max(xn + wn, xd + wd)
            # gc.DrawLines([(xline1, yline), (xline2, yline)])
            #
            # ratio.bounding_rects[0] = (xn, yn, wn, hn)
            # ratio.center = (xn + wn * 0.5, yn + hn * 0.5)

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

        if connector.is_directional:
            if connector.partial:
                connector.update_arrow(connector.end)
            else:
                p1, p2 = connector.segments[-1]
                connector.update_arrow(self.snap(p2))
            p1, p2, p3 = connector.arrow
            path.MoveToPoint(p1)
            path.AddLineToPoint(p2)
            path.AddLineToPoint(p3)

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

    def build_netlist(self):

        groups = [[], ]

        connector_groups = []

        # first, make groups of all the connected connectors
        connector_groups = []
        for connector in self.connectors:
            grp = []
            for connection in connector.get_connection_points():
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

        # now build the netlist:

        netlist = net.Netlist(self.name)

        engine2block = {}

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
                    engine = block.get_engine(nodes)
                    engine2block[engine] = block
                    netlist.device(block.name, engine)
                    if isinstance(engine, inter.SignalDevice):
                        pass

        # now setup references for signal propagation:

        nodeports = {}

        for key, node in netlist.nodes.items():
            nodeports[node] = []
            for device in netlist.devices.values():
                for port, node2 in device.port2node.items():
                    if node == node2:
                        nodeports[node].append((device, port))

        for node, ports in nodeports.items():

            for device1, port1 in ports:
                port2port = {}
                block = engine2block[device1]
                for blockport in block.ports.values():
                    if blockport.index == port1:
                        if blockport.direction == sb.PortDirection.OUT:
                            port2port[port1] = []
                            for device2, port2 in ports:
                                port2port[port1].append((device2, port2))
                device1.port2port = port2port

        return netlist

    def get_netlist_code(self, name, netlist_mod_name=None):

        netlist = self.build_netlist()

        code = ""
        if netlist_mod_name:
            code += '{0} = {1}.Netlist("{0}")'.format(name, netlist_mod_name)
        else:
            code += '{0} = Netlist("{0}")'.format(name)
        for dname, device in netlist.devices.items():
            code += '\n{0}.device("{1}", {2})'.format(name, dname,
                                                  device.get_code_string())
        return code


class DeviceTree(wx.TreeCtrl):
    def __init__(self, parent, blocks):

        style = (wx.TR_FULL_ROW_HIGHLIGHT |
                 wx.TR_HAS_BUTTONS |
                 wx.TR_HIDE_ROOT |
                 wx.TR_HAS_VARIABLE_ROW_HEIGHT)

        wx.TreeCtrl.__init__(self, parent, style=style)
        self.blocks = blocks

        #for name, device_type in self.devices.items():
        self.root = self.AddRoot("Library")
        self.root.device_type = None

        images = load.get_block_thumbnails(blocks, width=5)
        images_sel = images.copy()

        w, h = 36, 36

        imagelist = wx.ImageList(w, h)
        self.imagemap = {}

        for name in images:
            image = images[name].Scale(w, h, wx.IMAGE_QUALITY_BICUBIC)
            image_sel = images_sel[name].Scale(w, h, wx.IMAGE_QUALITY_BICUBIC)
            self.imagemap[name] = (
                imagelist.Add(image.ConvertToBitmap()),
                imagelist.Add(image_sel.ConvertToBitmap()))

        self.AssignImageList(imagelist)

        famnodes = {}

        for name, device_type in self.blocks.items():
            family = device_type.family
            if not family in famnodes:
                famnodes[family] = self.AppendItem(self.root, family)
                famnodes[family].device_type = None
            if name in self.imagemap:
                index, index_sel = self.imagemap[name]
            else:
                index, index_sel = -1, -1
            item = self.AppendItem(famnodes[family], name, index, index_sel)
            self.SetItemData(item, name)


        # bindings:
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.on_begin_drag)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_selection_changed)

        self.selected_item = None

        self.ExpandAll()

    def on_begin_drag(self, event):
        if self.selected_item:
            name = self.GetItemData(self.selected_item)
            drag_source = wx.DropSource(self)
            dataobj = wx.TextDataObject(name)
            dataobj.device_type = name
            drag_source.SetData(dataobj)
            drag_source.DoDragDrop(True)

    def on_selection_changed(self, event):
        self.selected_item = event.GetItem()


class MainFrame(gui.MainFrame):

    def __init__(self, redirect=False):

        global schematics, active_schematic

        # call super:

        gui.MainFrame.__init__(self, None)

        self.imagelist = wx.ImageList(16, 16)

        image = wx.Image("./artwork/pylogo16.gif", wx.BITMAP_TYPE_GIF)
        self.pylogo16 = self.imagelist.Add(image.ConvertToBitmap())

        image = wx.Image("./artwork/pytext16.png", wx.BITMAP_TYPE_PNG)
        self.pytext16 = self.imagelist.Add(image.ConvertToBitmap())

        image = wx.Image("./artwork/schem16.png", wx.BITMAP_TYPE_PNG)
        self.schem16 = self.imagelist.Add(image.ConvertToBitmap())

        image = wx.Image("./artwork/chip16.png", wx.BITMAP_TYPE_PNG)
        self.chip16 = self.imagelist.Add(image.ConvertToBitmap())

        self.ntb_left.SetImageList(self.imagelist)
        self.ntb_editor.SetImageList(self.imagelist)
        self.ntb_bottom.SetImageList(self.imagelist)

        icon = wx.Icon("subcircuit.ico")
        self.SetIcon(icon)

        self.SetTitle("SubCircuit")

        # application icon:

        icon = wx.Icon(ICONFILE, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        # schematic setup:

        self.schematics = {}
        schematics = self.schematics
        self.schcnt = 1
        self.active_schem = None
        active_schematic = self.active_schem
        self.active_script = None

        # param table(s):
        self.param_table = None

        # additional bindings (others are in gui.py):

        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSED, self.on_page_close,
                  self.ntb_editor)

        self.Bind(aui.EVT_AUINOTEBOOK_TAB_RIGHT_DOWN, self.on_schem_context,
                  self.ntb_editor)

        # add all loaded devices to the window:

        self.menu_blocks = wx.Menu()

        self.add_event_devices = {}

        self.blocks, self.engines = load.import_devices("devices")

        blocks_by_family = {}

        for key, block in self.blocks.items():
            if not block.family in blocks_by_family:
                blocks_by_family[block.family] = {}
            blocks_by_family[block.family][key] = block

        for family, famblocks in blocks_by_family.items():
            sub_menu = wx.Menu()
            for key, block in famblocks.items():
                event_id = wx.NewIdRef()
                item = wx.MenuItem(sub_menu, event_id, key)
                sub_menu.Append(item)
                self.Bind(wx.EVT_MENU, self.on_add_device, id=event_id)
                self.add_event_devices[event_id] = key

            self.menu_blocks.AppendSubMenu(sub_menu, family)

        self.menu.Append(self.menu_blocks, "Blocks")

        # interactive window:

        self.debugger = Debugger()
        self.szr_shell = wx.BoxSizer(wx.VERTICAL)
        self.pnl_shell = wx.Panel(self.ntb_bottom)
        self.pnl_shell.SetSizer(self.szr_shell)
        self.interactive = Interactive(self.pnl_shell, 0, self.debugger)
        self.szr_shell.Fit(self.pnl_shell)
        self.szr_shell.Add(self.interactive, 1, wx.EXPAND)

        self.ntb_bottom.SetImageList(self.imagelist)
        self.ntb_bottom.AddPage(self.pnl_shell, " Interactive", True,
                                self.pylogo16)

        pystyle = self.interactive.GetStyleAt(0)

        self.interactive.SelectAll()
        start, end = self.interactive.GetSelection()
        text = self.interactive.GetSelectedText()
        lines = text.split("\n")[:3]
        self.interactive.push("from subcircuit.netlist import Netlist",
                              silent=False)

        stc.StyledTextCtrl.ClearAll(self.interactive)
        pyver = sys.version
        self.interactive.AddText("\nPython {0}\n".format(pyver.replace("\n",
                                                                       " ")))

        self.interactive.StartStyling(self.interactive.GetLastPosition(), 0)
        self.interactive.push("\n")  # force imput prompt

        if redirect:
            sys.stdout = self.interactive
            sys.stderr = self.interactive

        load.load_engines_to_module(sys.modules[__name__])

        # device tree:

        self.szr_tree = wx.BoxSizer(wx.VERTICAL)
        self.pnl_tree = wx.Panel(self.ntb_left)
        self.pnl_tree.SetSizer(self.szr_tree)

        self.device_tree = DeviceTree(self.pnl_tree, self.blocks)

        self.szr_tree.Fit(self.pnl_tree)
        self.szr_tree.Add(self.device_tree, 1, wx.EXPAND | wx.ALL)

        self.ntb_left.SetImageList(self.imagelist)
        self.ntb_left.AddPage(self.pnl_tree, " Devices", True, self.chip16)

        self.statusbar.SetStatusText("Ready")

        self.Refresh()

    def new_schem(self, name=None):
        global active_schematic
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
                    name = DEF_SCHEM_NAME.format(self.schcnt) + ".sch"
        self.schcnt += 1
        sch = sb.Schematic(name)
        sch.sim_settings = DEF_SIM_SETTINGS
        schem = SchematicWindow(subcircuit.ntb_editor, sch)

        paramlist = sch.parameters
        self.param_table = param.ParameterTable(subcircuit.ntb_editor, paramlist)

        self.ntb_editor.AddPage(schem, "Schematic", True, self.schem16)
        self.ntb_editor.AddPage(self.param_table, "Parameters", False, self.schem16)

        self.schematics[name] = schem
        self.active_schem = schem
        active_schematic = self.active_schem
        schem.path = None

        wx.SafeYield()

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
                sch = schem.schematic.clone()
                paramlist = self.param_table.paramlist
                sch.parameters = paramlist
                # remove plot curves:
                for device in sch.blocks.values():
                    device.plot_curves = []
                    try:
                        device.bmp = None
                    except:
                        pass
                pickle.dump(sch, f)
                wx.MessageBox("File saved to: [{0}]".format(path))
                pth, file_ = os.path.split(path)
                self.ntb_editor.SetPageText(self.ntb_editor.GetSelection(),
                                            file_)
                self.active_schem.name = file_

        except Exception as e:
            wx.MessageBox("File save failed. {0}".format(e.message))

    def open_schematic(self, path):
        global active_schematic
        d, name = os.path.split(path)
        f = open(path)
        sch = pickle.load(f)
        sch.name = name
        sch.path = path
        schem = SchematicWindow(subcircuit.ntb_editor, sch)
        self.schematics[name] = schem
        self.active_schem = schem

        for block in self.active_schem.blocks.values():
            block.design_update()

        paramlist = sch.parameters
        self.param_table = param.ParameterTable(subcircuit.ntb_editor, paramlist)

        self.ntb_editor.AddPage(schem, "Block Diagram", True, self.schem16)
        self.ntb_editor.AddPage(self.param_table, "Parameters", False, self.schem16)

    def run(self):
        if self.active_schem:
            self.netlist = self.active_schem.build_netlist()

            settings = self.active_schem.sim_settings

            dt = settings['dt']
            tmax = settings['tmax']
            maxitr = settings['maxitr']
            tol = settings['tol']
            voltages = settings['voltages']
            currents = settings['currents']

            self.netlist.trans(dt, tmax)

            for block in self.active_schem.blocks.values():
                block.end()

            chans = []

            for v in voltages.split():
                chans.append(inter.Voltage(int(v.strip())))

            for i in currents.split():
                chans.append(inter.Current(i.strip()))

            self.netlist.plot(*chans)

            self.active_schem.Refresh()

    def gen_netlist(self, schem):

        name = schem.name.split(".")[0]

        header = "\n"

        header += "# Auto-generated netlist from schematic: {0}\n\n"
        header += "from subcircuit.netlist import Netlist, import_devices\n"
        header += "from subcircuit.stimuli import Sin, Pulse, Pwl, Exp\n"
        header += "from subcircuit.interfaces import Voltage, Current\n\n"
        header += "import_devices()\n\n"
        header += "# Netlist Definition:\n"

        code = header.format(schem.name)

        code += schem.get_netlist_code(name)

        code += "\n\n# Simulation:\n"

        settings = self.active_schem.sim_settings.values()
        (dt, tmax, maxitr, tol, voltages, currents) = settings

        code += "{0}.trans({1}, {2})\n\n".format(name, dt, tmax)

        voltplots = ""
        for volt in voltages.split(" "):
            voltplots += "Voltage({0}),".format(volt)

        currplots = ""
        for curr in currents.split(" "):
            currplots += 'Current("{0}"),'.format(curr)

        if voltages or currents:
            code += "{0}.plot({1}, {2})".format(name, voltplots.strip(","),
                                                currplots.strip(","))

        # add interactive window:
        script = PyEdit(self.ntb_editor)
        script.AddText(code)

        self.ntb_editor.AddPage(script, name + ".py", True, self.pytext16)

        self.active_script = script

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

    def on_run_script(self, event):
        if self.active_script:
            print("Runnning active script...".format())
            code = self.active_script.GetText()
            for line in code.split("\n"):
                if line:
                    self.interactive.push(line)
            print("Complete.")

    def on_page_close(self, event):
        index = event.GetSelection()

    def on_schem_context(self, event):
        pass

    def on_gen_netlist(self, event):
        self.gen_netlist(self.active_schem)


class SubCircuitApp(wx.App):
    def __init__(self):
        wx.App.__init__(self)
        #self.Bind(wx.EVT_ACTIVATE, self.on_activate)

    def on_activate(self, event):
        self.GetTopWindow().Raise()


# endregion


if __name__ == '__main__':

    is_windows = wx.Platform == "__WXMSW__"

    os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

    blocks, engines = load.import_devices("devices")

    app = SubCircuitApp()

    subcircuit = MainFrame(redirect=False)
    subcircuit.SetSize((1000, 600))
    subcircuit.SetPosition((100, 100))
    subcircuit.new_schem()

    if is_windows:
        import ctypes
        myappid = 'josephmhood.subcircuit.v01'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    subcircuit.Show()
    app.MainLoop()