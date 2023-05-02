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

import sys

# Need to account for 4 possible variations of version declaration specified in (rejected) PEP 396
VERSION_ATTRS = ("__version__", "version", "__version_tuple__", "version_tuple")  # nosec
NULL_VERSIONS = frozenset((None, "", "0", "0.0", "0.0.0", "0.0.0.0", (0,), (0, 0), (0, 0, 0), (0, 0, 0, 0)))  # nosec


def get_package_version(name):
    """Gets the version string of the library.
    :param name: The name of library.
    :type name: str
    :return: The version of the library. Returns None if can't determine version.
    :type return: str or None

    Usage::
        >>> get_package_version("botocore")
                "1.1.0"
    """

    version = _get_package_version(name)

    # Coerce iterables into a string
    if isinstance(version, tuple):
        version = ".".join(str(v) for v in version)

    return version


def get_package_version_tuple(name):
    """Gets the version tuple of the library.
    :param name: The name of library.
    :type name: str
    :return: The version of the library. Returns None if can't determine version.
    :type return: tuple or None

    Usage::
        >>> get_package_version_tuple("botocore")
                (1, 1, 0)
    """

    def int_or_str(value):
        try:
            return int(value)
        except Exception:
            return str(value)

    version = _get_package_version(name)

    # Split "." separated strings and cast fields to ints
    if isinstance(version, str):
        version = tuple(int_or_str(v) for v in version.split("."))

    return version


def _get_package_version(name):
    module = sys.modules.get(name, None)
    version = None
    for attr in VERSION_ATTRS:
        try:
            version = getattr(module, attr, None)
            # Cast any version specified as a list into a tuple.
            version = tuple(version) if isinstance(version, list) else version
            if version not in NULL_VERSIONS:
                return version
        except Exception:
            pass

    # importlib was introduced into the standard library starting in Python3.8.
    if "importlib" in sys.modules and hasattr(sys.modules["importlib"], "metadata"):
        try:
            version = sys.modules["importlib"].metadata.version(name)  # pylint: disable=E1101
            if version not in NULL_VERSIONS:
                return version
        except Exception:
            pass

    if "pkg_resources" in sys.modules:
        try:
            version = sys.modules["pkg_resources"].get_distribution(name).version
            if version not in NULL_VERSIONS:
                return version
        except Exception:
            pass