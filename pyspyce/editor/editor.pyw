import sys
import bdb

import wx
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure
from wx.py.editwindow import EditWindow as PyEdit
from wx.py.shell import Shell as PyShell

from pyspyce.editor import editor_ui as ui


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
            print message
            # sync_source_line()
            if frame and filename[:1] + filename[-1:] != "<>" and os.path.exists(filename):
                if self.gui:
                    # we may be in other thread (i.e. debugging web2py)
                    wx.PostEvent(self.gui, DebugEvent(filename, lineno))

            # wait user events:
            self.waiting = True
            self.frame = frame
            try:
                while self.waiting:
                    wx.YieldIfNeeded()
            finally:
                self.waiting = False
            self.frame = None


class Editor(PyEdit):
    """PySpyce Editor"""

    def __init__(self, parent, id, script):
        """Create a new PySpyce editor window, add to parent, and load script."""
        PyEdit.__init__(self, parent, id)
        if script:
            self.AddText(open(script).read())
        self.setDisplayLineNumbers(True)


class Interactive(PyShell):
    """PySpyce interactive window."""

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


class MainFrame(ui.MainFrame):
    """PySpyce Main GUI Frame."""

    def __init__(self):
        """Create a new PySpyce GUI."""
        ui.MainFrame.__init__(self, None)
        #self.SetTitle("PySpyce Circuit Simulator")
        #icon = wx.Icon('image/pyspyce256.ico', wx.BITMAP_TYPE_ICO)
        #self.SetIcon(icon)
        self.debugger = Debugger()

        #self.script = 'examples.py'

        # add editor:
        self.editor = Editor(self.pnl_editor, 0, None)
        self.sizer_te = wx.BoxSizer(wx.VERTICAL)
        self.pnl_editor.SetSizer(self.sizer_te)
        self.sizer_te.Fit(self.pnl_editor)
        self.sizer_te.Add(self.editor, 1, wx.EXPAND | wx.ALL, 5)

        # add interactive window:
        self.interactive = Interactive(self.pnl_shell, 0, self.debugger)
        self.szr_shell = wx.BoxSizer(wx.VERTICAL)
        self.pnl_shell.SetSizer(self.szr_shell)
        self.szr_shell.Fit(self.pnl_shell)
        self.szr_shell.Add(self.interactive, 1, wx.EXPAND | wx.ALL, 5)

        # self.add_plot(([1,2,3], [3,4,5], 'label'))

    def on_run(self, event):
        filename = self.script
        self.interactive.run('from pyspyce import *')
        self.interactive.run('set_integrated_mode(True)')
        globals()['plot_notebook'] = self.ntb_top
        self.interactive.run('set_plot_notebook(plot_notebook)')
        self.interactive.runfile(filename)
        self.status_bar.SetStatusText('Running script: [{0}].'.format(filename))
        self.Layout()
        self.ntb_top.Layout()
        p = self.m_splitter1.GetSashPosition()
        self.m_splitter1.SetSashPosition(p + 1)

    def add_plot(self, *curves):
        plot_panel = PlotPanel(self.ntb_top)
        self.ntb_top.AddPage(plot_panel, 'Plot', True)
        plot_panel.set_data(curves)
        plot_panel.draw()


def main():
    """PySpyce Main Function"""
    # force this app to be the main process (above Python.exe).

    myappid = 'pyspyce'
    # ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    # Start GUI:
    app = wx.App()
    frame = MainFrame()
    frame.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()