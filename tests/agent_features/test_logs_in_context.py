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

import json
import logging

import pytest

from newrelic.agent import get_linking_metadata
from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.log import NewRelicContextFormatter
from newrelic.packages import six

if six.PY2:
    from io import BytesIO as Buffer
else:
    from io import StringIO as Buffer

_logger = logging.getLogger(__name__)


@pytest.fixture
def log_buffer(caplog):
    buf = Buffer()

    _formatter = NewRelicContextFormatter("", datefmt="ISO8601")
    _handler = logging.StreamHandler(buf)
    _handler.setFormatter(_formatter)

    _logger.addHandler(_handler)
    caplog.set_level(logging.INFO, logger=__name__)

    yield buf

    _logger.removeHandler(_handler)


class NonPrintableObject(object):
    def __str__(self):
        raise RuntimeError("Unable to print object.")

    def __repr__(self):
        raise RuntimeError("Unable to print object.")


def test_newrelic_logger_no_error(log_buffer):
    extra = {
        "string": "foo",
        "integer": 1,
        "float": 1.23,
        "null": None,
        "array": [1, 2, 3],
        "bool": True,
        "non_serializable": {"set"},
        "non_printable": NonPrintableObject(),
        "object": {
            "first": "bar",
            "second": "baz",
        },
    }
    _logger.info(u"Hello %s", u"World", extra=extra)

    log_buffer.seek(0)
    message = json.load(log_buffer)

    timestamp = message.pop("timestamp")
    thread_id = message.pop("thread.id")
    process_id = message.pop("process.id")
    filename = message.pop("file.name")
    line_number = message.pop("line.number")

    assert isinstance(timestamp, int)
    assert isinstance(thread_id, int)
    assert isinstance(process_id, int)
    assert filename.endswith("/test_logs_in_context.py")
    assert isinstance(line_number, int)

    expected = {
        u"entity.name": u"Python Agent Test (agent_features)",
        u"entity.type": u"SERVICE",
        u"message": u"Hello World",
        u"log.level": u"INFO",
        u"logger.name": u"test_logs_in_context",
        u"thread.name": u"MainThread",
        u"process.name": u"MainProcess",
        u"extra.string": u"foo",
        u"extra.integer": 1,
        u"extra.float": 1.23,
        u"extra.null": None,
        u"extra.array": [1, 2, 3],
        u"extra.bool": True,
        u"extra.non_serializable": u"set(['set'])" if six.PY2 else u"{'set'}",
        u"extra.non_printable": u"<unprintable NonPrintableObject object>",
        u"extra.object": {
            u"first": u"bar",
            u"second": u"baz",
        },
    }
    expected_extra_txn_keys = (
        "entity.guid",
        "hostname",
    )

    for k, v in expected.items():
        assert message.pop(k) == v

    assert set(message.keys()) == set(expected_extra_txn_keys)



class ExceptionForTest(ValueError):
    pass


@background_task()
def test_newrelic_logger_error_inside_transaction(log_buffer):
    try:
        raise ExceptionForTest
    except ExceptionForTest:
        _logger.exception(u"oops")

    log_buffer.seek(0)
    message = json.load(log_buffer)

    timestamp = message.pop("timestamp")
    thread_id = message.pop("thread.id")
    process_id = message.pop("process.id")
    filename = message.pop("file.name")
    line_number = message.pop("line.number")

    assert isinstance(timestamp, int)
    assert isinstance(thread_id, int)
    assert isinstance(process_id, int)
    assert filename.endswith("/test_logs_in_context.py")
    assert isinstance(line_number, int)

    expected = {
        u"entity.name": u"Python Agent Test (agent_features)",
        u"entity.type": u"SERVICE",
        u"message": u"oops",
        u"log.level": u"ERROR",
        u"logger.name": u"test_logs_in_context",
        u"thread.name": u"MainThread",
        u"process.name": u"MainProcess",
        u"error.class": u"test_logs_in_context:ExceptionForTest",
        u"error.message": u"",
        u"error.expected": False,
    }
    expected_extra_txn_keys = (
        "trace.id",
        "span.id",
        "entity.guid",
        "hostname",
    )

    for k, v in expected.items():
        assert message.pop(k) == v

    assert set(message.keys()) == set(expected_extra_txn_keys)


def test_newrelic_logger_error_outside_transaction(log_buffer):
    try:
        raise ExceptionForTest
    except ExceptionForTest:
        _logger.exception(u"oops")

    log_buffer.seek(0)
    message = json.load(log_buffer)

    timestamp = message.pop("timestamp")
    thread_id = message.pop("thread.id")
    process_id = message.pop("process.id")
    filename = message.pop("file.name")
    line_number = message.pop("line.number")

    assert isinstance(timestamp, int)
    assert isinstance(thread_id, int)
    assert isinstance(process_id, int)
    assert filename.endswith("/test_logs_in_context.py")
    assert isinstance(line_number, int)

    expected = {
        u"entity.name": u"Python Agent Test (agent_features)",
        u"entity.type": u"SERVICE",
        u"message": u"oops",
        u"log.level": u"ERROR",
        u"logger.name": u"test_logs_in_context",
        u"thread.name": u"MainThread",
        u"process.name": u"MainProcess",
        u"error.class": u"test_logs_in_context:ExceptionForTest",
        u"error.message": u"",
    }
    expected_extra_txn_keys = (
        "entity.guid",
        "hostname",
    )

    for k, v in expected.items():
        assert message.pop(k) == v

    assert set(message.keys()) == set(expected_extra_txn_keys)



EXPECTED_KEYS_TXN = (
    "trace.id",
    "span.id",
    "entity.name",
    "entity.type",
    "entity.guid",
        "hostname",
)

EXPECTED_KEYS_NO_TXN = EXPECTED_KEYS_TRACE_ENDED = (
    "entity.name",
    "entity.type",
    "entity.guid",
    "hostname",
)


def validate_metadata(metadata, expected):
    for key in expected:
        assert key in metadata, key
        assert metadata[key], metadata[key]
    for key in metadata.keys():
        assert key in expected, key


@background_task(name="test_get_linking_metadata_api")
def test_get_linking_metadata_api_inside_transaction():
    with FunctionTrace("test_linking_metadata") as trace:
        metadata = trace.get_linking_metadata()
        validate_metadata(metadata, EXPECTED_KEYS_TXN)
    metadata = trace.get_linking_metadata()
    validate_metadata(metadata, EXPECTED_KEYS_TRACE_ENDED)


def test_get_linking_metadata_api_outside_transaction():
    metadata = get_linking_metadata()
    validate_metadata(metadata, EXPECTED_KEYS_NO_TXN)
