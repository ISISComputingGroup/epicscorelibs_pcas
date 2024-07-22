#!/usr/bin/env python

from __future__ import print_function

import os
import subprocess
import sys
from glob import glob

from setuptools_dso import DSO, setup
from setuptools_dso.compiler import new_compiler

mydir = os.path.abspath(os.path.dirname(__file__))

# I will use some of what I'm about to install
sys.path.insert(0, os.path.join(mydir, "src", "python"))

import epicscorelibs.path
from epicscorelibs.config import get_config_var

os.add_dll_directory(epicscorelibs.path.lib_path)


def build(lib_name, sources=None, depends=None, dsos=None):
    if not sources:
        sources = glob(f"pcas/src/{lib_name}/**/*.c") + glob(f"pcas/src/{lib_name}/**/*.cc")

        # Generated cc which is only actually used in includes (can't build by itself)
        sources = [
            s
            for s in sources
            if not s.endswith("aitConvertGenerated.cc")
            and not s.endswith("aitGen.c")
            and not s.endswith("genApps.cc")
            and not s.endswith("casOpaqueAddr.cc")
            and "test" not in s
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
        ],
        library_dirs=[epicscorelibs.path.lib_path],
        dsos=dsos or [],
        libraries=["Com", "ca"],
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


build_version_file()
build_generated_files()
gdd_mod = build("gdd", depends=["pcas/src/gdd/aitConvertGenerated.cc", "pcas/src/gdd/gddApps.h"])
pcas_mod = build("pcas", depends=["pcas/src/pcas/build/casVersionNum.h"])

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
