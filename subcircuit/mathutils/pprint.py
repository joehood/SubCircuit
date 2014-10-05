from __future__ import print_function
import wx

import sympy
from sympy.parsing.sympy_parser import parse_expr as parse

import matplotlib
import matplotlib.figure
import matplotlib.backends.backend_agg

import Image  # PIL (Python Image Library)
import ImageChops  # Image Channel Operations library
import ImageOps  # Various whole image operations.

from cStringIO import StringIO


# region charmap

charmap = ((r"*", u""),
           (r"{alpha}", u"\u03b1"),
           (r"{beta}", u"\u03b2"),
           (r"{gamma}", u"\u03b3"),
           (r"{delta}", u"\u03b4"),
           (r"{epsilon}", u"\u03b5"),
           (r"{zeta}", u"\u03b6"),
           (r"{eta}", u"\u03b7"),
           (r"{theta}", u"\u03b8"),
           (r"{iota}", u"\u03b9"),
           (r"{kappa}", u"\u03ba"),
           (r"{lambda}", u"\u03bb"),
           (r"{mu}", u"\u03bc"),
           (r"{nu}", u"\u03bd"),
           (r"{xi}", u"\u03be"),
           (r"{omicron}", u"\u03bf"),
           (r"{pi}", u"\u03c0"),
           (r"{ro}", u"\u03c1"),
           (r"{sigma}", u"\u03c3"),
           (r"{tau}", u"\u03c4"),
           (r"{upsilon}", u"\u03c5"),
           (r"{phi}", u"\u03c6"),
           (r"{chi}", u"\u03c7"),
           (r"{psi}", u"\u03c8"),
           (r"{omega}", u"\u03c9"),
           (r"{div}", u"\u00F7"),
           (r"{deg}", u"\u00B0"),
           (r"{1/2}", u"\u00BC"),
           (r"{1/4}", u"\u00BD"),
           (r"{int}", u"\u0283"),
           (r"_{beta}", u"\u1D66"),
           (r"_{lambda}", u"\u1D67"),
           (r"_{ro}", u"\u1D68"),
           (r"_{theta}", u"\u1D69"),
           (r"_{chi}", u"\u1D6A"),
           (r"{x}", u"\u00D7"),
           (r"{.}", u"\u00B7"),
           (r"_0", u"\u2080"),
           (r"_1", u"\u2081"),
           (r"_2", u"\u2082"),
           (r"_3", u"\u2083"),
           (r"_4", u"\u2084"),
           (r"_5", u"\u2085"),
           (r"_6", u"\u2086"),
           (r"_7", u"\u2087"),
           (r"_8", u"\u2088"),
           (r"_9", u"\u2089"),
           (r"_+", u"\u208A"),
           (r"_-", u"\u208B"),
           (r"_=", u"\u208C"),
           (r"_(", u"\u208D"),
           (r"_)", u"\u208E"),
           (r"_a", u"\u2090"),
           (r"_e", u"\u2091"),
           (r"_o", u"\u2092"),
           (r"_x", u"\u2093"),
           (r"_i", u"\u1D62"),
           (r"_r", u"\u1D63"),
           (r"_u", u"\u1D64"),
           (r"_v", u"\u1D65"),
           (r"^{theta}", u"\u1DBF"),
           (r"^{epsilon}", u"\u1D4B"),
           (r"^{upsilon}", u"\u02E1"),
           (r"^{eta}", u"\u1D51"),
           (r"^{nu}", u"\u1D5b"),
           (r"^{beta}", u"\u1D5d"),
           (r"^{delta}", u"\u1D5f"),
           (r"^{phi}", u"\u1D60"),
           (r"^{chi}", u"\u1D61"),
           (r"^0", u"\u2070"),
           (r"^1", u"\u00B9"),
           (r"^i", u"\u2071"),
           (r"^2", u"\u00B2"),
           (r"^3", u"\u00B3"),
           (r"^4", u"\u2074"),
           (r"^5", u"\u2075"),
           (r"^6", u"\u2076"),
           (r"^7", u"\u2077"),
           (r"^8", u"\u2078"),
           (r"^9", u"\u2079"),
           (r"^+", u"\u207A"),
           (r"^-", u"\u207B"),
           (r"^=", u"\u207C"),
           (r"^(", u"\u207D"),
           (r"^)", u"\u207E"),
           (r"^n", u"\u207F"),
           (r"^a", u"\u00AA"),
           (r"^o", u"\u00BA"),
           (r"^b", u"\u1D47"),
           (r"^d", u"\u1D48"),
           (r"^e", u"\u1D49"),
           (r"^g", u"\u1D4D"),
           (r"^k", u"\u1D4F"),
           (r"^m", u"\u1D50"),
           (r"^p", u"\u1D56"),
           (r"^t", u"\u1D57"),
           (r"^u", u"\u1D58"),
           (r"^h", u"\u02B0"),
           (r"^j", u"\u02B0"),
           (r"^r", u"\u02B2"),
           (r"^w", u"\u02B3"),
           (r"^y", u"\u02E0"),
           (r"^s", u"\u02E2"),
           (r"^x", u"\u02E3"),
           (r"^A", u"\u1D2C"),
           (r"^B", u"\u1D2E"),
           (r"^C", u"\u1D9C"),
           (r"^D", u"\u1D30"),
           (r"^E", u"\u1D31"),
           (r"^G", u"\u1D33"),
           (r"^H", u"\u1D34"),
           (r"^I", u"\u1D35"),
           (r"^J", u"\u1D36"),
           (r"^K", u"\u1D37"),
           (r"^L", u"\u1D38"),
           (r"^M", u"\u1D39"),
           (r"^N", u"\u1D3A"),
           (r"^O", u"\u1D3C"),
           (r"^P", u"\u1D3E"),
           (r"^R", u"\u1D3F"),
           (r"^T", u"\u1D40"),
           (r"^U", u"\u1D41"),
           (r"^W", u"\u1D42"))

# endregion


def unicode_print(str):
    pstr = str

    for char, ucode in charmap:
        pstr = pstr.replace(char, ucode)

    return pstr


def equ2latex(strg):

    a = sympy.Symbol("s")

    expr = sympy.sympify(strg)

    ltx = str(expr)
    ltx = sympy.latex(expr)

    return ltx


def tex2img(tex, filename="equ.png", font_size=20):

    font_size = 20

    figure = matplotlib.figure.Figure(None, facecolor=(0, 0, 0, 0))
    canvas = matplotlib.backends.backend_agg.FigureCanvasAgg(figure)

    font_size = font_size

    tex = "${0}$".format(tex)

    figure.clear()
    figure.text(0.05, 0.5, tex, size=font_size)

    canvas.draw()

    png = "equ.png"

    figure.savefig(png, transparent=True, dpi=300, format="png")

    img = Image.open(png)

    imginv = ImageChops.invert(img.convert('L'))

    box = imginv.getbbox()

    img = img.crop(box)

    img = ImageOps.expand(img, border=10, fill=(255, 255, 255, 0))

    img.save(png, format="png")

    return img


def equ2bmp(equ, size=20):

    ltx = equ2latex(equ)
    img = tex2img(ltx, font_size=size)
    return wx.Bitmap("equ.png", wx.BITMAP_TYPE_PNG)


class TestWindow(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.bmp = None

    def on_paint(self, event):
        dc = wx.PaintDC(self)
        gc = wx.GraphicsContext.Create(dc)

        max_width = 200.0

        w0, h0 = self.bmp.GetSize()

        w = min(max_width, w0)
        h = h0 * (w / w0)


        gc.DrawBitmap(self.bmp, 50, 50, w, h)

    def set_equ(self, equ, size=20):

        ltx = equ2latex(equ)
        img = tex2img(ltx, font_size=size)

        self.bmp = wx.Bitmap("equ.png", wx.BITMAP_TYPE_PNG)

        self.Refresh()



if __name__ == "__main__":

    str1 = "Sigma"

    rplc = (("^2", "**2"),)

    for s0, s1 in rplc:
        str1.replace(s0, s1)

    app = wx.App()
    frame = wx.Frame(None)
    frame.SetSize((400, 400))
    test = TestWindow(frame)

    test.set_equ(str1, 20)

    frame.Show()
    app.MainLoop()



