from distutils.core import setup
import py2exe
from distutils.filelist import findall

setup(windows=[
    {
        "script": "pyspyce/wxpyspyce.pyw",
        "icon_resources": [(1, "pyspyce/pslogo.ico")]
    }
],
      zipfile="pyspycelib",
      data_files=["msvcr90.dll", "pyspyce/pslogo.ico"],
      options={
          "py2exe": {
              "packages": ["pyspyce.devices", "pyspyce"],
              "dist_dir": "C:/builds/pyspyce/",
              "bundle_files": 3,
              "optimize": 1,
              "dll_excludes": ["MSVCP90.dll"]
          }
      }
)


print "done."
