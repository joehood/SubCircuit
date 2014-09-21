from distutils.core import setup
import py2exe
from distutils.filelist import findall

setup(windows=[{
        "script": "subcircuit/wxsubcircuit.pyw",
        "icon_resources": [(1, "subcircuit/subcircuit.ico")]
    }],
      zipfile="pyspycelib",
      data_files=["msvcr90.dll", "subcircuit/subcircuit.ico"],
      options={
          "py2exe": {
              "packages": ["subcircuit.devices", "subcircuit"],
              "dist_dir": "C:/builds/subcircuit/",
              "bundle_files": 3,
              "optimize": 1,
              "dll_excludes": ["MSVCP90.dll"]
          }
      }
)

