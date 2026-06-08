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

"""
Usage:

from testing_support.fixture.vcr import *

"""

from pathlib import Path

import pytest

CENSORED_HEADERS = ["authorization", "x-goog-api-key"]
IGNORED_HEADERS = ["content-length", "traceparent", "tracestate", "user-agent", "x-goog-api-client"]
MATCH_ON = ["method", "scheme", "host", "port", "path", "body", "headers", "query"]


# === Settings fixtures, required and overridable ===


@pytest.fixture(autouse=True)
def vcr_censored_headers():
    """
    Headers whose values are replaced with a placeholder in recorded cassettes.
    This is useful to match requests that have these headers present, but whose values are indeterminate.
    Override to customize.
    """
    return CENSORED_HEADERS


@pytest.fixture(autouse=True)
def vcr_ignored_headers():
    """
    Headers dropped entirely from recorded cassettes.
    This is useful to match requests that may or may not have these headers present.
    Override to customize.
    """
    return IGNORED_HEADERS


@pytest.fixture(autouse=True)
def vcr_match_on():
    """Request properties VCR.py uses to match against recorded cassettes. Override to customize."""
    return MATCH_ON


@pytest.fixture(autouse=True)
def default_cassette_name(request):
    """Default cassette name is cassette.yaml in each test suite. Override to customize."""
    return str(Path(request.fspath).parent / "cassette")


# === Informative fixtures, not required ===


@pytest.fixture(autouse=True)
def vcr_recording(record_mode):
    """This fixture provides a boolean check for whether or not recording is enabled, based on the record_mode."""
    return record_mode.lower() != "none"


# === Infrastructure fixtures, required and not overridable ===


@pytest.fixture(autouse=True)
def vcr_config(vcr_censored_headers, vcr_ignored_headers, vcr_match_on):
    """VCR.py configuration passed to the pytest-recording plugin. Not recommended to override directly."""
    filter_headers = [(h, "XXXXXX") for h in vcr_censored_headers] + vcr_ignored_headers
    return {"filter_headers": filter_headers, "match_on": vcr_match_on}


def pytest_collection_modifyitems(items):
    """Apply the vcr marker to every collected test so pytest-recording engages."""
    for item in items:
        item.add_marker(pytest.mark.vcr)
