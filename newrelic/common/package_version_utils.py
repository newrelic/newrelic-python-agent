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
import warnings
from functools import lru_cache

# Need to account for 4 possible variations of version declaration specified in (rejected) PEP 396
VERSION_ATTRS = ("__version__", "version", "__version_tuple__", "version_tuple")
NULL_VERSIONS = frozenset((None, "", "0", "0.0", "0.0.0", "0.0.0.0", (0,), (0, 0), (0, 0, 0), (0, 0, 0, 0)))  # noqa: S104


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


@lru_cache()
def _get_package_version(name):
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

    importlib_metadata = None
    # importlib.metadata was introduced into the standard library starting in Python 3.8.
    importlib_metadata = getattr(sys.modules.get("importlib", None), "metadata", None)
    if importlib_metadata is None:
        # importlib_metadata is a backport library installable from PyPI.
        try:
            import importlib_metadata
        except ImportError:
            pass

    if importlib_metadata is not None:
        try:
            # In Python 3.10+ packages_distribution can be checked for as well.
            if hasattr(importlib_metadata, "packages_distributions"):
                distributions = importlib_metadata.packages_distributions()
                distribution_name = distributions.get(name, name)
                distribution_name = distribution_name[0] if isinstance(distribution_name, list) else distribution_name
            else:
                distribution_name = name

            version = importlib_metadata.version(distribution_name)
            if version not in NULL_VERSIONS:
                return version
        except Exception:
            pass

    # Fallback to pkg_resources, which is available in older versions of setuptools.
    if "pkg_resources" in sys.modules:
        try:
            version = sys.modules["pkg_resources"].get_distribution(name).version
            if version not in NULL_VERSIONS:
                return version
        except Exception:
            pass
