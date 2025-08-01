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

from pathlib import Path

python_version = sys.version_info[:2]

if python_version >= (3, 7):
    pass
else:
    error_msg = (
        "The New Relic Python agent only supports Python 3.7+. We recommend upgrading to a newer version of Python."
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
        }
        last_supported_version = last_supported_version_lookup.get(python_version, None)

        if last_supported_version:
            python_version_str = "%s.%s" % (python_version[0], python_version[1])
            error_msg += " The last agent version to support Python %s was v%s." % (
                python_version_str,
                last_supported_version,
            )
    except Exception:
        pass

    raise RuntimeError(error_msg)

with_setuptools = False

try:
    from setuptools import setup

    with_setuptools = True
except ImportError:
    from distutils.core import setup

from distutils.command.build_ext import build_ext
from distutils.core import Extension
from distutils.errors import CCompilerError, DistutilsExecError, DistutilsPlatformError


def newrelic_agent_guess_next_version(tag_version):
    if hasattr(tag_version, "tag"):  # For setuptools_scm 7.0+
        tag_version = tag_version.tag

    version, _, _ = str(tag_version).partition("+")
    version_info = list(map(int, version.split(".")))
    if len(version_info) < 3:
        return version
    version_info[1] += 1
    version_info[2] = 0
    return ".".join(map(str, version_info))


def newrelic_agent_next_version(version):
    if version.exact:
        return version.format_with("{tag}")
    else:
        return version.format_next_version(newrelic_agent_guess_next_version, fmt="{guessed}")


script_directory = Path(__file__).parent

readme_file = script_directory / "README.md"
with readme_file.open() as f:
    readme_file_contents = f.read()

if sys.platform == "win32" and python_version > (2, 6):
    build_ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError, IOError)
else:
    build_ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError)


class BuildExtFailed(Exception):
    pass


class optional_build_ext(build_ext):
    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError:
            raise BuildExtFailed()

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except build_ext_errors:
            raise BuildExtFailed()


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
    "newrelic/packages",
    "newrelic/packages/isort",
    "newrelic/packages/isort/stdlibs",
    "newrelic/packages/urllib3",
    "newrelic/packages/urllib3/util",
    "newrelic/packages/urllib3/contrib",
    "newrelic/packages/urllib3/contrib/_securetransport",
    "newrelic/packages/urllib3/packages",
    "newrelic/packages/urllib3/packages/backports",
    "newrelic/packages/wrapt",
    "newrelic/packages/opentelemetry_proto",
    "newrelic.samplers",
]

classifiers = [
    "Development Status :: 5 - Production/Stable",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
    "Topic :: System :: Monitoring",
]

kwargs = dict(
    name="newrelic",
    use_scm_version={
        "version_scheme": newrelic_agent_next_version,
        "local_scheme": "no-local-version",
        "git_describe_command": "git describe --dirty --tags --long --match *.*.*",
        "write_to": "newrelic/version.txt",
    },
    setup_requires=["setuptools_scm>=3.2,<9"],
    description="New Relic Python Agent",
    long_description=readme_file_contents,
    long_description_content_type="text/markdown",
    url="https://docs.newrelic.com/docs/apm/agents/python-agent/",
    project_urls={"Source": "https://github.com/newrelic/newrelic-python-agent"},
    author="New Relic",
    author_email="support@newrelic.com",
    maintainer="New Relic",
    maintainer_email="support@newrelic.com",
    license="Apache-2.0",
    zip_safe=False,
    classifiers=classifiers,
    packages=packages,
    python_requires=">=3.7",
    package_data={
        "newrelic": ["newrelic.ini", "version.txt", "packages/urllib3/LICENSE.txt", "common/cacert.pem", "scripts/azure-prebuild.sh"],
    },
    extras_require={"infinite-tracing": ["grpcio", "protobuf"]},
)

if with_setuptools:
    kwargs["entry_points"] = {
        "console_scripts": ["newrelic-admin = newrelic.admin:main"],
    }
else:
    kwargs["scripts"] = ["scripts/newrelic-admin"]


def with_librt():
    try:
        if sys.platform.startswith("linux"):
            import ctypes.util

            return ctypes.util.find_library("rt")
    except Exception:
        pass


def run_setup(with_extensions):
    def _run_setup():
        # Create a local copy of kwargs, if there is no c compiler run_setup
        # will need to be re-run, and these arguments can not be present.

        kwargs_tmp = dict(kwargs)

        if with_extensions:
            monotonic_libraries = []
            if with_librt():
                monotonic_libraries = ["rt"]

            kwargs_tmp["ext_modules"] = [
                Extension("newrelic.packages.wrapt._wrappers", ["newrelic/packages/wrapt/_wrappers.c"]),
                Extension(
                    "newrelic.common._monotonic", ["newrelic/common/_monotonic.c"], libraries=monotonic_libraries
                ),
                Extension("newrelic.core._thread_utilization", ["newrelic/core/_thread_utilization.c"]),
            ]
            kwargs_tmp["cmdclass"] = dict(build_ext=optional_build_ext)

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
    if with_extensions.lower() == "true":
        with_extensions = True
    elif with_extensions.lower() == "false":
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
