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

import importlib.metadata as importlib_metadata
import sys
import warnings
from functools import lru_cache

# Need to account for 4 possible variations of version declaration specified in (rejected) PEP 396
VERSION_ATTRS = ("__version__", "version", "__version_tuple__", "version_tuple")
NULL_VERSIONS = frozenset((None, "", "0", "0.0", "0.0.0", "0.0.0.0", (0,), (0, 0), (0, 0, 0), (0, 0, 0, 0)))  # noqa: S104

# Global variable to hold importlib.metadata.packages_distributions() after it's called once
_packages_distributions = {}


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


@lru_cache
def _get_package_version(name):
    # Cached lookup helper that will avoid the cost of determining
    # a package's version more than once.
    global _packages_distributions

    module = sys.modules.get(name, None)
    version = None

    with warnings.catch_warnings(record=True):
        for attr in VERSION_ATTRS:
            try:
                version = getattr(module, attr, None)

                # Some frameworks (such as `pypdfium2`) may use a class
                # property to define the version.  Because class properties
                # are not callable we need to check if the result is
                # anything other than a string, tuple, or list.  If so,
                # we need to skip this method of version retrieval and use
                # `pkg_resources` or `importlib.metadata`.
                if version and not isinstance(version, (str, tuple, list)):
                    continue

                # Cast any version specified as a list into a tuple.
                version = tuple(version) if isinstance(version, list) else version
                if version not in NULL_VERSIONS:
                    return version
            except Exception:
                pass

    # In Python 3.10+ packages_distribution can be checked as well.
    try:
        # Cached lookup for packages_distributions() to avoid scanning the filesystem
        # every time we need to check a package verison.
        if not _packages_distributions and hasattr(importlib_metadata, "packages_distributions"):
            _packages_distributions = importlib_metadata.packages_distributions()

        # Try to grab the package's distribution name, and fallback to just the package name if we can't find it.
        distribution_names = _packages_distributions.get(name, [name])
        distribution_name = distribution_names[0]

        version = importlib_metadata.version(distribution_name)
        if version not in NULL_VERSIONS:
            return version
    except Exception:
        pass
