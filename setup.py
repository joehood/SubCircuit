"""py2exe dist setup script

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
      }, requires=["numpy"]
)

