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

import six
import pytest

from newrelic.api.application import application_instance as application
from newrelic.api.background_task import background_task
from newrelic.api.time_trace import record_exception

from testing_support.fixtures import (validate_transaction_exception_message,
        set_default_encoding, validate_application_exception_message,
        reset_core_stats_engine)

UNICODE_MESSAGE = u'I💜🐍'
UNICODE_ENGLISH = u'I love python'
BYTES_ENGLISH = b'I love python'
BYTES_UTF8_ENCODED = b'I\xf0\x9f\x92\x9c\xf0\x9f\x90\x8d'
INCORRECTLY_DECODED_BYTES_PY2 = u'I\u00f0\u009f\u0092\u009c\u00f0\u009f\u0090\u008d'
INCORRECTLY_DECODED_BYTES_PY3 = u"b'I\\xf0\\x9f\\x92\\x9c\\xf0\\x9f\\x90\\x8d'"
# =================== Exception messages during transaction ====================

# ---------------- Python 2

@pytest.mark.skipif(six.PY3, reason="Testing Python 2 string behavior")
@set_default_encoding('ascii')
@validate_transaction_exception_message(UNICODE_MESSAGE)
@background_task()
def test_py2_transaction_exception_message_unicode():
    """Assert unicode message when using non-ascii characters is preserved,
    with sys default encoding"""
    try:
        raise ValueError(UNICODE_MESSAGE)
    except ValueError:
        record_exception()

@pytest.mark.skipif(six.PY3, reason="Testing Python 2 string behavior")
@set_default_encoding('ascii')
@validate_transaction_exception_message(UNICODE_ENGLISH)
@background_task()
def test_py2_transaction_exception_message_unicode_english():
    """Assert unicode message when using ascii compatible characters preserved,
    with sys default encoding"""
    try:
        raise ValueError(UNICODE_ENGLISH)
    except ValueError:
        record_exception()

@pytest.mark.skipif(six.PY3, reason="Testing Python 2 string behavior")
@set_default_encoding('ascii')
@validate_transaction_exception_message(UNICODE_ENGLISH)
@background_task()
def test_py2_transaction_exception_message_bytes_english():
    """Assert byte string of ascii characters decodes sensibly"""
    try:
        raise ValueError(BYTES_ENGLISH)
    except ValueError:
        record_exception()

@pytest.mark.skipif(six.PY3, reason="Testing Python 2 string behavior")
@set_default_encoding('ascii')
@validate_transaction_exception_message(INCORRECTLY_DECODED_BYTES_PY2)
@background_task()
def test_py2_transaction_exception_message_bytes_non_english():
    """Assert known situation where (explicitly) utf-8 encoded byte string gets
    mangled when default sys encoding is ascii. THIS TEST ASSERTS THAT THE
    MESSAGE IS WRONG. We do not expect it to work now, or in the future.
    """
    try:
        raise ValueError(BYTES_UTF8_ENCODED)
    except ValueError:
        record_exception()

@pytest.mark.skipif(six.PY3, reason="Testing Python 2 string behavior")
@set_default_encoding('ascii')
@validate_transaction_exception_message(INCORRECTLY_DECODED_BYTES_PY2)
@background_task()
def test_py2_transaction_exception_message_bytes_implicit_encoding_non_english():
    """Assert known situation where (implicitly) utf-8 encoded byte string gets
    mangled when default sys encoding is ascii. THIS TEST ASSERTS THAT THE
    MESSAGE IS WRONG. We do not expect it to work now, or in the future.
    """
    try:

        # Bytes literal with non-ascii compatible characters only allowed in
        # python 2

        raise ValueError('I💜🐍')
    except ValueError:
        record_exception()

@pytest.mark.skipif(six.PY3, reason="Testing Python 2 string behavior")
@set_default_encoding('utf-8')
@validate_transaction_exception_message(UNICODE_MESSAGE)
@background_task()
def test_py2_transaction_exception_message_unicode_utf8_encoding():
    """Assert unicode error message is preserved with sys non-default utf-8
    encoding
    """
    try:
        raise ValueError(UNICODE_MESSAGE)
    except ValueError:
        record_exception()

@pytest.mark.skipif(six.PY3, reason="Testing Python 2 string behavior")
@set_default_encoding('utf-8')
@validate_transaction_exception_message(UNICODE_MESSAGE)
@background_task()
def test_py2_transaction_exception_message_bytes_utf8_encoding_non_english():
    """Assert utf-8 encoded byte produces correct exception message when sys
    encoding is also utf-8.
    """
    try:

        # Bytes literal with non-ascii compatible characters only allowed in
        # python 2

        raise ValueError('I💜🐍')
    except ValueError:
        record_exception()

# ---------------- Python 3

@pytest.mark.skipif(six.PY2, reason="Testing Python 3 string behavior")
@validate_transaction_exception_message(UNICODE_MESSAGE)
@background_task()
def test_py3_transaction_exception_message_bytes_non_english_unicode():
    """Assert (native) unicode exception message is preserved when when
    non-ascii compatible characters present"""
    try:
        raise ValueError(UNICODE_MESSAGE)
    except ValueError:
        record_exception()

@pytest.mark.skipif(six.PY2, reason="Testing Python 3 string behavior")
@validate_transaction_exception_message(UNICODE_ENGLISH)
@background_task()
def test_py3_transaction_exception_message_unicode_english():
    """Assert (native) unicode exception message is preserved, when characters
    are ascii-compatible"""
    try:
        raise ValueError(UNICODE_ENGLISH)
    except ValueError:
        record_exception()

@pytest.mark.skipif(six.PY2, reason="Testing Python 3 string behavior")
@validate_transaction_exception_message(INCORRECTLY_DECODED_BYTES_PY3)
@background_task()
def test_py3_transaction_exception_message_bytes_non_english():
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
        record_exception()

# =================== Exception messages outside transaction ====================

# ---------------- Python 2

@pytest.mark.skipif(six.PY3, reason="Testing Python 2 string behavior")
@reset_core_stats_engine()
@set_default_encoding('ascii')
@validate_application_exception_message(UNICODE_MESSAGE)
def test_py2_application_exception_message_unicode():
    """Assert unicode message when using non-ascii characters is preserved,
    with sys default encoding"""
    try:
        raise ValueError(UNICODE_MESSAGE)
    except ValueError:
        app = application()
        record_exception(application=app)

@pytest.mark.skipif(six.PY3, reason="Testing Python 2 string behavior")
@reset_core_stats_engine()
@set_default_encoding('ascii')
@validate_application_exception_message(UNICODE_ENGLISH)
def test_py2_application_exception_message_unicode_english():
    """Assert unicode message when using ascii compatible characters preserved,
    with sys default encoding"""
    try:
        raise ValueError(UNICODE_ENGLISH)
    except ValueError:
        app = application()
        record_exception(application=app)

@pytest.mark.skipif(six.PY3, reason="Testing Python 2 string behavior")
@reset_core_stats_engine()
@set_default_encoding('ascii')
@validate_application_exception_message(UNICODE_ENGLISH)
def test_py2_application_exception_message_bytes_english():
    """Assert byte string of ascii characters decodes sensibly"""
    try:
        raise ValueError(BYTES_ENGLISH)
    except ValueError:
        app = application()
        record_exception(application=app)

@pytest.mark.skipif(six.PY3, reason="Testing Python 2 string behavior")
@reset_core_stats_engine()
@set_default_encoding('ascii')
@validate_application_exception_message(INCORRECTLY_DECODED_BYTES_PY2)
def test_py2_application_exception_message_bytes_non_english():
    """Assert known situation where (explicitly) utf-8 encoded byte string gets
    mangled when default sys encoding is ascii. THIS TEST ASSERTS THAT THE
    MESSAGE IS WRONG. We do not expect it to work now, or in the future.
    """
    try:
        raise ValueError(BYTES_UTF8_ENCODED)
    except ValueError:
        app = application()
        record_exception(application=app)

@pytest.mark.skipif(six.PY3, reason="Testing Python 2 string behavior")
@reset_core_stats_engine()
@set_default_encoding('ascii')
@validate_application_exception_message(INCORRECTLY_DECODED_BYTES_PY2)
def test_py2_application_exception_message_bytes_implicit_encoding_non_english():
    """Assert known situation where (implicitly) utf-8 encoded byte string gets
    mangled when default sys encoding is ascii. THIS TEST ASSERTS THAT THE
    MESSAGE IS WRONG. We do not expect it to work now, or in the future.
    """
    try:

        # Bytes literal with non-ascii compatible characters only allowed in
        # python 2

        raise ValueError('I💜🐍')
    except ValueError:
        app = application()
        record_exception(application=app)

@pytest.mark.skipif(six.PY3, reason="Testing Python 2 string behavior")
@reset_core_stats_engine()
@set_default_encoding('utf-8')
@validate_application_exception_message(UNICODE_MESSAGE)
def test_py2_application_exception_message_unicode_utf8_encoding():
    """Assert unicode error message is preserved with sys non-default utf-8
    encoding
    """
    try:
        raise ValueError(UNICODE_MESSAGE)
    except ValueError:
        app = application()
        record_exception(application=app)

@pytest.mark.skipif(six.PY3, reason="Testing Python 2 string behavior")
@reset_core_stats_engine()
@set_default_encoding('utf-8')
@validate_application_exception_message(UNICODE_MESSAGE)
def test_py2_application_exception_message_bytes_utf8_encoding_non_english():
    """Assert utf-8 encoded byte produces correct exception message when sys
    encoding is also utf-8.
    """
    try:

        # Bytes literal with non-ascii compatible characters only allowed in
        # python 2

        raise ValueError('I💜🐍')
    except ValueError:
        app = application()
        record_exception(application=app)

# ---------------- Python 3

@pytest.mark.skipif(six.PY2, reason="Testing Python 3 string behavior")
@reset_core_stats_engine()
@validate_application_exception_message(UNICODE_MESSAGE)
def test_py3_application_exception_message_bytes_non_english_unicode():
    """Assert (native) unicode exception message is preserved when when
    non-ascii compatible characters present"""
    try:
        raise ValueError(UNICODE_MESSAGE)
    except ValueError:
        app = application()
        record_exception(application=app)

@pytest.mark.skipif(six.PY2, reason="Testing Python 3 string behavior")
@reset_core_stats_engine()
@validate_application_exception_message(UNICODE_ENGLISH)
def test_py3_application_exception_message_unicode_english():
    """Assert (native) unicode exception message is preserved, when characters
    are ascii-compatible"""
    try:
        raise ValueError(UNICODE_ENGLISH)
    except ValueError:
        app = application()
        record_exception(application=app)

@pytest.mark.skipif(six.PY2, reason="Testing Python 3 string behavior")
@reset_core_stats_engine()
@validate_application_exception_message(INCORRECTLY_DECODED_BYTES_PY3)
def test_py3_application_exception_message_bytes_non_english():
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
        record_exception(application=app)
