#!/usr/bin/env python

from __future__ import print_function

import os
import subprocess
import sys
from glob import glob

from setuptools_dso import DSO, setup
from setuptools_dso.compiler import new_compiler

mydir = os.path.abspath(os.path.dirname(__file__))

sys.path.insert(0, os.path.join(mydir, "src", "python"))

import epicscorelibs.path
from epicscorelibs.config import get_config_var

os.add_dll_directory(epicscorelibs.path.lib_path)


def build(lib_name, sources=None, depends=None, dsos=None, libraries=None):
    if not sources:
        sources = (
            glob(f"pcas/src/{lib_name}/**/*.c", recursive=True)
            + glob(f"pcas/src/{lib_name}/**/*.cc", recursive=True)
            + glob(f"pcas/src/{lib_name}/**/*.cpp", recursive=True)
        )

        # Generated cc which is only actually used in includes (can't build by itself)
        sources = [
            s
            for s in sources
            if not s.endswith("aitConvertGenerated.cc")  # For code generation only
            and not s.endswith("aitGen.c")  # For code generation only
            and not s.endswith("genApps.cc")  # For code generation only
            and not s.endswith("casOpaqueAddr.cc")  # Not sure...
            # and not s.endswith("ioBlocked.cc")  # Multithreaded impl doesn't compile?
            and "test" not in s  # Tests
            and "example" not in s  # Example code
            and "vms" not in s  # VMS sources
        ]

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


def build_generated_files():
    ait = [
        "aitGen.c",
        "aitTypes.c",
    ]
    genapps = [
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
        "genApps.cc",
    ]

    ait_sources = [f"pcas/src/gdd/{item}" for item in ait]
    ait_objs = [f'pcas/src/gdd/{item.split(".")[0]}.obj' for item in ait]

    genapps_sources = [f"pcas/src/gdd/{item}" for item in genapps]
    genapps_objs = [f'pcas/src/gdd/{item.split(".")[0]}.obj' for item in genapps]

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
    comp.link_executable(ait_objs, "pcas/src/gdd/aitGen")

    subprocess.check_call(
        [
            os.path.join(mydir, "pcas", "src", "gdd", "aitGen"),
            os.path.join(mydir, "pcas", "src", "gdd", "aitConvertGenerated.cc"),
        ],
        cwd=os.path.join(mydir, "pcas", "src", "gdd"),
    )

    comp.compile(
        sources=genapps_sources + ["pcas/src/gdd/genApps.cc"],
        output_dir=mydir,
        extra_preargs=epicscorelibs.config.get_config_var("CXXFLAGS"),
    )
    comp.link_executable(genapps_objs, "pcas/src/gdd/genApps")

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


def build_version_file():
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
            new_line = line.replace("@EPICS_PCAS_MAJOR_VERSION@", major)
            new_line = new_line.replace("@EPICS_PCAS_MINOR_VERSION@", minor)
            new_line = new_line.replace("@EPICS_PCAS_MAINTENANCE_VERSION@", maint)
            new_line = new_line.replace("@EPICS_PCAS_DEVELOPMENT_FLAG@", dev)
            dest.write(new_line)


def find_file(name, recursive=False):
    f = glob(f"**/{name}", recursive=recursive)
    if len(f) != 1:
        raise ValueError(f"Can't find unique file {name}: options were {f}")
    return f


build_version_file()
build_generated_files()
gdd_mod = build("gdd", depends=["pcas/src/gdd/aitConvertGenerated.cc", "pcas/src/gdd/gddApps.h"])
pcas_mod = build(
    "pcas",
    depends=["pcas/src/pcas/build/casVersionNum.h"],
    dsos=["epicscorelibs_pcas.lib.gdd"],
    libraries=["ws2_32"]
    if "windows" in epicscorelibs.config.get_config_var("EPICS_HOST_ARCH")
    else [],
    sources=find_file("caServer.cc", recursive=True)
    + find_file("caServerI.cc", recursive=True)
    + find_file("casCoreClient.cc", recursive=True)
    + find_file("casDGClient.cc", recursive=True)
    + find_file("casStrmClient.cc", recursive=True)
    + find_file("casPV.cc", recursive=True)
    + find_file("casPVI.cc", recursive=True)
    + find_file("casChannel.cc", recursive=True)
    + find_file("casChannelI.cc", recursive=True)
    + find_file("casAsyncIOI.cc", recursive=True)
    + find_file("casAsyncReadIO.cc", recursive=True)
    + find_file("casAsyncReadIOI.cc", recursive=True)
    + find_file("casAsyncWriteIO.cc", recursive=True)
    + find_file(
        "casAsyncWriteIOI.cpp", recursive=True
    )  # Note: incorrect in makefile, .cpp on filesystem
    + find_file("casAsyncPVExistIO.cc", recursive=True)
    + find_file(
        "casAsyncPVExistIOI.cpp", recursive=True
    )  # Note: incorrect in makefile, .cpp on filesystem
    + find_file("casAsyncPVAttachIO.cc", recursive=True)
    + find_file(
        "casAsyncPVAttachIOI.cpp", recursive=True
    )  # Note: incorrect in makefile, .cpp on filesystem
    + find_file("casEventSys.cc", recursive=True)
    + find_file("casMonitor.cc", recursive=True)
    + find_file("casMonEvent.cc", recursive=True)
    + find_file("inBuf.cc", recursive=True)
    + find_file("outBuf.cc", recursive=True)
    + find_file("casCtx.cc", recursive=True)
    + find_file("casEventMask.cc", recursive=True)
    + find_file("st/ioBlocked.cc", recursive=True)  # Exclude mt impl
    + find_file("pvExistReturn.cc", recursive=True)
    + find_file("pvAttachReturn.cc", recursive=True)
    + find_file("caNetAddr.cc", recursive=True)
    + find_file("beaconTimer.cc", recursive=True)
    + find_file("beaconAnomalyGovernor.cc", recursive=True)
    + find_file("clientBufMemoryManager.cpp", recursive=True)
    + find_file("chanIntfForPV.cc", recursive=True)
    + find_file("channelDestroyEvent.cpp", recursive=True)
    + find_file("casIntfOS.cc", recursive=True)
    + find_file("casDGIntfOS.cc", recursive=True)
    + find_file("casStreamOS.cc", recursive=True)
    + find_file("caServerIO.cc", recursive=True)
    + find_file("casIntfIO.cc", recursive=True)
    + find_file("casDGIntfIO.cc", recursive=True)
    + find_file("casStreamIO.cc", recursive=True)
    + find_file(
        "ipIgnoreEntry.cpp", recursive=True
    ),  # Note: incorrect in makefile, .cpp on filesystem
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
        "setuptools",  # needed at runtime for 'pkg_resources'
        "setuptools_dso>=2.9a1",  # 'setuptools_dso.runtime' used in 'epicscorelibs.path'
        "numpy",  # needed for epicscorelibs.ca.dbr
    ],
    packages=[
        "epicscorelibs_pcas",
    ],
    package_dir={"": os.path.join("python")},
    package_data={
        "": ["*.dll"],
    },
    x_dsos=[gdd_mod, pcas_mod],
    # x_expand=[
    #     (
    #         "pcas/src/pcas/build/casVersionNum.h@",
    #         "pcas/src/pcas/build/casVersionNum.h",
    #         ["pcas/configure/CONFIG_PCAS_VERSION"],
    #     ),
    # ],
    zip_safe=False,
)
