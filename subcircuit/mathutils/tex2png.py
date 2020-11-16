
import wx
import matplotlib
matplotlib.use('WXAgg')
import matplotlib.figure
import matplotlib.backends.backend_wxagg

import Image  # PIL (Python Image Library)
import ImageChops  # Image Channel Operations library
import ImageStat  # Image Statistics library
import ImageOps  # Various whole image operations.


class MathPanel(wx.Panel):
    """
    The MathPanel is a very simple panel with just and MPL figure on it,
    it will automatically render text in the middle of the figure
    """

    def __init__(self, parent):

        wx.Panel.__init__(self, parent=parent, size=(500, 200))

        self.figure = matplotlib.figure.Figure(None, facecolor='white')
        self.canvas = matplotlib.backends.backend_wxagg.FigureCanvasWxAgg(
            self, -1, self.figure)

        self._SetSize()
        self.Bind(wx.EVT_SIZE, self._SetSize)

        self.TeX = ''
        self.font_size = 20
        self.RenderEquation()

    def SetTeX(self, str):

        self.TeX = '$%s$' % (str)
        self.RenderEquation()

    def RenderEquation(self):

        self.renderError = False  # Can save to file only if False

        try:
            self.figure.clear()
            self.figure.text(0.05, 0.5, self.TeX, size=self.font_size)
            self.canvas.draw()

        except matplotlib.pyparsing.ParseFatalException:

            self.renderError = True  # Don't save the Tex error message to a file !
            self.figure.clear()
            self.figure.text(0.05, 0.5, 'Parsing Error in MathTeX',
                             size=self.font_size)
            self.canvas.draw()

    def _SetSize(self, evt=None):

        pixels = self.GetSize()
        self.SetSize(pixels)
        self.canvas.SetSize(pixels)

        dpi = self.figure.get_dpi()
        self.figure.set_size_inches(float(pixels[0]) / dpi,
                                    float(pixels[1]) / dpi)


class MathFrame(wx.Frame):

    def __init__(self):

        wx.Frame.__init__(self, None, -1, pos=(10, 10),
                          title='Matplotlib Math EquationRenderer Test')
        self.ClientSize = (800, 275)

        # Frames need an initial panel to provide tab traversal and
        # cross-platform background color capabilities.
        frmPanel = wx.Panel(self)

        self.math_panel = MathPanel(frmPanel)

        self.input_box = wx.TextCtrl(frmPanel, size=(500, -1))

        self.input_box.Font = wx.Font(10,
                                      wx.FONTFAMILY_ROMAN,
                                      wx.FONTSTYLE_NORMAL,
                                      wx.FONTWEIGHT_NORMAL)

        self.input_box.Bind(wx.EVT_TEXT, self.OnText)

        equation = r'Goober = {\min(\int\ (\ {\delta{(\ \pi{}*\frac{\sum(\ a+\O\o\l\S\P\L\{b\}\ )\ } {( c-d )}})}\ )}'
        self.input_box.Value = equation

        label_stTxt = wx.StaticText(frmPanel, label='Type some TeX here :')

        saveBtn = wx.Button(frmPanel, label='Save Equation to File')
        saveBtn.Bind(wx.EVT_LEFT_DOWN, self.OnSaveToFileBtn)

        exitBtn = wx.Button(frmPanel, label='Exit')
        exitBtn.Bind(wx.EVT_LEFT_DOWN, self.OnExit)

        frmPnl_vertSzr = wx.BoxSizer(wx.VERTICAL)

        frmPnl_vertSzr.Add(label_stTxt, proportion=0, flag=wx.TOP | wx.LEFT,
                           border=5)
        frmPnl_vertSzr.Add(self.input_box, proportion=0, flag=wx.GROW | wx.ALL,
                           border=5)
        frmPnl_vertSzr.Add(self.math_panel, proportion=1, flag=wx.GROW)
        frmPnl_vertSzr.Add(saveBtn, proportion=0,
                           flag=wx.ALIGN_CENTER | wx.BOTTOM | wx.TOP,
                           border=10)
        frmPnl_vertSzr.Add(exitBtn, proportion=0,
                           flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)

        frmPanel.SetSizerAndFit(frmPnl_vertSzr)

    def OnText(self, evt):

        self.math_panel.SetTeX(self.input_box.Value)

    def OnExit(self, evt):

        self.Close()

    def OnSaveToFileBtn(self, event):

        if not self.math_panel.renderError:

            filename = 'equ.png'
            self.math_panel.figure.savefig(filename, dpi=300)

            pilImg = Image.open(filename)

            # Find the ordinates of the minimally enclosing bounding box.
            #
            # Create a simplified and inverted version of the original image to examine.
            invertedImage = ImageChops.invert(pilImg.convert('L'))

            # Get the bounding box's ordinates. Works on any image with a black background.
            box = invertedImage.getbbox()
            pilImg = pilImg.crop(box)

            # Add back a thin border padding
            pilImg = ImageOps.expand(pilImg, border=10, fill=(255, 255, 255))

            # Save the image to a disk file. Only PNG and TIFF formats are non-destructive.
            pilImg.save(filename)

        else:
            pass


def img_from_tex(tex, font_size=20):

    figure = matplotlib.figure.Figure(None, facecolor='white')
    #canvas = matplotlib.backends.backend_wxagg.FigureCanvasWxAgg(None, -1, figure)
    canvas = matplotlib.backends.backend_wxagg.FigureCanvasAgg(figure)

    font_size = font_size

    tex = "${0}$".format(tex)

    figure.clear()
    figure.text(0.05, 0.5, tex, size=font_size)
    canvas.draw()

    filename = 'equ.png'

    figure.savefig(filename, dpi=600)

    img = Image.open(filename)

    imginv = ImageChops.invert(img.convert('L'))

    box = imginv.getbbox()
    img = img.crop(box)

    img = ImageOps.expand(img, border=10, fill=(255, 255, 255))

    img.save(filename)

    return img



if __name__ == '__main__':

    app = wx.App(redirect=False)
    appFrame = MathFrame().Show()
    app.MainLoop()

    #img = img_from_tex(r"\frac{\theta}{\zeta}")

