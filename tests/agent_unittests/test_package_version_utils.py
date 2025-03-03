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

import pytest
from testing_support.validators.validate_function_called import validate_function_called

from newrelic.common.package_version_utils import (
    NULL_VERSIONS,
    VERSION_ATTRS,
    _get_package_version,
    get_package_version,
    get_package_version_tuple,
)

# Notes:
# importlib.metadata was a provisional addition to the std library in PY38 and PY39
# while pkg_resources was deprecated.
# importlib.metadata is no longer provisional in PY310+.  It added some attributes
# such as distribution_packages and removed pkg_resources.

IS_PY38_PLUS = sys.version_info[:2] >= (3, 8)
IS_PY310_PLUS = sys.version_info[:2] >= (3, 10)
SKIP_IF_NOT_IMPORTLIB_METADATA = pytest.mark.skipif(not IS_PY38_PLUS, reason="importlib.metadata is not supported.")
SKIP_IF_IMPORTLIB_METADATA = pytest.mark.skipif(
    IS_PY38_PLUS, reason="importlib.metadata is preferred over pkg_resources."
)
SKIP_IF_NOT_PY310_PLUS = pytest.mark.skipif(not IS_PY310_PLUS, reason="These features were added in 3.10+")


@pytest.fixture(scope="function", autouse=True)
def patched_pytest_module(monkeypatch):
    for attr in VERSION_ATTRS:
        if hasattr(pytest, attr):
            monkeypatch.delattr(pytest, attr)

    yield pytest


@pytest.fixture(scope="function", autouse=True)
def cleared_package_version_cache():
    """Ensure cache is empty before every test to exercise code paths."""
    _get_package_version.cache_clear()


@pytest.mark.parametrize(
    "attr,value,expected_value",
    (
        ("version", "1.2.3.4", "1.2.3.4"),
        ("__version__", "1.3.5rc2", "1.3.5rc2"),
        ("__version_tuple__", (3, 5, 8), "3.5.8"),
        ("version_tuple", [3, 1, "0b2"], "3.1.0b2"),
    ),
)
def test_get_package_version(monkeypatch, attr, value, expected_value):
    # There is no file/module here, so we monkeypatch
    # pytest instead for our purposes
    monkeypatch.setattr(pytest, attr, value, raising=False)
    version = get_package_version("pytest")
    assert version == expected_value


def test_skips_version_callables(monkeypatch):
    # There is no file/module here, so we monkeypatch
    # pytest instead for our purposes
    monkeypatch.setattr(pytest, "version", lambda x: "1.2.3.4", raising=False)
    monkeypatch.setattr(pytest, "version_tuple", [3, 1, "0b2"], raising=False)

    version = get_package_version("pytest")

    assert version == "3.1.0b2"


@pytest.mark.parametrize(
    "attr,value,expected_value",
    (
        ("version", "1.2.3.4", (1, 2, 3, 4)),
        ("__version__", "1.3.5rc2", (1, 3, "5rc2")),
        ("__version_tuple__", (3, 5, 8), (3, 5, 8)),
        ("version_tuple", [3, 1, "0b2"], (3, 1, "0b2")),
    ),
)
def test_get_package_version_tuple(monkeypatch, attr, value, expected_value):
    # There is no file/module here, so we monkeypatch
    # pytest instead for our purposes
    monkeypatch.setattr(pytest, attr, value, raising=False)
    version = get_package_version_tuple("pytest")
    assert version == expected_value


@SKIP_IF_NOT_IMPORTLIB_METADATA
@validate_function_called("importlib.metadata", "version")
def test_importlib_metadata():
    version = get_package_version("pytest")
    assert version not in NULL_VERSIONS, version


@SKIP_IF_NOT_PY310_PLUS
@validate_function_called("importlib.metadata", "packages_distributions")
def test_mapping_import_to_distribution_packages():
    version = get_package_version("pytest")
    assert version not in NULL_VERSIONS, version


@SKIP_IF_IMPORTLIB_METADATA
@validate_function_called("pkg_resources", "get_distribution")
def test_pkg_resources_metadata():
    version = get_package_version("pytest")
    assert version not in NULL_VERSIONS, version


def _getattr_deprecation_warning(attr):
    if attr == "__version__":
        warnings.warn("Testing deprecation warnings.", DeprecationWarning)
        return "3.2.1"
    else:
        raise NotImplementedError


def test_deprecation_warning_suppression(monkeypatch, recwarn):
    # Add fake module to be deleted later
    monkeypatch.setattr(pytest, "__getattr__", _getattr_deprecation_warning, raising=False)

    assert get_package_version("pytest") == "3.2.1"

    assert not recwarn.list, "Warnings not suppressed."


def test_version_caching(monkeypatch):
    # Add fake module to be deleted later
    sys.modules["mymodule"] = sys.modules["pytest"]
    monkeypatch.setattr(pytest, "__version__", "1.0.0", raising=False)
    version = get_package_version("mymodule")
    assert version not in NULL_VERSIONS, version

    # Ensure after deleting that the call to _get_package_version still completes because of caching
    del sys.modules["mymodule"]
    version = get_package_version("mymodule")
    assert version not in NULL_VERSIONS, version


def test_version_as_class_property(monkeypatch):
    # There is no file/module here, so we monkeypatch
    # pytest instead for our purposes
    class FakeModule:
        @property
        def version(self):
            return "1.2.3"

    monkeypatch.setattr(pytest, "version", FakeModule.version, raising=False)

    version = get_package_version("pytest")
    assert version not in NULL_VERSIONS and isinstance(version, str), version


# This test checks to see if the version is a property of the class
# but also checks to see if the something like version.version_tuple
# has been exported as a tuple.
def test_version_as_class_property_and_version_tuple(monkeypatch):
    # There is no file/module here, so we monkeypatch
    # pytest instead for our purposes
    class FakeModule:
        @property
        def version(self):
            return "1.2.3"

    monkeypatch.setattr(pytest, "version", FakeModule.version, raising=False)
    monkeypatch.setattr(pytest, "version_tuple", (1, 2, 3), raising=False)

    version = get_package_version("pytest")
    assert version not in NULL_VERSIONS and isinstance(version, str), version
