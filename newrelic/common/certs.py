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

"""This module returns the CA certificate bundle from certifi if installed."""

import logging
from pathlib import Path

_logger = logging.getLogger(__name__)

SSL_CERTS_ERROR_MESSAGE = (
    "SSL certificates are required and could not be found, and certifi does not appear to be installed. "
    "Please install SSL certificates using your system package manager or install "
    "newrelic with the certificates extra using pip to resolve this issue. "
    "(eg. pip install newrelic[certificates])"
)


def where():
    try:
        import certifi

        return Path(certifi.where())
    except Exception:
        _logger.exception(SSL_CERTS_ERROR_MESSAGE)
