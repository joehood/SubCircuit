"""Generic graphical sandbox for laying out blocks with connectors.
"""

import math

import inspect
from collections import OrderedDict as ODict
from copy import deepcopy
from copy import copy

import wx


# region Constants

DARKMODE = True

if DARKMODE:

    BG_COLOR = wx.Colour(20, 20, 20)
    FG_COLOR = wx.Colour(210, 210, 210)
    GRID_COLOR = wx.Colour(40, 40, 40)
    DEVICE_COLOR = wx.Colour(210, 210, 210)
    SELECT_COLOR = wx.Colour(255, 255, 255)
    HOVER_COLOR = wx.Colour(200, 200, 200)
    GHOST_COLOR = wx.Colour(150, 150, 150)
    SCOPE_BG = wx.Colour(100, 100, 100)
    SCOPE_FG = wx.Colour(0, 100, 0)
    SCOPE_CURVE = wx.Colour(100, 200, 100)

else:

    BG_COLOR = wx.Colour(255, 255, 255)
    FG_COLOR = wx.Colour(0, 0, 0)
    GRID_COLOR = wx.Colour(230, 230, 230)
    DEVICE_COLOR = wx.Colour(0, 0, 0)
    SELECT_COLOR = wx.Colour(0, 0, 0)
    HOVER_COLOR = wx.Colour(0, 0, 0)
    GHOST_COLOR = wx.Colour(150, 150, 150)
    SCOPE_BG = wx.Colour(200, 200, 200)
    SCOPE_FG = wx.Colour(255, 255, 255)
    SCOPE_CURVE = wx.Colour(100, 200, 100)

LINE_WIDTH = 1
SELECT_WIDTH = 4
HOVER_WIDTH = 3
GRID_MAJOR = 40
GRID_MINOR = 10
GRID_WIDTH = 1
FONT_SIZE = 14

MOVE_DELTA = GRID_MINOR
CONNECTOR_HIT_MARGIN = 10
PORT_HIT_MARGIN = 5
PORT_RADIUS = 3
HANDLE_HIT_MARGIN = 10
HANDLE_SIZE = 8

SHOW_MOUSE_POSITION = False
ORTHO_CONNECTORS = False
SNAP_TO_GRID = True

MIN_SCALE_FACTOR = 0.5
MAX_SCALE_FACTOR = 100.0

PI = math.pi
TWO_PI = math.pi * 2
PI_OVER_TWO = math.pi * 0.5
PI_OVER_THREE = math.pi / 3
PI_OVER_FOUR = math.pi / 4
TWO_PI_OVER_THREE = math.pi * 2 / 3
THREE_PI_OVER_TWO = math.pi * 1.5

# endregion


# region Enumerations

class Mode(object):

    DISARMED = "DISARMED"
    STANDBY = "STANDBY"
    CONNECT = "CONNECT"
    HANDLE = "HANDLE"
    SELECTION = "SELECTION"
    MOVE = "MOVE"
    EDIT = "EDIT"
    ADD_BLOCK = "ADD_BLOCK"


class PortDirection(object):

    IN = "IN"
    OUT = "OUT"
    INOUT = "INOUT"
    DQ = "DQ"
    ABC = "ABC"


class Alignment(object):

    """Alignment constants.

    Numbers are the positions on a number pad with bi-directional lookup:

    NW:1       N:2   NE:3
     W:4  CENTER:5    E:6
    SW:7       S:8   SE:9

    """

    CENTER = 5
    N = 2
    NE = 3
    E = 6
    SE = 9
    S = 8
    SW = 7
    W = 4
    NW = 1

    items = {5: "CENTER", 2: "N", 3: "NE",
             6: "E", 9: "SE", 8: "S",
             7: "SW", 4: "W", 1: "NW",
             "CENTER": 5, "N": 2, "NE": 3,
             "E": 6, "SE": 9, "S": 8,
             "SW": 7, "W": 4, "NW": 1}

    @classmethod
    def __getitem__(cls, item):

        """In order to index like a dict.
        """
        return cls.items[item]

# endregion


# region Classes

class Symbol(object):

    """The drawn park of a block. Contains the drawn objects.
    """

    def __init__(self):

        self.lines = []
        self.circles = []
        self.rects = []
        self.rrects = []
        self.arcs = []
        self.labels = []
        self.fields = []
        self.equations = []

    def draw(self, dc, color=wx.Colour(0, 0, 0), width=5,
             fill=wx.Colour(0, 0, 0)):

        dc.SetBrush(wx.Brush(fill))
        dc.SetPen(wx.Pen(color, width))

        for circle in self.circles:
            if len(circle) == 3:
                dc.DrawCircle(*circle)
            elif len(circle) == 4:
                dc.DrawEllipse(*circle)

        for rect in self.rects:

            try:
                x, y, w, h, r = rect
            except:
                x, y, w, h = rect

            dc.DrawRectangle(x, y, w, h)

        for rrect in self.rrects:
            dc.DrawRectangle(rrect.x, rrect.y, rrect.w, rrect.h)

        for arc in self.arcs:
            pts = []

            x, y, r, ang1, ang2, cw = arc

            x1 = x + r * math.cos(ang1)
            y1 = y + r * math.sin(ang1)

            x2 = x + r * math.cos(ang2)
            y2 = y + r * math.sin(ang2)

            if ang2 == 0.0:
                if cw:
                    xc, yc = x1 + r, y1 - r
                else:
                    xc, yc = x1 + r, y1 + r
            else:
                if cw:
                    xc, yc = x1 - r, y1 - r
                else:
                    xc, yc = x1 + r, y1 - r

            pts.append(wx.Point(x1, y1))
            pts.append(wx.Point(xc, yc))
            pts.append(wx.Point(x2, y2))

            dc.DrawSpline(pts)

        for line in self.lines:
            pt1 = line[0]
            for pt2 in line[1:]:
                (x1, y1), (x2, y2) = pt1, pt2
                dc.DrawLine(x1, y1, x2, y2)
                pt1 = pt2

    def add_field(self, text="", position=(0, 0), size=5, align=Alignment.E,
                  block_rect=None, block_align=None, visible=True):

        field = Field(text, position, size, align, block_rect, block_align, visible)
        self.fields.append(field)
        return field

    def add_equation(self, numerator="", denominator="", position=(0, 0), size=5,
                  align=Alignment.E, block_rect=None, block_align=None):

        equation = EquationField(numerator, denominator, position, size, align,
                      block_rect, block_align)

        self.equations.append(equation)
        return equation

    def add_rrect(self, x, y, w, h, corners_only=False):

        rrect = ResizableRect(x, y, w, h, corners_only)
        self.rrects.append(rrect)
        return rrect


class SchematicObject(object):

    """Generic interactive object on the schematic.
    """

    zorder = 0  # will be incremented by the constructor.

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

    def flip_horizontal(self):

        self.hor_flip = not self.hor_flip

    def flip_vertical(self):

        self.ver_flip = not self.ver_flip

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


class Field(SchematicObject):

    """Text field.
    """

    def __init__(self, text="", position=(0, 0), size=5, align=Alignment.E,
                 rect_anchor=False, rect_align=None, visible=True):

        SchematicObject.__init__(self)

        self.text = text
        self.position = position
        self.size = size
        self.align = align
        self.rect_anchor = rect_anchor
        self.rect_align = rect_align
        self.visible = visible


class EquationField(Field):

    """Specialize text field with an equation to be rendered.
    """

    def __init__(self, equation="", position=(0, 0), size=5,
                 align=Alignment.E, rect_anchor=False, rect_align=None,
                 visible=True):

        Field.__init__(self, text="", position=position, size=size, align=align,
                 rect_anchor=rect_anchor, rect_align=rect_align, visible=True)

        self.equation = equation
        self.position = position
        self.size = size
        self.align = align
        self.rect_anchor = rect_anchor
        self.rect_align = rect_align
        self.visible = visible


class Handle(SchematicObject):

    """Grabable handle object.
    """

    def __init__(self, rect, position, alignment):

        SchematicObject.__init__(self)

        self.alignment = alignment
        self.position = position
        self.rect = rect

    def __getitem__(self, item):

        return self.position[item]

    def translate(self, delta):

        delta = self.rect.move_handle(self, delta)


class ResizableRect(SchematicObject):

    def __init__(self, x, y, w, h, corners_only=False, transparent=False):

        SchematicObject.__init__(self)

        self.x0, self.y0, self.w0, self.h0 = x, y, w, h
        self.x, self.y, self.w, self.h = x, y, w, h
        self.handles = None
        self.corners_only = corners_only
        self.setup_handles()
        self.block = None
        self.transparent = transparent

    def move_handle(self, handle, delta):

        if handle.rect == self:

            dx, dy = delta
            xp, yp = self.x, self.y
            update = True

            x0, y0, w0, h0 = self.x, self.y, self.w, self.h

            if handle.alignment == Alignment.NW:

                self.x = xp + dx
                self.y = yp + dy
                self.w -= dx
                self.h -= dy

            elif handle.alignment == Alignment.SW:

                self.x = xp + dx
                self.w -= dx
                self.h += dy

            elif handle.alignment == Alignment.NE:

                self.y = yp + dy
                self.w += dx
                self.h -= dy

            elif handle.alignment == Alignment.SE:

                self.w += dx
                self.h += dy

            elif handle.alignment == Alignment.N:

                self.y = yp + dy
                self.h -= dy

            elif handle.alignment == Alignment.S:

                self.h += dy

            elif handle.alignment == Alignment.W:

                self.x = xp + dx
                self.w -= dx

            elif handle.alignment == Alignment.E:

                self.w += dx

            else:

                update = False

            if update:

                self.setup_handles()

            return self.x, self.y, self.w, self.h

    def __getitem__(self, item):

        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        elif item == 2:
            return self.w
        elif item == 3:
            return self.h

    def setup_handles(self):

        x, y, w, h = self.x, self.y, self.w, self.h

        corners = dict(NW=Handle(self, (x, y), Alignment.NW),
                       SW=Handle(self, (x, y + h), Alignment.SW),
                       NE=Handle(self, (x + w, y), Alignment.NE),
                       SE=Handle(self, (x + w, y + h), Alignment.SE))

        edges = dict(N=Handle(self, (x + w / 2, y), Alignment.N),
                     S=Handle(self, (x + w / 2, y + h), Alignment.S),
                     W=Handle(self, (x, y + h / 2), Alignment.W),
                     E=Handle(self, (x + w, y + h / 2), Alignment.E))

        if self.corners_only:
            self.handles = corners

        else:
            self.handles = dict(corners.items() + edges.items())


class ConnectionPoint(SchematicObject):

    """Generic connectable point (eg. port or knee point)
    """

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

    """Connection point attached to block.
    """

    def __init__(self, block, index, position, direction=PortDirection.INOUT,
                 block_edge=Alignment.W, is_ground=False, anchored_rect=None,
                 anchored_align=None):

        ConnectionPoint.__init__(self, None)

        self.block_edge = block_edge
        self.index = index
        self.node = None
        self.position = position
        self.block = block
        self.is_ground = is_ground
        self.direction = direction
        self.initial_value = 0.0
        self.value = self.initial_value
        self.connected_ports = []
        self.anchored_rect = anchored_rect
        self.anchored_align = anchored_align

    def translate(self, delta):

        pass

    def add_connected_port(self, port):

        if not port in self.connected_ports:
            self.connected_ports.append(port)

    def remove_connected_port(self, port):

        if port in self.connected_ports:
            self.connected_ports.remove(port)

    def __str__(self):

        return f"Port({self.block}, {self.index})"

    def __repr__(self):

        return str(self)


class KneePoint(ConnectionPoint):

    def __init__(self, connector, position):

        ConnectionPoint.__init__(self, connector)

        self.position = position
        self.segments = None
        self.center = position


class Segment(SchematicObject):

    """An edge in the connection graph.
    """

    def __init__(self, connector, connection1, connection2):

        SchematicObject.__init__(self)

        self.connector = connector
        self.connection1 = connection1
        self.connection2 = connection2
        self.closest_hit_point = None
        self.ghost_knee = None

    def __getitem__(self, key):

        connections = self.connection1, self.connection2
        return connections[key]

    def get_angle(self):

        (x1, y1), (x2, y2) = self
        dx, dy = x2 - x1, y2 - y1

        return math.atan2(dy, dx)

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

    def __init__(self, start_connection):

        SchematicObject.__init__(self)

        self.start = start_connection.center
        self.end = self.start
        self.partial = True
        self.knees = []
        self.ports = []
        self.end_connection_point = None
        self.start_connection_point = start_connection
        self.segments = []
        self.active_connection = start_connection
        start_connection.add_connector(self)
        self.is_directional = True
        self.arrow = None

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

    def get_connection_points(self):

        return self.knees + self.ports

    def add_segment(self, next_connection):

        segment = Segment(self, self.active_connection, next_connection)

        self.segments.append(segment)

        if isinstance(next_connection, KneePoint):
            self.add_knee(next_connection)

        elif isinstance(next_connection, Port):
            self.add_port(next_connection)

        next_connection.add_connector(self)
        self.active_connection = next_connection

    def split_segment(self, segment, splitting_connection):

        if segment in self.segments:

            connection1 = segment.connection1
            segment2 = Segment(self, connection1, splitting_connection)
            segment.connection1 = splitting_connection
            i = self.segments.index(segment)
            self.segments.insert(i, segment2)
            self.add_knee(splitting_connection)
            splitting_connection.add_connector(self)

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
            return x2, y2
        elif self.partial:
            return self.end
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

    def update_arrow(self, pt, size=10, angle=PI_OVER_FOUR):

        line = None
        ang = None
        x, y = pt

        if self.partial and not self.segments:
            (x1, y1), (x2, y2) = self.start, self.end
            dx, dy = x2 - x1, y2 - y1
            ang = math.atan2(dy, dx)

        elif self.partial and self.segments:
            (xd, yd), (x1, y1) = self.segments[-1]
            (x2, y2) = self.end
            dx, dy = x2 - x1, y2 - y1
            ang = math.atan2(dy, dx)

        elif self.segments:
            ang = self.segments[-1].get_angle()

        if ang is not None:
            ang0 = ang + PI - angle
            ang1 = ang + PI + angle
            x0, y0 = x + size * math.cos(ang0), y + size * math.sin(ang0)
            x1, y1 = x + size * math.cos(ang1), y + size * math.sin(ang1)
            line = (x0, y0), (x, y), (x1, y1)

        self.arrow = line

    def __str__(self):

        return "(" + "-".join([str(port).strip() for port in self.ports]) + ")"

    def __repr__(self):

        return str(self)


class BlockLabel(SchematicObject):

    """Movable, anchored block label
    """

    def __init__(self, name, text, position, visible=True):

        SchematicObject.__init__(self)

        self.name = name
        self.position = position
        self.properties = {"text":text, "visible":visible}

    def get_text(self):

        return self.properties["text"]

    def set_text(self, txt):

        self.properties["text"] = txt

    def get_visible(self):

        return self.properties["visible"]

    def set_visible(self, visible):

        self.properties["visible"] = visible


class Block(SchematicObject):

    is_block = True

    def __init__(self, name, engine=None, is_ground=False,
                 is_signal_device=True, label_visible=True):

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
        self.labels = ODict()

        self.nominal_size = (120, 120)

        # copy symbol geometry from class attributes to instance:

        self.lines = deepcopy(self.symbol.lines)
        self.circles = deepcopy(self.symbol.circles)
        self.rects = deepcopy(self.symbol.rects)
        self.rrects = deepcopy(self.symbol.rrects)
        self.arcs = deepcopy(self.symbol.arcs)
        self.fields = deepcopy(self.symbol.fields)
        self.equations = deepcopy(self.symbol.equations)

        for rrect in self.rrects:
            rrect.block = self

        self.labels['name'] = BlockLabel('name', name, (-20, -20),
                                         visible=label_visible)

    def design_update(self):

        """Implemented by derived class if actions need to be taken after design
        time updates (like changed connections).
        """

        pass

    def get_engine(self, nodes):

        """Returns an instance of the engine for this block. Required to be
        implemented by the derived class.
        """

        raise NotImplementedError()

    def end(self):

        """Implemented by derived class if actions need to be taken at the end
        of the simulation.
        """

        pass

    def add_field(self, text="", position=(0, 0), size=5, align=Alignment.E,
                  block_rect=None, block_align=None, visible=True):

        field = Field(text, position, size, align, block_rect, block_align, visible)
        self.fields.append(field)

        return field

    def add_equation(self, equation="", position=(0, 0), size=5,
                  align=Alignment.E, block_rect=None, block_align=None):

        equation = EquationField(equation, position, size, align,
                      block_rect, block_align)
        self.equations.append(equation)

        return equation

    def __str__(self):

        return self.name

    def __repr__(self):

        return str(self)


class Schematic(object):

    """Schemetic data structure for file persistence.
    """

    def __init__(self, name):

        self.name = name
        self.blocks = {}
        self.connectors = []
        self.sim_settings = None
        self.parameters = []

    def copy(self):

        other = Schematic(self.name)

        other.blocks = {}
        other.connectors = []

        for name, block in self.blocks.items():

            if hasattr(block, "bmp"):
                bmptemp = block.bmp
                block.bmp = None
                other.blocks[name] = copy(block)
                block.bmp = bmptemp
            else:
                other.blocks[name] = copy(block)

        other.connectors = copy(self.connectors)

        other.sim_settings = copy(self.sim_settings)

        other.parameters = copy(self.parameters)

        return other


# endregion


# region Functions

def distance(line, point):

    """Returns the closest point and distance from a point to a line segment.
    """

    (cx, cy), ((ax, ay), (bx, by)) = point, line
    r_num = (cx - ax) * (bx - ax) + (cy - ay) * (by - ay)
    r_den = (bx - ax) * (bx - ax) + (by - ay) * (by - ay)

    if r_den > 0.0:

        r = r_num / r_den
        px, py = ax + r * (bx - ax), ay + r * (by - ay)
        s = ((ay - cy) * (bx - ax) - (ax - cx) * (by - ay)) / r_den

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

# endregion