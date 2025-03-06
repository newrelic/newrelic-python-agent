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
import sys
from io import StringIO as Buffer
from traceback import format_exception

import pytest

from newrelic.agent import get_linking_metadata
from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.log import NewRelicContextFormatter

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


@pytest.fixture
def log_buffer_with_stack_trace(caplog):
    buf = Buffer()

    _formatter = NewRelicContextFormatter("", datefmt="ISO8601", stack_trace_limit=None)
    _handler = logging.StreamHandler(buf)
    _handler.setFormatter(_formatter)

    _logger.addHandler(_handler)
    caplog.set_level(logging.INFO, logger=__name__)

    yield buf

    _logger.removeHandler(_handler)


class NonPrintableObject:
    def __str__(self):
        raise RuntimeError("Unable to print object.")

    __repr__ = __str__


class NonSerializableObject:
    def __str__(self):
        return f"<{self.__class__.__name__} object>"

    __repr__ = __str__


def test_newrelic_logger_min_extra_keys_no_error(log_buffer):
    extra = {"string": "foo"}
    _logger.info("Hello %s", "World", extra=extra)

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
        "entity.name": "Python Agent Test (agent_features)",
        "entity.type": "SERVICE",
        "message": "Hello World",
        "log.level": "INFO",
        "logger.name": "test_logs_in_context",
        "thread.name": "MainThread",
        "process.name": "MainProcess",
        "extra.string": "foo",
    }
    expected_extra_txn_keys = ("entity.guid", "hostname")

    for k, v in expected.items():
        assert message.pop(k) == v

    assert set(message.keys()) == set(expected_extra_txn_keys)


def test_newrelic_logger_no_error(log_buffer):
    extra = {
        "string": "foo",
        "integer": 1,
        "float": 1.23,
        "null": None,
        "array": [1, 2, 3],
        "bool": True,
        "set": {"set"},
        "non_serializable": NonSerializableObject(),
        "non_printable": NonPrintableObject(),
        "object": {"first": "bar", "second": "baz"},
    }
    _logger.info("Hello %s", "World", extra=extra)

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
        "entity.name": "Python Agent Test (agent_features)",
        "entity.type": "SERVICE",
        "message": "Hello World",
        "log.level": "INFO",
        "logger.name": "test_logs_in_context",
        "thread.name": "MainThread",
        "process.name": "MainProcess",
        "extra.string": "foo",
        "extra.integer": 1,
        "extra.float": 1.23,
        "extra.null": None,
        "extra.array": [1, 2, 3],
        "extra.bool": True,
        "extra.set": '["set"]',
        "extra.non_serializable": "<NonSerializableObject object>",
        "extra.non_printable": "<unprintable NonPrintableObject object>",
        "extra.object": {"first": "bar", "second": "baz"},
    }
    expected_extra_txn_keys = ("entity.guid", "hostname")

    for k, v in expected.items():
        assert message.pop(k) == v

    assert set(message.keys()) == set(expected_extra_txn_keys)


class ExceptionForTest(ValueError):
    pass


@background_task()
def test_newrelic_logger_error_inside_transaction_no_stack_trace(log_buffer):
    try:
        raise ExceptionForTest
    except ExceptionForTest:
        _logger.exception("oops")

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
        "entity.name": "Python Agent Test (agent_features)",
        "entity.type": "SERVICE",
        "message": "oops",
        "log.level": "ERROR",
        "logger.name": "test_logs_in_context",
        "thread.name": "MainThread",
        "process.name": "MainProcess",
        "error.class": "test_logs_in_context:ExceptionForTest",
        "error.message": "",
        "error.expected": False,
    }
    expected_extra_txn_keys = ("trace.id", "span.id", "entity.guid", "hostname")

    for k, v in expected.items():
        assert message.pop(k) == v

    assert set(message.keys()) == set(expected_extra_txn_keys)


@background_task()
def test_newrelic_logger_error_inside_transaction_with_stack_trace(log_buffer_with_stack_trace):
    try:
        try:
            raise ExceptionForTest("cause")
        except ExceptionForTest:
            raise ExceptionForTest("exception-with-cause")
    except ExceptionForTest:
        _logger.exception("oops")
        expected_stack_trace = "".join(format_exception(*sys.exc_info()))

    log_buffer_with_stack_trace.seek(0)
    message = json.load(log_buffer_with_stack_trace)

    timestamp = message.pop("timestamp")
    thread_id = message.pop("thread.id")
    process_id = message.pop("process.id")
    filename = message.pop("file.name")
    line_number = message.pop("line.number")
    stack_trace = message.pop("error.stack_trace")

    assert isinstance(timestamp, int)
    assert isinstance(thread_id, int)
    assert isinstance(process_id, int)
    assert filename.endswith("/test_logs_in_context.py")
    assert isinstance(line_number, int)
    assert isinstance(stack_trace, str)
    assert stack_trace and stack_trace == expected_stack_trace

    expected = {
        "entity.name": "Python Agent Test (agent_features)",
        "entity.type": "SERVICE",
        "message": "oops",
        "log.level": "ERROR",
        "logger.name": "test_logs_in_context",
        "thread.name": "MainThread",
        "process.name": "MainProcess",
        "error.class": "test_logs_in_context:ExceptionForTest",
        "error.message": "exception-with-cause",
        "error.expected": False,
    }
    expected_extra_txn_keys = ("trace.id", "span.id", "entity.guid", "hostname")

    for k, v in expected.items():
        assert message.pop(k) == v

    assert set(message.keys()) == set(expected_extra_txn_keys)


def test_newrelic_logger_error_outside_transaction_no_stack_trace(log_buffer):
    try:
        raise ExceptionForTest
    except ExceptionForTest:
        _logger.exception("oops")

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
        "entity.name": "Python Agent Test (agent_features)",
        "entity.type": "SERVICE",
        "message": "oops",
        "log.level": "ERROR",
        "logger.name": "test_logs_in_context",
        "thread.name": "MainThread",
        "process.name": "MainProcess",
        "error.class": "test_logs_in_context:ExceptionForTest",
        "error.message": "",
    }
    expected_extra_txn_keys = ("entity.guid", "hostname")

    for k, v in expected.items():
        assert message.pop(k) == v

    assert set(message.keys()) == set(expected_extra_txn_keys)


def test_newrelic_logger_error_outside_transaction_with_stack_trace(log_buffer_with_stack_trace):
    try:
        try:
            raise ExceptionForTest("cause")
        except ExceptionForTest:
            raise ExceptionForTest("exception-with-cause")
    except ExceptionForTest:
        _logger.exception("oops")
        expected_stack_trace = "".join(format_exception(*sys.exc_info()))

    log_buffer_with_stack_trace.seek(0)
    message = json.load(log_buffer_with_stack_trace)

    timestamp = message.pop("timestamp")
    thread_id = message.pop("thread.id")
    process_id = message.pop("process.id")
    filename = message.pop("file.name")
    line_number = message.pop("line.number")
    stack_trace = message.pop("error.stack_trace")

    assert isinstance(timestamp, int)
    assert isinstance(thread_id, int)
    assert isinstance(process_id, int)
    assert filename.endswith("/test_logs_in_context.py")
    assert isinstance(line_number, int)
    assert isinstance(stack_trace, str)
    assert stack_trace and stack_trace == expected_stack_trace

    expected = {
        "entity.name": "Python Agent Test (agent_features)",
        "entity.type": "SERVICE",
        "message": "oops",
        "log.level": "ERROR",
        "logger.name": "test_logs_in_context",
        "thread.name": "MainThread",
        "process.name": "MainProcess",
        "error.class": "test_logs_in_context:ExceptionForTest",
        "error.message": "exception-with-cause",
    }
    expected_extra_txn_keys = ("entity.guid", "hostname")

    for k, v in expected.items():
        assert message.pop(k) == v

    assert set(message.keys()) == set(expected_extra_txn_keys)


EXPECTED_KEYS_TXN = ("trace.id", "span.id", "entity.name", "entity.type", "entity.guid", "hostname")

EXPECTED_KEYS_NO_TXN = EXPECTED_KEYS_TRACE_ENDED = ("entity.name", "entity.type", "entity.guid", "hostname")


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
