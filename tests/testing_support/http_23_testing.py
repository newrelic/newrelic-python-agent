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

import niquests

VALID_HTTP_VERSIONS = frozenset((None, 1, 2, 3))
INVALID_HTTP_INPUT_WARNING = "Invalid HTTP version. Expected an integer (1, 2, or 3) or None for no specific version."
INVALID_HTTP_VERSION_USED_WARNING = "Incorrect HTTP version used: {}"


def make_request(host, port, path="", method="GET", body=None, http_version=None, timeout=10):
    assert http_version in VALID_HTTP_VERSIONS, INVALID_HTTP_INPUT_WARNING

    # Disable other HTTP connection types
    session_kwargs = {}
    if http_version == 1:
        session_kwargs["disable_http2"] = True
        session_kwargs["disable_http3"] = True
    elif http_version == 2:
        session_kwargs["disable_http1"] = True
        session_kwargs["disable_http3"] = True
    elif http_version == 3:
        # HTTP/1.1 must remain enabled to allow the session to open
        session_kwargs["disable_http2"] = True

    # Create session
    with niquests.Session(**session_kwargs) as session:
        session.verify = False  # Disable SSL verification
        if http_version == 3:
            # Preset quic cache to enable HTTP/3 connections
            session.quic_cache_layer[(host, port)] = ("", port)

        # Send Request
        response = session.request(method.upper(), f"https://{host}:{port}{path}", data=body, timeout=timeout)
        response.ok  # Ensure response is completed
        response.raise_for_status()  # Check response status code

        # Check HTTP version used was correct
        if http_version == 1:
            assert response.http_version in {10, 11}, INVALID_HTTP_VERSION_USED_WARNING.format(response.http_version)
        elif http_version == 2:
            assert response.http_version == 20, INVALID_HTTP_VERSION_USED_WARNING.format(response.http_version)
        elif http_version == 3:
            assert response.http_version == 30, INVALID_HTTP_VERSION_USED_WARNING.format(response.http_version)

        return response
