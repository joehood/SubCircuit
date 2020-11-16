"""Tools for dynamically loading device definitions.

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

import inspect
import os
import sys

import wx

import sandbox as sb
import interfaces as inter


def load_engines_to_module(module, dir="devices"):
    """imports all device engines into the provided module's namepace.
    :param module: the module into which the device classes will be imported
    :return: None
    """
    modpaths = os.listdir(dir)
    devicemods = {}

    for modpath in modpaths:
        name, ext =  os.path.splitext(modpath)
        if not name == "__init__" and ext == ".py":
            devicemods[name] = __import__("subcircuit.devices." + name,
                                          fromlist=[name])
    for name, mod in devicemods.items():
        clsdefs = inspect.getmembers(mod, inspect.isclass)
        for clsname, cls in clsdefs:
            if issubclass(cls, inter.Device):
                setattr(module, clsname, cls)


def import_devices(package="devices"):
    """Imports devices and block classes into a module's namespace.
    :param package: local package to search in
    :return: blocks, engines
    """
    engines = {}
    blocks = {}

    modpaths = os.listdir(package)
    devicemods = {}

    for modpath in modpaths:
        name, ext = os.path.splitext(modpath)
        if not name == "__init__" and ext == ".py":
            devicemods[name] = __import__("subcircuit." + package + "." + name,
                                          fromlist=[name])

    for name, mod in devicemods.items():
        clsdefs = inspect.getmembers(mod, inspect.isclass)
        for clsname, cls in clsdefs:
            is_type = False
            try:
                is_type = cls.is_device
                engines[clsname] = cls
            except AttributeError:
                pass
            try:
                is_type = cls.is_block
                friendly_name = cls.friendly_name
                blocks[friendly_name] = cls
            except AttributeError:
                pass

    return blocks, engines


def get_block_thumbnail(type_, fgcolor=wx.Colour(0, 0, 0),
                     bgcolor=wx.Colour(255, 255, 255), width=5):

    size = (120, 120)

    try:
        size = type_.size
    except:
        pass

    bitmap = wx.Bitmap(*size)
    dc = wx.MemoryDC()
    dc.SelectObject(bitmap)
    dc.Clear()
    dc.SetBackground(wx.Brush(bgcolor))
    type_.symbol.draw(dc, color=fgcolor, fill=bgcolor, width=width)
    dc.SelectObject(wx.NullBitmap)

    return bitmap


def get_block_thumbnails(blocks, fgcolor=wx.Colour(0, 0, 0),
                     bgcolor=wx.Colour(255, 255, 255), width=5):
    """
    :param package:
    :return:
    """

    images = {}

    for name, block_type in blocks.items():
        try:
            bitmap = get_block_thumbnail(block_type, fgcolor, bgcolor, width)
            image = bitmap.ConvertToImage()
            images[name] = image
        except Exception as e:
            print(f"Error getting block bitmap: {e}")

    # debug:

    for name, image in images.items():
        image.SaveFile(f"c:\\temp\\images\\{name}.png", wx.BITMAP_TYPE_PNG)

    return images


if __name__ == "__main__":

    os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

    engines, blocks = import_devices("devices")
    images = get_block_thumbnails(blocks)
    for name, image in images.items():
        image.SaveFile(f"c:\\temp\\{name}.png", wx.BITMAP_TYPE_PNG)