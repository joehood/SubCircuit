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
        name, ext = modpath.split(".")
        if not name == "__init__" and ext == "py":
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
        name, ext = modpath.split(".")
        if not name == "__init__" and ext == "py":
            devicemods[name] = __import__("subcircuit." + package + "." + name,
                                          fromlist=[name])

    for name, mod in devicemods.items():
        clsdefs = inspect.getmembers(mod, inspect.isclass)
        for clsname, cls in clsdefs:
            if issubclass(cls, sb.Block):
                friendly_name = cls.friendly_name
                blocks[friendly_name] = cls
            elif issubclass(cls, inter.Device):
                engines[clsname] = cls

    return blocks, engines


def get_block_bitmap(type_, color=wx.Colour(0,0,0), width=5):

    size = (120, 120)

    try:
        size = type_.size
    except:
        pass

    bitmap = wx.EmptyBitmap(*size)
    dc = wx.MemoryDC()
    dc.SelectObject(bitmap)
    type_.symbol.draw(dc, color=color, width=width)
    dc.SelectObject(wx.NullBitmap)

    return bitmap


def get_block_images(blocks, color=wx.Colour(0,0,0), width=5):
    """
    :param package:
    :return:
    """

    images = {}

    for name, block_type in blocks.items():
        try:
            bitmap = get_block_bitmap(block_type, color=color, width=width)
            image = bitmap.ConvertToImage()
            images[name] = image
        except Exception as e:
            pass

    return images


if __name__ == "__main__":

    engines, blocks = import_devices("devices")
    images = get_block_images(blocks)
    for name, image in images.items():
        image.SaveFile('Users/josephmhood/Documents/test/{0}.png'.format(name),
                       wx.BITMAP_TYPE_PNG)