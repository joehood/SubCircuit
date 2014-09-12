from __future__ import print_function
import wx
import wx.aui
from pyspyce import *
from interfaces import *
from devices import *
from simulator import *
import gui
import pickle
import sys, os
from collections import OrderedDict as odict


# region Constants

BG_COLOR = wx.Colour(40, 120, 40)
GRID_COLOR = wx.Colour(60, 140, 60)
DEVICE_COLOR = wx.Colour(200, 200, 200)
SELECT_COLOR = wx.Colour(255, 255, 255)
HOVER_COLOR = wx.Colour(255, 255, 255)
LINE_WIDTH = 3
SELECT_WIDTH = 6
HOVER_WIDTH = 3
GRID_SIZE = 20
GRID_WIDTH = 1
SHOW_CROSSHAIR = False
MOVE_DELTA = GRID_SIZE
GHOST_COLOR = GRID_COLOR
DEF_DEVICE = "R"

# endregion


class SchematicObject(object):
    def __init__(self):
        self.position = 0, 0
        self.rotation = 0
        self.hor_flip = False
        self.ver_flip = False
        self.scale = 1.0
        self.selected = False
        self.bounding_rect = (0, 0, 0, 0)
        self.center = (0, 0)
        self.hover = False
        self.selected = False

    def translate(self, delta):
        x, y = self.position
        dx, dy = delta
        self.position = x + dx, y + dy
        if self.bounding_rect:
            x, y, w, h = self.bounding_rect
            self.bounding_rect = (x + dx, y + dx, w, h)

    def hittest(self, point):
        x, y = point
        x1, y1, w, h = self.bounding_rect
        x2 = x1 + w
        y2 = y1 + h
        if x1 < x < x2 and y1 < y < y2:
            return True
        else:
            return False


class Port(SchematicObject):
    def __init__(self, block, index, position, is_ground=False):
        SchematicObject.__init__(self)
        self.index = index
        self.node = None
        self.position = position
        self.connectors = {}
        self.block = block
        self.radius = 4
        self.hit_margin = 4
        self.connected = False
        self.is_ground = is_ground

    def __str__(self):
        return "{0}:{1}".format(self.block, self.index)

    def __repr__(self):
        return str(self)


class Joint(SchematicObject):
    def __init__(self):
        SchematicObject.__init__(self)
        self.port = None
        self.segment = None
        self.location = 0


class Connector(SchematicObject):
    def __init__(self, start):
        SchematicObject.__init__(self)

        self.sandbox = None
        self.start = start
        self.end = start
        self.partial = True
        self.knees = []
        self.hover = False
        self.selected = False
        self.ports = []
        self.end_port = None
        self.start_port = None

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


class Block(SchematicObject):
    def __init__(self, name, engine, is_ground=False):
        SchematicObject.__init__(self)
        self.name = name
        self.ports = {}
        self.properties = {}
        self.outputs = {}
        self.lines = []
        self.circles = []
        self.is_ghost = False
        self.is_ground = is_ground
        self.engine = engine

    def get_engine(self, nodes):
        raise NotImplementedError()

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
        self.properties['resistance'] = 1.0

        # resistor shape:
        self.lines.append(((50, 0),(50, 20),(35, 25),(65, 35),(35, 45),
                           (65, 55),(35, 65),(65, 75),(50, 80),(50, 100)))

    def get_engine(self, nodes):
        return R(nodes, self.properties['resistance'])


class CBlock(Block):
    def __init__(self, name):

        # init super:
        Block.__init__(self, name, C)

        # ports:
        self.ports['positive'] = Port(self, 0, (50, 0))
        self.ports['negative'] = Port(self, 1, (50, 100))

        # properties:
        self.properties['capacitance'] = 1.0

        # leads:
        self.lines.append(((50, 0), (50, 40)))
        self.lines.append(((50, 60), (50, 100)))

        # plates:
        self.lines.append(((30, 40), (70, 40)))
        self.lines.append(((30, 60), (70, 60)))

    def get_engine(self, nodes):
        return C(nodes, self.properties['capacitance'])


class VBlock(Block):
    def __init__(self, name):

        # init super:
        Block.__init__(self, name, V)

        # ports:
        self.ports['positive'] = Port(self, 0, (50, 0))
        self.ports['negative'] = Port(self, 1, (50, 100))

        # properties:
        self.properties['voltage'] = 1.0

        # leads:
        self.lines.append(((50, 0), (50, 25)))
        self.lines.append(((50, 75), (50, 100)))

        # plus:
        self.lines.append(((50, 33), (50, 43)))
        self.lines.append(((45, 38), (55, 38)))

        # circle
        self.circles.append((50, 50, 25))

    def get_engine(self, nodes):
        return V(nodes, self.properties['voltage'])


class GndBlock(Block):
    def __init__(self, name):

        # init super:
        Block.__init__(self, name, None, is_ground=True)
        self.is_ground = True

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


# device type name to class mapping:
DEVICELIB = dict(R=RBlock, C=CBlock, V=VBlock, GND=GndBlock)


class Mode(object):
    DISARMED = 0
    STANDBY = 1
    CONNECT = 2
    MOVE = 3
    EDIT = 4
    ADD_DEVICE = 5


class Schematic(object):
    def __init__(self, name):
        self.name = name
        self.blocks = {}
        self.connectors = []


class SchematicWindow(wx.Panel):
    def __init__(self, parent, schematic=None, name=""):

        if schematic:
            self.schematic = schematic
        else:
            self.schematic = Schematic("Cir1")

        if name:
            self.schematic.name = name

        self.name = schematic.name
        self.blocks = schematic.blocks
        self.connectors = schematic.connectors

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
            name = "{0}{1}".format(type_, self.new_counter)
            while name in self.blocks:
                self.new_counter += 1
                name = "{0}{1}".format(type_, self.new_counter)

        self.ghost = DEVICELIB[type_](name)
        self.mode = Mode.ADD_DEVICE
        self.new_counter += 1
        self.blocks[name] = self.ghost
        self.ghost.is_ghost = True
        self.ghost.translate((-50, -50))
        self.SetFocus()

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
            for name, block in self.blocks.items():
                for name, port in block.ports.items():
                    if port.hittest(pt):
                        port_hit = True
                        port.selected = True
                        self.mode = Mode.CONNECT
                        port_pt = port.center
                        connector = Connector(port_pt)
                        connector.add_port(port)
                        connector.start_port = port
                        self.connectors.append(connector)
                        self.active_connector = connector
                    else:
                        port.selected = False
                if block.hittest(pt) and not port_hit and not self.drug:
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
            if not (port_hit or block_hit):
                self.deselect_all()

        elif self.mode == Mode.CONNECT:
            port_hit = False
            for name, block in self.blocks.items():
                for name, port in block.ports.items():
                    if port.hittest(pt):
                        port_hit = True
                        port.selected = True
                        self.mode = Mode.STANDBY
                        port_pt = port.center
                        self.active_connector.end = port_pt
                        self.active_connector.add_port(port)
                        self.active_connector.end_port = port
                        self.active_connector = None
                    else:
                        port.selected = False
            if not port_hit:
                self.active_connector.add_knee(pt)

        elif self.mode == Mode.ADD_DEVICE:
            pass


        self.Refresh()

    def on_motion(self, event):
        self.update_position(event)
        drag = event.Dragging()
        left = event.LeftIsDown()

        if drag:
            self.drug = True

        if self.mode == Mode.ADD_DEVICE:
            dx_object = (event.x - self.x0_object) / self.scale
            dy_object = (event.y - self.y0_object) / self.scale
            self.x0_object = event.x
            self.y0_object = event.y

            assert self.ghost is not None
            self.ghost.translate((dx_object, dy_object))

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
                self.Refresh()
            else:  # moving but not dragging:
                hit = False
                pt = self.x, self.y
                for block in self.blocks.values():
                    for port in block.ports.values():
                        if port.hittest(pt):
                            port.hover = True
                            hit = True
                        else:
                            port.hover = False
                    if block.hittest(pt) and not hit:
                        block.hover = True
                        hit = True
                    else:
                        block.hover = False
                if self.mode == Mode.CONNECT:
                    self.active_connector.end = pt
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

        elif code == wx.WXK_DELETE:
            for obj in self.selected_objects:
                if isinstance(obj, Block):
                    to_del = None
                    for name, block in self.blocks.items():
                        if obj is block:
                            to_del = name
                    if to_del:
                        del self.blocks[to_del]

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
            offset = i * spacing - extension/2
            gc.StrokeLine(offset, 0 - extension/2, offset, h)
        for i in range(hor):
            offset = i * spacing - extension/2
            gc.StrokeLine(0 - extension/2, offset, w, offset)

    def get_bounding(self, path):
        rect = path.GetBox()
        x, y = rect.GetLeftTop()
        w, h = rect.GetSize()
        bounding = (x, y, w, h)
        center = rect.GetCentre()
        return bounding, center

    def render_block(self, block, gc):
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

        x, y = block.position
        matrix = gc.CreateMatrix()
        matrix.Translate(x, y)
        path = gc.CreatePath()

        for line in block.lines:
            path.MoveToPoint(line[0])
            for point in line[1:]:
                x2, y2 = point
                path.AddLineToPoint(x2, y2)

        for circle in block.circles:
            path.AddCircle(*circle)

        path.Transform(matrix)
        gc.StrokePath(path)

        block.bounding_rect, block.center = self.get_bounding(path)

        for name, port in block.ports.items():

            if block.is_ghost:
                gc.SetPen(self.pen_ghost)
                gc.SetBrush(self.brush_ghost)
            elif block.selected:
                gc.SetPen(self.pen_select)
                gc.SetBrush(self.brush_select)
            elif port.selected:
                gc.SetPen(self.pen)
                gc.SetBrush(self.brush)
            elif port.hover or block.hover:
                gc.SetPen(self.pen_hover)
                gc.SetBrush(self.brush_hover)
            else:
                gc.SetPen(self.pen)
                gc.SetBrush(self.brush)

            (x, y), r, m = port.position, port.radius, port.hit_margin
            path = gc.CreatePath()
            path.MoveToPoint(x, y)
            path.AddCircle(x, y, r)
            path.Transform(matrix)
            gc.StrokePath(path)
            gc.FillPath(path)
            path = gc.CreatePath()
            path.AddRectangle(x-r-m, y-r-m, (r + m)*2, (r + m)*2)
            path.Transform(matrix)
            port.bounding_rect, port.center = self.get_bounding(path)

    def render_connector(self, connector, gc):

        connector.start = connector.start_port.center
        if connector.end_port:
            connector.end = connector.end_port.center

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

        path.MoveToPoint(connector.start)

        for knee in connector.knees:
            x2, y2 = knee
            path.AddLineToPoint(x2, y2)

        path.AddLineToPoint(connector.end)

        gc.StrokePath(path)

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

        groups = [[],]

        for connector in self.connectors:
            start = connector.start_port
            end = connector.end_port

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
        self.ntb_main.AddPage(schem, name)
        self.schcnt += 1
        self.schematics[name] = schem
        self.active_schem = schem
        return schem

    def add_device(self, type_):
        if self.active_schem:
            self.active_schem.start_add(type_)

    def save_schematic(self, schem, path):
        f = open(path, 'w')
        pickle.dump(schem.schematic, f)

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
        netlist.trans(0.1, 1)
        netlist.plot(Current('V4'))

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

    def on_save(self, event):
        schem = None
        if self.active_schem:
            schem = self.active_schem
        elif self.schematics:
            schem = self.schematics[0]

        if schem:
            name = "{0}.sch".format(schem.name)
            dlg = wx.FileDialog(self, message="Save Schematic",
                                defaultFile=name,
                                wildcard="*.sch",
                                style=wx.FD_SAVE)

            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                self.save_schematic(schem, path)

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

    def on_add_I(self, event):
        self.add_device("I")

    def on_setup(self, event):
        event.Skip()

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
    #frame.new_schem()

    frame.open_schematic("/Users/josephmhood/Documents/Cir1.sch")
    frame.run()

    # sch1 = frame.new_schematic("circuit1")
    #
    # netlist = Netlist("Test")
    #
    # sch1.add_block('r1', RBlock(), (200, 100))
    # netlist.device('r1', R((1, 0), 10.0))
    #
    # sch1.add_block('v1', VBlock(), (100, 100))
    # netlist.device('v1', V((1, 0), 100.0))
    #
    # sch1.add_block('g1', GndBlock(), (100, 220))
    #
    # netlist.trans(0.1, 1.0)
    # netlist.plot(Voltage(1), Current('v1'))

    frame.Show()
    app.MainLoop()

# endregion