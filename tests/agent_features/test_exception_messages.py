# -*- coding: utf-8 -*-
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

from testing_support.fixtures import (
    reset_core_stats_engine,
    validate_application_exception_message,
    validate_transaction_exception_message,
)

from newrelic.api.application import application_instance as application
from newrelic.api.background_task import background_task
from newrelic.api.time_trace import notice_error

UNICODE_MESSAGE = "I💜🐍"
UNICODE_ENGLISH = "I love python"
BYTES_ENGLISH = b"I love python"
BYTES_UTF8_ENCODED = b"I\xf0\x9f\x92\x9c\xf0\x9f\x90\x8d"
INCORRECTLY_DECODED_BYTES_PY2 = "I\u00f0\u009f\u0092\u009c\u00f0\u009f\u0090\u008d"
INCORRECTLY_DECODED_BYTES_PY3 = "b'I\\xf0\\x9f\\x92\\x9c\\xf0\\x9f\\x90\\x8d'"

# =================== Exception messages during transaction ====================


@validate_transaction_exception_message(UNICODE_MESSAGE)
@background_task()
def test_transaction_exception_message_bytes_non_english_unicode():
    """Assert (native) unicode exception message is preserved when when
    non-ascii compatible characters present"""
    try:
        raise ValueError(UNICODE_MESSAGE)
    except ValueError:
        notice_error()


@validate_transaction_exception_message(UNICODE_ENGLISH)
@background_task()
def test_transaction_exception_message_unicode_english():
    """Assert (native) unicode exception message is preserved, when characters
    are ascii-compatible"""
    try:
        raise ValueError(UNICODE_ENGLISH)
    except ValueError:
        notice_error()


@validate_transaction_exception_message(INCORRECTLY_DECODED_BYTES_PY3)
@background_task()
def test_transaction_exception_message_bytes_non_english():
    """An issue can occur if you cast from bytes to a string in
    python 3 (that is using str(), not using encode/decode methods).
    This is because all characters in bytes are literals, no implicit
    decoding happens, like it does in python 2. You just shouldn't use bytes
    for exception messages in Python 3. THIS TEST ASSERTS THAT THE
    MESSAGE IS WRONG. We do not expect it to work now, or in the future.
    """
    try:
        raise ValueError(BYTES_UTF8_ENCODED)
    except ValueError:
        notice_error()


# =================== Exception messages outside transaction ====================


@reset_core_stats_engine()
@validate_application_exception_message(UNICODE_MESSAGE)
def test_application_exception_message_bytes_non_english_unicode():
    """Assert (native) unicode exception message is preserved when when
    non-ascii compatible characters present"""
    try:
        raise ValueError(UNICODE_MESSAGE)
    except ValueError:
        app = application()
        notice_error(application=app)


@reset_core_stats_engine()
@validate_application_exception_message(UNICODE_ENGLISH)
def test_application_exception_message_unicode_english():
    """Assert (native) unicode exception message is preserved, when characters
    are ascii-compatible"""
    try:
        raise ValueError(UNICODE_ENGLISH)
    except ValueError:
        app = application()
        notice_error(application=app)


@reset_core_stats_engine()
@validate_application_exception_message(INCORRECTLY_DECODED_BYTES_PY3)
def test_application_exception_message_bytes_non_english():
    """It really makes a mess of things when you cast from bytes to a
    string in python 3 (that is using str(), not using encode/decode methods).
    This is because all characters in bytes are literals, no implicit
    decoding happens, like it does in python 2. You just shouldn't use bytes
    for exception messages in Python 3. THIS TEST ASSERTS THAT THE
    MESSAGE IS WRONG. We do not expect it to work now, or in the future.
    """
    try:
        raise ValueError(BYTES_UTF8_ENCODED)
    except ValueError:
        app = application()
        notice_error(application=app)


@reset_core_stats_engine()
@validate_application_exception_message("My custom message")
def test_nr_message_exception_attr_override():
    """Override the message using the _nr_message attribute."""
    try:
        raise ValueError("Original error message")
    except ValueError as e:
        e._nr_message = "My custom message"
        app = application()
        notice_error(application=app)
