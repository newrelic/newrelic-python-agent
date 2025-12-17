# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

python_version = sys.version_info[:2]

if python_version < (3, 9):
    error_msg = (
        "The New Relic Python agent only supports Python 3.9+. We recommend upgrading to a newer version of Python."
    )

    try:
        # Lookup table for the last agent versions to support each Python version.
        last_supported_version_lookup = {
            (2, 6): "3.4.0.95",
            (2, 7): "9.13.0",
            (3, 3): "3.4.0.95",
            (3, 4): "4.20.0.120",
            (3, 5): "5.24.0.153",
            (3, 6): "7.16.0.178",
            (3, 7): "10.17.0",
            (3, 8): "11.2.0",
        }
        last_supported_version = last_supported_version_lookup.get(python_version, None)

        if last_supported_version:
            python_version_str = "{}.{}".format(python_version[0], python_version[1])
            error_msg += " The last agent version to support Python {} was v{}.".format(
                python_version_str, last_supported_version
            )
    except Exception:
        pass

    raise RuntimeError(error_msg)

with_setuptools = False
is_windows = sys.platform == "win32"

try:
    from setuptools import setup

    with_setuptools = True
except ImportError:
    from distutils.core import setup

from distutils.command.build_ext import build_ext
from distutils.core import Extension
from distutils.errors import CCompilerError, DistutilsExecError, DistutilsPlatformError
from pathlib import Path

build_ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError, OSError)


class BuildExtFailed(Exception):
    pass


class optional_build_ext(build_ext):
    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError:
            raise BuildExtFailed

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except build_ext_errors:
            raise BuildExtFailed


kwargs = {
    "name": "newrelic",
    "setup_requires": ["setuptools>=61.2", "setuptools_scm>=6.4,<10"],
    "license": "Apache-2.0",
}

if not with_setuptools:
    script_directory = Path(__file__).parent
    if not script_directory:
        script_directory = Path.cwd()

    readme_file = script_directory / "README.md"

    kwargs["scripts"] = ["scripts/newrelic-admin"]

    # Old config that now lives in pyproject.toml
    # Preserved here for backwards compatibility with distutils
    packages = [
        "newrelic",
        "newrelic.admin",
        "newrelic.api",
        "newrelic.bootstrap",
        "newrelic.common",
        "newrelic.core",
        "newrelic.extras",
        "newrelic.extras.framework_django",
        "newrelic.extras.framework_django.templatetags",
        "newrelic.hooks",
        "newrelic.network",
        "newrelic.packages",
        "newrelic.packages.isort",
        "newrelic.packages.isort.stdlibs",
        "newrelic.packages.urllib3",
        "newrelic.packages.urllib3.util",
        "newrelic.packages.urllib3.contrib",
        "newrelic.packages.urllib3.contrib._securetransport",
        "newrelic.packages.urllib3.packages",
        "newrelic.packages.urllib3.packages.backports",
        "newrelic.packages.wrapt",
        "newrelic.packages.opentelemetry_proto",
        "newrelic.samplers",
    ]

    kwargs.update(
        {
            "python_requires": ">=3.9",  # python_requires is also located in pyproject.toml
            "zip_safe": False,
            "packages": packages,
            "package_data": {
                "newrelic": [
                    "newrelic.ini",
                    "packages/urllib3/LICENSE.txt",
                    "common/cacert.pem",
                    "scripts/azure-prebuild.sh",
                ]
            },
        }
    )


def run_setup(with_extensions):
    def _run_setup():
        # Create a local copy of kwargs, if there is no c compiler run_setup
        # will need to be re-run, and these arguments can not be present.

        kwargs_tmp = dict(kwargs)

        if with_extensions:
            kwargs_tmp["ext_modules"] = [
                Extension("newrelic.packages.wrapt._wrappers", ["newrelic/packages/wrapt/_wrappers.c"]),
                Extension("newrelic.core._thread_utilization", ["newrelic/core/_thread_utilization.c"]),
            ]
            kwargs_tmp["cmdclass"] = {"build_ext": optional_build_ext}

        setup(**kwargs_tmp)

    if os.environ.get("TDDIUM") is not None:
        try:
            print("INFO: Running under tddium. Use lock.")
            from lock_file import LockFile
        except ImportError:
            print("ERROR: Cannot import locking mechanism.")
            _run_setup()
        else:
            print("INFO: Attempting to create lock file.")
            with LockFile("setup.lock", wait=True):
                _run_setup()
    else:
        _run_setup()


WARNING = """
WARNING: The optional C extension components of the Python agent could
not be compiled. This can occur where a compiler is not present on the
target system or the Python installation does not have the corresponding
developer package installed. The Python agent will instead be installed
without the extensions. The consequence of this is that although the
Python agent will still run, some non core features of the Python agent,
such as capacity analysis instance busy metrics, will not be available.
Pure Python versions of code supporting some features, rather than the
optimised C versions, will also be used resulting in additional overheads.
"""

with_extensions = os.environ.get("NEW_RELIC_EXTENSIONS", None)
if with_extensions:
    if with_extensions.lower() in ["on", "true", "1"]:
        with_extensions = True
    elif with_extensions.lower() in ["off", "false", "0"]:
        with_extensions = False
    else:
        with_extensions = None

if hasattr(sys, "pypy_version_info"):
    with_extensions = False

if with_extensions is not None:
    run_setup(with_extensions=with_extensions)

else:
    try:
        run_setup(with_extensions=True)

    except BuildExtFailed:
        print(75 * "*")

        print(WARNING)
        print("INFO: Trying to build without extensions.")

        print()
        print(75 * "*")

        run_setup(with_extensions=False)

        print(75 * "*")

        print(WARNING)
        print("INFO: Only pure Python agent was installed.")

        print()
        print(75 * "*")
