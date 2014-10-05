
import wx
from wx.grid import Grid as wxGrid



class Parameter(object):
    def __init__(self, ptitype="CON", ptiindex=-1, label=None,
                 desc="", units="NA",
                 default=None, value=None, constraints_warn=None,
                 constraints_error=None):
        self.ptitype = ptitype
        self.ptiindex = 0
        self.label = label
        self.desc = desc
        self.units = units
        self.default = default
        self.value = default
        self.constaints_warn = []
        self.constaints_error = []



class ParameterTable(wxGrid):
    def __init__(self, parent, paramlist):
        wxGrid.__init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                        size=wx.DefaultSize, style=wx.WANTS_CHARS,
                        name="")

        self.paramlist = paramlist

        self.CreateGrid(200, 9)
        self.EnableEditing(True)
        self.EnableGridLines(True)
        self.EnableDragGridSize(False)
        self.SetMargins(0, 0)
        self.EnableDragColMove(True)
        self.EnableDragColSize(True)
        self.EnableDragRowSize(True)
        self.EnableDragCell(False)

        self.SetColLabelValue(0, "Type"); self.SetColSize(0, 40)
        self.SetColLabelValue(1, "Index"); self.SetColSize(1, 40)
        self.SetColLabelValue(2, "Label"); self.SetColSize(2, 80)
        self.SetColLabelValue(3, "Description"); self.SetColSize(3, 120)
        self.SetColLabelValue(4, "Units"); self.SetColSize(4, 60)
        self.SetColLabelValue(5, "Default"); self.SetColSize(5, 80)
        self.SetColLabelValue(6, "Value"); self.SetColSize(6, 80)
        self.SetColLabelValue(7, "Constraints (Warn)"); self.SetColSize(7, 160)
        self.SetColLabelValue(8, "Constraints (Error)"); self.SetColSize(8, 160)

        self.SetColLabelSize(20)
        self.SetColLabelAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)
        self.SetRowLabelSize(0)
        self.SetRowLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_CENTRE)
        self.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)

        # Connect Events
        self.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.on_grid_update)

        # load:
        self.data2grid()

    def __del__(self):
        pass

    def data2grid(self):

        for param in self.paramlist:

            self.ClearGrid()

            row = 0

            for param in self.paramlist:

                ptitype = param.ptitype
                ptiindex = param.ptiindex
                label = param.label
                desc = param.desc
                units = param.units
                default = param.default
                value = param.value
                constraints_warn = param.constraints_warn
                constraints_error = param.constraints_error

                self.SetCellValue(0, 0, str(ptitype))
                self.SetCellValue(0, 1, str(ptiindex))
                self.SetCellValue(0, 2, str(label))
                self.SetCellValue(0, 3, str(desc))
                self.SetCellValue(0, 4, str(units))
                self.SetCellValue(0, 5, str(default))
                self.SetCellValue(0, 6, str(value))
                self.SetCellValue(0, 7, str(constraints_warn))
                self.SetCellValue(0, 8, str(constraints_error))

                row += 1

    def parse_constraints(self, strg):
        constraints = []
        return constraints

    def grid2data(self):

        self.paramlist = []

        for row in range(self.GetNumberRows()):

            ptitype = str(self.GetCellValue(row, 0)).strip()

            if ptitype is not "":

                ptiindex = self.GetCellValue(row, 1)
                label = self.GetCellValue(row, 2)
                desc = self.GetCellValue(row, 3)
                units = self.GetCellValue(row, 4)
                default = self.GetCellValue(row, 5)
                value = self.GetCellValue(row, 6)
                constraints_warn = self.GetCellValue(row, 7)
                constraints_error = self.GetCellValue(row, 8)

                param = Parameter(ptitype, ptiindex, label, desc, units, default, value,
                                  constraints_warn, constraints_error)

                self.paramlist.append(param)

    def on_grid_update(self, event):

        self.grid2data()



if __name__ == "__main__":

    app = wx.App()
    frame = wx.Frame(None)

    grid = ParameterTable(frame, [])

    szr = wx.BoxSizer(wx.VERTICAL)
    szr.Add(grid, 0, 0, 5)
    frame.SetSizer(szr)
    frame.Layout()
    szr.Fit(frame)

    frame.Show()
    app.MainLoop()