# -*- coding: utf-8 -*- 

# ##########################################################################
# # Python code generated with wxFormBuilder (version Jun  5 2014)
# # http://www.wxformbuilder.org/
# #
# # PLEASE DO "NOT" EDIT THIS FILE!
# ##########################################################################

import wx
import wx.xrc

# ##########################################################################
## Class MainFrame
###########################################################################

class MainFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title=wx.EmptyString, pos=wx.DefaultPosition,
                          size=wx.Size(800, 600),
                          style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)

        self.status_bar = self.CreateStatusBar(1, wx.ST_SIZEGRIP, wx.ID_ANY)
        self.menu_bar = wx.MenuBar(0)
        self.menu_file = wx.Menu()
        self.item_open = wx.MenuItem(self.menu_file, wx.ID_ANY, u"Open", wx.EmptyString, wx.ITEM_NORMAL)
        self.menu_file.AppendItem(self.item_open)

        self.menu_bar.Append(self.menu_file, u"File")

        self.menu_run = wx.Menu()
        self.item_run = wx.MenuItem(self.menu_run, wx.ID_ANY, u"Run Script", wx.EmptyString, wx.ITEM_NORMAL)
        self.menu_run.AppendItem(self.item_run)

        self.menu_bar.Append(self.menu_run, u"Run")

        self.SetMenuBar(self.menu_bar)

        szr_main = wx.BoxSizer(wx.VERTICAL)

        self.m_splitter1 = wx.SplitterWindow(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
                                             wx.SP_3D | wx.SP_3DSASH)
        self.m_splitter1.Bind(wx.EVT_IDLE, self.m_splitter1OnIdle)

        self.panel_top = wx.Panel(self.m_splitter1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        szr_top = wx.BoxSizer(wx.VERTICAL)

        self.ntb_top = wx.Notebook(self.panel_top, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        self.pnl_editor = wx.Panel(self.ntb_top, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.ntb_top.AddPage(self.pnl_editor, u"Editor", True)

        szr_top.Add(self.ntb_top, 1, wx.EXPAND | wx.ALL, 5)

        self.panel_top.SetSizer(szr_top)
        self.panel_top.Layout()
        szr_top.Fit(self.panel_top)
        self.panel_bottom = wx.Panel(self.m_splitter1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        szr_bottom = wx.BoxSizer(wx.VERTICAL)

        self.ntb_bottom = wx.Notebook(self.panel_bottom, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        self.pnl_shell = wx.Panel(self.ntb_bottom, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.ntb_bottom.AddPage(self.pnl_shell, u"Python 2.7 Interactive", False)

        szr_bottom.Add(self.ntb_bottom, 1, wx.ALL | wx.EXPAND, 5)

        self.panel_bottom.SetSizer(szr_bottom)
        self.panel_bottom.Layout()
        szr_bottom.Fit(self.panel_bottom)
        self.m_splitter1.SplitHorizontally(self.panel_top, self.panel_bottom, 0)
        szr_main.Add(self.m_splitter1, 1, wx.EXPAND, 5)

        self.SetSizer(szr_main)
        self.Layout()

        self.Centre(wx.BOTH)

        # Connect Events
        self.Bind(wx.EVT_MENU, self.on_run, id=self.item_run.GetId())

    def __del__(self):
        pass


    # Virtual event handlers, overide them in your derived class
    def on_run(self, event):
        event.Skip()

    def m_splitter1OnIdle(self, event):
        self.m_splitter1.SetSashPosition(0)
        self.m_splitter1.Unbind(wx.EVT_IDLE)
	

