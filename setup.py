#!/usr/bin/env python

from __future__ import print_function

import os
import shutil
import subprocess
import sys
from glob import glob

import epicscorelibs.path
from epicscorelibs.config import get_config_var
from setuptools import Command
from setuptools.command.build_py import build_py
from setuptools_dso import DSO, build_dso, setup
from setuptools_dso.compiler import new_compiler

mydir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(mydir, "src", "python"))
if os.name == "nt":
    os.add_dll_directory(epicscorelibs.path.lib_path)


def find_unique_file(name):
    f = glob(f"**/{name}", recursive=True)
    if len(f) != 1:
        raise ValueError(f"Can't find unique file {name}: options were {f}")
    return f[0]


ait_sources = ait = [
    find_unique_file(f)
    for f in [
        "aitGen.c",
        "aitTypes.c",
    ]
]

gdd_sources = [
    find_unique_file(f)
    for f in [
        "gdd.cc",
        "gddTest.cc",
        "gddAppTable.cc",
        "gddNewDel.cc",
        "gddAppDefs.cc",
        "aitTypes.c",
        "aitConvert.cc",
        "aitHelpers.cc",
        "gddArray.cc",
        "gddContainer.cc",
        "gddErrorCodes.cc",
        "gddUtils.cc",
        "gddEnumStringTable.cc",
    ]
]

genapps_sources = gdd_sources + [find_unique_file("genApps.cc")]

pcas_sources = [
    find_unique_file(f)
    for f in [
        "caServer.cc",
        "caServerI.cc",
        "casCoreClient.cc",
        "casDGClient.cc",
        "casStrmClient.cc",
        "casPV.cc",
        "casPVI.cc",
        "casChannel.cc",
        "casChannelI.cc",
        "casAsyncIOI.cc",
        "casAsyncReadIO.cc",
        "casAsyncReadIOI.cc",
        "casAsyncWriteIO.cc",
        "casAsyncWriteIOI.cpp",  # Note: incorrect in makefile, .cpp on filesystem
        "casAsyncPVExistIO.cc",
        "casAsyncPVExistIOI.cpp",  # Note: incorrect in makefile, .cpp on filesystem
        "casAsyncPVAttachIO.cc",
        "casAsyncPVAttachIOI.cpp",  # Note: incorrect in makefile, .cpp on filesystem
        "casEventSys.cc",
        "casMonitor.cc",
        "casMonEvent.cc",
        "inBuf.cc",
        "outBuf.cc",
        "casCtx.cc",
        "casEventMask.cc",
        "st/ioBlocked.cc",  # Exclude mt impl
        "pvExistReturn.cc",
        "pvAttachReturn.cc",
        "caNetAddr.cc",
        "beaconTimer.cc",
        "beaconAnomalyGovernor.cc",
        "clientBufMemoryManager.cpp",
        "chanIntfForPV.cc",
        "channelDestroyEvent.cpp",
        "casIntfOS.cc",
        "casDGIntfOS.cc",
        "casStreamOS.cc",
        "caServerIO.cc",
        "casIntfIO.cc",
        "casDGIntfIO.cc",
        "casStreamIO.cc",
        "ipIgnoreEntry.cpp",
    ]
]
pcas_libraries = ["ws2_32"] if os.name == "nt" else []


def build(lib_name, *, sources, depends=None, dsos=None, libraries=None):
    mod = DSO(
        name=f"epicscorelibs_pcas.lib.{lib_name}",
        sources=sources,
        include_dirs=[
            epicscorelibs.path.include_path,
            os.path.join(mydir, "pcas", "src", "gdd"),
            os.path.join(mydir, "pcas", "src", "pcas", "build"),
            os.path.join(mydir, "pcas", "src", "pcas", "generic"),
            os.path.join(mydir, "pcas", "src", "pcas", "generic", "st"),
            os.path.join(mydir, "pcas", "src", "pcas", "generic", "mt"),
            os.path.join(mydir, "pcas", "src", "pcas", "io", "bsdSocket"),
            os.path.join(mydir, "include"),
        ],
        library_dirs=[epicscorelibs.path.lib_path],
        dsos=dsos or [],
        libraries=["Com", "ca"] + (libraries or []),
        extra_link_args=get_config_var("LDFLAGS"),
        lang_compile_args={
            "c": get_config_var("CFLAGS"),
            "c++": get_config_var("CXXFLAGS"),
        },
        define_macros=get_config_var("CPPFLAGS"),
        depends=depends or [],
    )

    return mod


class BuildGenerated(Command):
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        self.build_version_file()
        self.build_generated_files()

    def build_version_file(self):
        with open(os.path.join(mydir, "pcas", "configure", "CONFIG_PCAS_VERSION")) as f:
            for line in f:
                if line.startswith("EPICS_PCAS_MAJOR_VERSION"):
                    major = line.split("=")[1].strip()
                if line.startswith("EPICS_PCAS_MINOR_VERSION"):
                    minor = line.split("=")[1].strip()
                if line.startswith("EPICS_PCAS_MAINTENANCE_VERSION"):
                    maint = line.split("=")[1].strip()
                if line.startswith("EPICS_PCAS_DEVELOPMENT_FLAG"):
                    dev = line.split("=")[1].strip()

        with open(
            os.path.join(mydir, "pcas", "src", "pcas", "build", "casVersionNum.h@"), "r"
        ) as source, open(
            os.path.join(mydir, "pcas", "src", "pcas", "build", "casVersionNum.h"), "w"
        ) as dest:
            for line in source:
                new_line = (
                    line.replace("@EPICS_PCAS_MAJOR_VERSION@", major)
                    .replace("@EPICS_PCAS_MINOR_VERSION@", minor)
                    .replace("@EPICS_PCAS_MAINTENANCE_VERSION@", maint)
                    .replace("@EPICS_PCAS_DEVELOPMENT_FLAG@", dev)
                )
                dest.write(new_line)

    def build_generated_files(self):
        ait_objs = [f'{item.split(".")[0]}.obj' for item in ait_sources]
        genapps_objs = [f'{item.split(".")[0]}.obj' for item in genapps_sources]

        comp = new_compiler()
        comp.add_include_dir(os.path.join(mydir, "pcas", "src", "gdd"))
        comp.add_include_dir(epicscorelibs.path.include_path)
        comp.add_library_dir(epicscorelibs.path.lib_path)
        comp.add_library("Com")
        comp.compile(
            sources=ait_sources,
            output_dir=mydir,
            extra_preargs=epicscorelibs.config.get_config_var("CXXFLAGS"),
        )
        comp.link_executable(ait_objs, os.path.join(mydir, "pcas", "src", "gdd", "aitGen"))

        # Call code-generation executable
        subprocess.check_call(
            [
                os.path.join(mydir, "pcas", "src", "gdd", "aitGen"),
                os.path.join(mydir, "pcas", "src", "gdd", "aitConvertGenerated.cc"),
            ],
            cwd=os.path.join(mydir, "pcas", "src", "gdd"),
        )

        comp.compile(
            sources=genapps_sources + [os.path.join(mydir, "pcas", "src", "gdd", "genApps.cc")],
            output_dir=mydir,
            extra_preargs=epicscorelibs.config.get_config_var("CXXFLAGS"),
        )
        comp.link_executable(genapps_objs, os.path.join(mydir, "pcas", "src", "gdd", "genApps"))

        # Call code-generation executable
        env_with_core_libs = os.environ.copy()
        env_with_core_libs["PATH"] += os.pathsep + epicscorelibs.path.lib_path
        subprocess.check_call(
            [
                os.path.join(mydir, "pcas", "src", "gdd", "genApps"),
                os.path.join(mydir, "pcas", "src", "gdd", "gddApps.h"),
            ],
            cwd=os.path.join(mydir, "pcas", "src", "gdd"),
            env=env_with_core_libs,
        )


class CopyHeaders(Command):
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for file in glob("**/*.h", recursive=True):
            dst = os.path.join(
                mydir, "python", "epicscorelibs_pcas", "include", os.path.basename(file)
            )
            shutil.copy(file, dst)


gdd_mod = build(
    "gdd",
    depends=[
        os.path.join(mydir, "pcas", "src", "gdd", "aitConvertGenerated.cc"),
        os.path.join(mydir, "pcas", "src", "gdd", "gddApps.h"),
    ],
    sources=gdd_sources + [find_unique_file("dbMapper.cc")],
)
cas_mod = build(
    "cas",
    depends=[
        os.path.join(mydir, "pcas", "src", "pcas", "build", "casVersionNum.h"),
    ],
    dsos=["epicscorelibs_pcas.lib.gdd"],
    libraries=pcas_libraries,
    sources=pcas_sources,
)

build_dso.sub_commands.extend(
    [
        ("build_generated", lambda self: True),
        ("copy_headers", lambda self: True),
        # We generate some headers dynamically so rerun build_py
        # (which redoes copy_data_files) after we've generated them.
        ("build_py_again", lambda self: True),
    ]
)

setup(
    name="epicscorelibs_pcas",
    version="0.0.1a0",
    description="The EPICS PCAS binary libraries for use by python modules",
    long_description="""The EPICS (Experimental Physics and Industrial Control System) PCAS libraries built against epicscorelibs.
""",
    url="https://github.com/IsisComputingGroup/epicscorelibs_pcas",
    author="Tom Willemsen",
    author_email="tom.willemsen@stfc.ac.uk",
    license="EPICS",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "License :: Freely Distributable",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Distributed Computing",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
    ],
    keywords="epics scada",
    project_urls={
        "Source": "https://github.com/IsisComputingGroup/epicscorelibs_pcas",
        "Tracker": "https://github.com/IsisComputingGroup/epicscorelibs_pcas/issues",
    },
    python_requires=">=3",
    install_requires=[
        "setuptools",
        "setuptools_dso>=2.9a1",
        "epicscorelibs",
    ],
    packages=[
        "epicscorelibs_pcas",
        "epicscorelibs_pcas.lib",
        "epicscorelibs_pcas.path",
        "epicscorelibs_pcas.include",
    ],
    cmdclass={
        "copy_headers": CopyHeaders,
        "build_generated": BuildGenerated,
        "build_py_again": build_py,
    },
    package_dir={"": "python"},
    package_data={"epicscorelibs_pcas.include": ["*.h"]},
    x_dsos=[gdd_mod, cas_mod],
    include_package_data=True,
    zip_safe=False,
)
