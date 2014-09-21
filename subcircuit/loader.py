"""Tools for dynamically loading device definitions."""

import inspect
import os
import sandbox as sb
import interfaces as inter


def get_engine_classes(package="devices"):
    modpaths = os.listdir(package)
    engines = {}

    for modpath in modpaths:
        name, ext = modpath.split(".")
        if not name == "__init__" and ext == "py":
            mod = __import__("subcircuit." + package + "." + name, fromlist=[name])
            engines[name] = []
            clsdefs = inspect.getmembers(mod, inspect.isclass)
            for clsname, cls in clsdefs:
                if issubclass(cls, inter.Device):
                    engines[name].append(dict(name=clsname, cls=cls))
    return engines


def import_devices(package="devices"):
    """Imports devices and block classes into this module's namespace.
    :param package: local package to search in
    :return: None
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
