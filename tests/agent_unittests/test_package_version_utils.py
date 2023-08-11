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

import pytest
from testing_support.validators.validate_function_called import validate_function_called

from newrelic.common.package_version_utils import (
    NULL_VERSIONS,
    VERSION_ATTRS,
    get_package_version,
    get_package_version_tuple,
)

IS_PY38_PLUS = sys.version_info[:2] >= (3, 8)
SKIP_IF_NOT_IMPORTLIB_METADATA = pytest.mark.skipif(not IS_PY38_PLUS, reason="importlib.metadata is not supported.")
SKIP_IF_IMPORTLIB_METADATA = pytest.mark.skipif(
    IS_PY38_PLUS, reason="importlib.metadata is preferred over pkg_resources."
)


@pytest.fixture(scope="function", autouse=True)
def patched_pytest_module(monkeypatch):
    for attr in VERSION_ATTRS:
        if hasattr(pytest, attr):
            monkeypatch.delattr(pytest, attr)

    yield pytest


@pytest.mark.parametrize(
    "attr,value,expected_value",
    (
        ("version", "1.2.3.4", "1.2.3.4"),
        ("__version__", "1.3.5rc2", "1.3.5rc2"),
        ("__version_tuple__", (3, 5, 8), "3.5.8"),
        ("version_tuple", [3, 1, "0b2"], "3.1.0b2"),
    ),
)
def test_get_package_version(attr, value, expected_value):
    # There is no file/module here, so we monkeypatch
    # pytest instead for our purposes
    setattr(pytest, attr, value)
    version = get_package_version("pytest")
    assert version == expected_value
    delattr(pytest, attr)


def test_skips_version_callables():
    # There is no file/module here, so we monkeypatch
    # pytest instead for our purposes
    setattr(pytest, "version", lambda x: "1.2.3.4")
    setattr(pytest, "version_tuple", [3, 1, "0b2"])

    version = get_package_version("pytest")

    assert version == "3.1.0b2"

    delattr(pytest, "version")
    delattr(pytest, "version_tuple")


@pytest.mark.parametrize(
    "attr,value,expected_value",
    (
        ("version", "1.2.3.4", (1, 2, 3, 4)),
        ("__version__", "1.3.5rc2", (1, 3, "5rc2")),
        ("__version_tuple__", (3, 5, 8), (3, 5, 8)),
        ("version_tuple", [3, 1, "0b2"], (3, 1, "0b2")),
    ),
)
def test_get_package_version_tuple(attr, value, expected_value):
    # There is no file/module here, so we monkeypatch
    # pytest instead for our purposes
    setattr(pytest, attr, value)
    version = get_package_version_tuple("pytest")
    assert version == expected_value
    delattr(pytest, attr)


@SKIP_IF_NOT_IMPORTLIB_METADATA
@validate_function_called("importlib.metadata", "version")
def test_importlib_metadata():
    version = get_package_version("pytest")
    assert version not in NULL_VERSIONS, version


@SKIP_IF_IMPORTLIB_METADATA
@validate_function_called("pkg_resources", "get_distribution")
def test_pkg_resources_metadata():
    version = get_package_version("pytest")
    assert version not in NULL_VERSIONS, version
