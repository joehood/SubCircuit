from __future__ import print_function
import wx


class Block(object):
    def __init__(self):
        self.position = (0, 0)
        self.rotation = 0
        self.scale = 1.0
        self.selected = False

    def draw(self, gc):
        pass


class RBlock(Block):
    def __init__(self):
        Block.__init__(self)
        self.line_color = wx.Colour(120, 120, 120)
        self.fill_color = wx.Colour(100, 100, 100)
        self.line_width = 2
        self.pen = wx.Pen(self.line_color, self.line_width)
        self.brush = wx.Brush(self.fill_color)
        self.pen.Cap = wx.CAP_BUTT

    def draw(self, gc):
        x, y = self.position
        gc.SetPen(self.pen)
        gc.SetBrush(self.brush)
        gc.BeginLayer(0.5)
        gc.DrawRoundedRectangle(x, y, 100, 100, 5)
        gc.EndLayer()



class Sandbox(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.Bind(wx.EVT_PAINT, self.on_paint)

        # drawing context:
        self.gc = None
        self.dc = None

        # mouse movement management:
        self.dragging = False
        self.x0 = 0.0
        self.y0 = 0.0
        self.dx = 0.0
        self.dy = 0.0
        self.scale = 1.0
        self.scale_factor = 1.0
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_scroll)

        # block management:
        self.blocks = {}

    def add_block(self, key, block, location):
        self.blocks[key] = block
        self.blocks[key].location = location

    def on_left_down(self, event):
        self.x0, self.y0 = event.GetLogicalPosition(self.dc)

    def on_motion(self, event):
        if event.Dragging():
            self.dx += (event.x - self.x0)
            self.dy += (event.y - self.y0)
            self.x0 = event.x
            self.y0 = event.y
            self.Refresh()

    def on_scroll(self, event):
        delta = event.GetWheelDelta()
        d = event.ControlDown()
        self.scale += delta * self.scale_factor
        self.Refresh()

    def draw_grid(self, gc):

        spacing = 10.0
        extension = 1000.0

        w, h = gc.GetSize()
        w += extension
        h += extension

        ver = int(w / spacing)
        hor = int(h / spacing)

        pen = wx.Pen(wx.Colour(200, 200, 200), 1)
        pen.Cap = wx.CAP_BUTT
        gc.SetPen(pen)

        for i in range(ver):
            offset = i * spacing - extension/2
            gc.StrokeLine(offset, 0 - extension/2, offset, h)

        for i in range(hor):
            offset = i * spacing - extension/2
            gc.StrokeLine(0 - extension/2, offset, w, offset)

    def on_paint(self, event):

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

        # blocks:
        for name, block in self.blocks.items():
            block.draw(gc)

        # pen = wx.Pen('red', 5)
        # pen.Cap = wx.CAP_BUTT
        # gc.SetPen(pen)
        # path = gc.CreatePath()
        # path.AddCircle(10, 10, 5)
        # gc.StrokePath(path)


if __name__ == '__main__':
    app = wx.App()
    frame = wx.Frame(None, size=(500, 500))

    sandbox = Sandbox(frame)
    resistor = RBlock()
    sandbox.add_block('r1', resistor, (100, 100))

    frame.Show()
    app.MainLoop()