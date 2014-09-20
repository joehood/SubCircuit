from setuptools import setup
import py2exe2msi.command

PACKAGE_NAME = "pypsyce"
VERSION = "1"

package_metadata = dict(
    name=PACKAGE_NAME,
    #version=VERSION,
    description="Python Based SPICE Circuit Simulator",
    author="josephmhood",
    author_email="",
    long_description="",
    license="Apache 2"
)

setup(
    options=dict(
        py2exe=dict(
            compressed=1,  # create a compressed zip archive
            optimize=2,
            excludes=["pywin",
                      "pywin.debugger",
                      "pywin.debugger.dbgcon",
                      "pywin.dialogs",
                      "pywin.dialogs.list"
            ]
        ),
        py2exe2msi=dict(
            pfiles_dir="c:/installs/pyspyce",
            upgrade_code="1"
        )
    ),
    # The lib directory contains everything except the executables and the python dll.
    # Can include a subdirectory name.
    zipfile="lib/shared.zip",
    **package_metadata
)
