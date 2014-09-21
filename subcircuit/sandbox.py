"""Generic ghaphical sandbox for laying out blocks with connectors.

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

import math
from collections import OrderedDict as ODict

import wx


# region Constants

# default settings:
BG_COLOR = wx.Colour(0, 0, 0)
GRID_COLOR = wx.Colour(30, 30, 30)
DEVICE_COLOR = wx.Colour(130, 130, 130)
SELECT_COLOR = wx.Colour(255, 255, 255)
HOVER_COLOR = wx.Colour(255, 255, 255)
GHOST_COLOR = wx.Colour(220, 220, 220)
SCOPE_BG = wx.Colour(50, 50, 50)
SCOPE_FG = wx.Colour(40, 80, 40)
SCOPE_CURVE = wx.Colour(100, 200, 100)
LINE_WIDTH = 2
SELECT_WIDTH = 3
HOVER_WIDTH = 2
GRID_SIZE = 20
GRID_WIDTH = 1
SHOW_CROSSHAIR = False
MOVE_DELTA = GRID_SIZE
DEF_DEVICE = "Resistor"
FONT_SIZE = 14
ORTHO_CONNECTORS = False
CONNECTOR_HIT_MARGIN = 10
PORT_HIT_MARGIN = 10
PORT_RADIUS = 3
SNAP_TO_GRID = True
DEF_SIM_SETTINGS = ODict()
DEF_SIM_SETTINGS["dt"] = 0.001
DEF_SIM_SETTINGS["tmax"] = 0.1
DEF_SIM_SETTINGS["maxitr"] = 200
DEF_SIM_SETTINGS["tol"] = 0.00001
DEF_SIM_SETTINGS["voltages"] = ""
DEF_SIM_SETTINGS["currents"] = ""

# endregion


class Mode(object):
    DISARMED = 0
    STANDBY = 1
    CONNECT = 3
    SELECTION = 4
    MOVE = 5
    EDIT = 6
    ADD_BLOCK = 7


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


class Schematic(object):
    def __init__(self, name):
        self.name = name
        self.blocks = {}
        self.connectors = []
        self.sim_settings = DEF_SIM_SETTINGS


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

