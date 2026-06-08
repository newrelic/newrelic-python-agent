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
VCR.py / pytest-recording fixtures for recording and replaying HTTP traffic in tests.

These fixtures wrap the ``pytest-recording`` plugin (which drives ``VCR.py``) so that tests
exercising real HTTP backends can run against pre-recorded "cassettes" instead of live
services. The first time a test runs in a recording mode, every outbound HTTP request and its
response is serialized to a YAML cassette. On later runs the cassette is replayed, so the test
does not require credentials or network access.

Usage
-----
Pull the fixtures into a test suite's conftest.py with a star import. Every fixture here is
``autouse=True``, so the import is all that is required. Nothing needs to be requested
explicitly::

    from testing_support.fixture.vcr import *  # noqa: F403

A ``pytest_collection_modifyitems`` hook then applies ``@pytest.mark.vcr`` to every collected
test in that suite, so individual tests do not need to be decorated.

Cassettes
---------
By default, the ``default_cassette_name`` fixture configures a single shared ``cassette.yaml``
in each suite's directory rather than the per-test cassette files pytest-recording uses.

Replaying
-----------------------
Replaying is as simple as running the test suite with an existing cassette file. The default
record mode is ``none``, which can also be specified to explictly run in replay mode::

    pytest tests/<suite>
    pytest tests/<suite> --record-mode=none


Recording
-----------------------
To record, run the suite with a record mode and valid backend credentials. It is recommended to
only use ``new_episodes`` to avoid recording duplicate responses in the cassette.yml file. This
also speeds up the process as only the first new interaction will be recorded, and the rest of
the tests that match will be replayed from the cassette file.::

    pytest tests/<suite> --record-mode=new_episodes # record only previously unrecorded interactions


The ``vcr_recording`` fixture exposes a boolean that can be used to check if the suite is currently
recording so suite fixtures can configure the HTTP clients with real API keys only when actually
recording. (True for any record mode other than ``none``)

Secrets such as API keys and authorization tokens are scrubbed from cassettes before they are
written by ``vcr_censored_headers``, so recorded cassettes are safe to commit. If API keys are
found unredacted, the missing header should be added to the CENSORED_HEADERS list and re-recorded.

Customizing
-----------
The settings fixtures (``vcr_censored_headers``, ``vcr_ignored_headers``, ``vcr_match_on``,
``default_cassette_name``) can be overridden in a suite's conftest.py to tailor matching,
redaction, or cassette location. ``vcr_config`` assembles them into the final VCR.py
configuration and should generally be left alone.
"""

from pathlib import Path

import pytest

# Default values for the overridable settings fixtures below
CENSORED_HEADERS = ["authorization", "x-goog-api-key"]
IGNORED_HEADERS = ["content-length", "traceparent", "tracestate", "user-agent", "x-goog-api-client"]
MATCH_ON = ["method", "scheme", "host", "port", "path", "body", "headers", "query"]


# === Settings fixtures, required and overridable ===


@pytest.fixture(autouse=True)
def vcr_censored_headers():
    """
    Header names whose values are replaced with a placeholder ("XXXXXX") in recorded cassettes.

    Use this for headers whose presence are required to match against, but whose values are secret
    or otherwise indeterminate (e.g. API keys and authorization tokens).

    Override this fixture to customize.
    """
    return CENSORED_HEADERS


@pytest.fixture(autouse=True)
def vcr_ignored_headers():
    """
    Header names dropped entirely from recorded cassettes.

    Use this for headers whose presence or value varies between runs and should not affect
    matching (e.g. ``content-length``, the agent's own ``traceparent``/``tracestate``,
    ``user-agent``).

    Override this fixture to customize.
    """
    return IGNORED_HEADERS


@pytest.fixture(autouse=True)
def vcr_match_on():
    """
    Request properties VCR.py compares to decide whether an incoming request matches a recorded
    interaction.

    Beyond VCR.py's defaults this also matches on ``body`` and ``headers``. Body matching when
    used with LLMs because the model prompt and inputs are encoded in the body. Headers are
    included as they frequently configure the way the response is returned
    (response streaming vs non-streaming, for example) and are therefore required to ensure
    the shape of the returned response matches the requested shape.

    Override this fixture to customize.
    """
    return MATCH_ON


@pytest.fixture(autouse=True)
def default_cassette_name(request):
    """
    Absolute path to the cassette for the current test, minus the ``.yaml`` extension VCR.py appends.

    Using a single cassette file allows all tests in the suite to share the same set of recorded
    interactions, massively deduplicating lines of YAML. If multiple cassetes are required,
    override this fixture to return a different file name based on some other fixture values.

    Override this fixture to customize.
    """
    return str(Path(request.fspath).parent / "cassette")


# === Informative fixtures, not required ===


@pytest.fixture(autouse=True)
def vcr_recording(record_mode):
    """
    Boolean indicating whether recording is currently enabled, meaning requests may reach the real backend.

    True for any record mode other than ``none``. Test suites can depend on this to configure their
    HTTP clients with real API keys only when recording and substitute fakes when replaying.
    """
    return record_mode.lower() != "none"


# === Infrastructure fixtures, required and not overridable ===


@pytest.fixture(autouse=True)
def vcr_config(vcr_censored_headers, vcr_ignored_headers, vcr_match_on):
    """
    Combines the overridable settings fixtures into VCR.py's final configuration.

    Override the individual settings fixtures rather than this one.
    """
    filter_headers = [(h, "XXXXXX") for h in vcr_censored_headers] + vcr_ignored_headers
    return {"filter_headers": filter_headers, "match_on": vcr_match_on}


def pytest_collection_modifyitems(items):
    """
    Pytest hook that applies the ``vcr`` marker to every collected test so pytest-recording engages automatically.
    """
    for item in items:
        item.add_marker(pytest.mark.vcr)
