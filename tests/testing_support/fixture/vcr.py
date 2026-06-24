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

try:
    import pytest_recording

except ImportError as exc:
    raise ImportError("pytest-recording is required to use the vcr fixtures.") from exc

import json
from pathlib import Path

import pytest

# Default values for the overridable settings fixtures below
VCR_CENSORED_HEADERS = ["authorization", "cookie", "set-cookie", "x-goog-api-key"]
VCR_IGNORED_HEADERS = ["content-length", "traceparent", "tracestate", "user-agent", "x-goog-api-client"]
VCR_REPLACE_HEADERS = []  # Must be tuples of (header_name, replacement_value)
VCR_MATCH_ON = ["method", "scheme", "host", "port", "path", "body", "headers", "query"]


# === Settings fixtures, required and overridable ===


@pytest.fixture(autouse=True)
def vcr_censored_headers():
    """
    Header names whose values are replaced with a placeholder ("XXXXXX") in recorded cassettes.

    Use this for headers whose presence are required to match against, but whose values are secret
    or otherwise indeterminate (e.g. API keys and authorization tokens).

    Override this fixture to customize.
    """
    return VCR_CENSORED_HEADERS


@pytest.fixture(autouse=True)
def vcr_ignored_headers():
    """
    Header names dropped entirely from recorded cassettes.

    Use this for headers whose presence or value varies between runs and should not affect
    matching (e.g. ``content-length``, the agent's own ``traceparent``/``tracestate``,
    ``user-agent``).

    Override this fixture to customize.
    """
    return VCR_IGNORED_HEADERS


@pytest.fixture(autouse=True)
def vcr_replace_headers():
    """
    Header names whose values are replaced with a specified value in recorded cassettes.

    Use this for headers whose presence are required to match against, but whose values need to be
    replaced with a consistent value (e.g. rate limit headers).

    Override this fixture to customize.
    """
    return VCR_REPLACE_HEADERS


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
    return VCR_MATCH_ON


@pytest.fixture(autouse=True)
def vcr_before_record_request():
    """
    VCR.py hook that is called before every request is recorded.

    Use this to modify the request (e.g. to redact secrets in the body) before it is written to
    the cassette. Note that this only affects what is recorded, not what is matched against when
    replaying.

    Override this fixture to customize.
    """
    return None  # Return a function to set this


@pytest.fixture(autouse=True)
def vcr_before_record_response():
    """
    VCR.py hook that is called before every response is recorded.

    Use this to modify the response (e.g. to redact secrets in the body) before it is written to
    the cassette. Note that this only affects what is recorded, not what is matched against when
    replaying.

    Override this fixture to customize.
    """
    return None  # Return a function to set this


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
def vcr_config(
    vcr_censored_headers,
    vcr_ignored_headers,
    vcr_replace_headers,
    vcr_match_on,
    vcr_before_record_request,
    vcr_before_record_response,
):
    """
    Combines the overridable settings fixtures into VCR.py's final configuration.

    Override the individual settings fixtures rather than this one.
    """
    filter_headers = (
        [(h, "XXXXXX") for h in vcr_censored_headers]
        + [(h, str(v)) for h, v in vcr_replace_headers]
        + vcr_ignored_headers
    )
    config = {"filter_headers": filter_headers, "match_on": vcr_match_on, "decode_compressed_response": True}
    config["before_record_response"] = _build_before_record_response(vcr_before_record_response, filter_headers)
    if vcr_before_record_request:
        config["before_record_request"] = vcr_before_record_request
    return config


def _build_before_record_response(wrapped=None, filter_headers=None):
    """
    Wrap a user-defined before_record_response function to also apply additional global logic.
    """

    def before_record_response(response):
        # Grab Content-Type and charset to attempt to load the body
        _, content_type = _get_header(response["headers"], "content-type")
        if ";" in content_type:
            charset = content_type.split(";")[1].split("=")[1].lower().strip()
            content_type = content_type.split(";")[0].strip()
        else:
            charset = "utf-8"

        if content_type and content_type.casefold() == "application/json":
            # Load body from JSON encoded with charset, then dump back to minified JSON and re-encode with charset for recording.
            # This makes recorded cassettes easier to read and diff by removing unnecessary whitespace that doesn't render well.
            loaded_body = json.loads(response["body"]["string"].decode(charset))
            response["body"]["string"] = json.dumps(loaded_body, indent=None).encode(charset)

        # Filter response headers the same way that request headers are filtered
        if filter_headers:
            for _header in filter_headers:
                # Unpack filters
                if isinstance(_header, (tuple, list)):
                    header, value = _header
                else:
                    header = _header
                    value = None

                # Replace or drop headers
                recorded_header, _ = _get_header(response["headers"], header)
                if recorded_header:
                    if value is not None:
                        response["headers"][recorded_header] = [value]
                    else:
                        response["headers"].pop(recorded_header, None)

        # Run the wrapped copy of before_record_response
        if wrapped:
            response = wrapped(response)

        return response

    return before_record_response


def _get_header(headers, name):
    """Lookup a header case-insensitively and return the actual header name and value."""
    for key in headers:
        if key.casefold() == name.casefold():
            return key, headers[key][0]

    return None, None


def pytest_collection_modifyitems(items):
    """
    Pytest hook that applies the ``vcr`` marker to every collected test so pytest-recording engages automatically.
    """
    for item in items:
        item.add_marker(pytest.mark.vcr)
