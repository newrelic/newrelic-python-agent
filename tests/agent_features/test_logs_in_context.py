import json
import logging
import pytest

from newrelic.api.log import NewRelicContextFormatter
from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace
from newrelic.agent import get_linking_metadata
import newrelic.packages.six as six

if six.PY2:
    from io import BytesIO as Buffer
else:
    from io import StringIO as Buffer

_logger = logging.getLogger(__name__)


@pytest.fixture
def log_buffer(caplog):
    buf = Buffer()

    _formatter = NewRelicContextFormatter('%(module)s %(message)s')
    _handler = logging.StreamHandler(buf)
    _handler.setFormatter(_formatter)

    _logger.addHandler(_handler)
    caplog.set_level(logging.INFO, logger=__name__)

    yield buf

    _logger.removeHandler(_handler)


def test_newrelic_logger_no_error(log_buffer):
    _logger.info(u"Hello %s", u"World")

    log_buffer.seek(0)
    message = json.load(log_buffer)

    timestamp = message.pop("timestamp")
    thread_id = message.pop("thread.id")
    filename = message.pop("file.name")
    line_number = message.pop("line.number")

    assert type(timestamp) is int
    assert type(thread_id) is int
    assert filename.endswith("/test_logs_in_context.py")
    assert type(line_number) is int

    assert message == {
        u"entity.type": u"SERVICE",
        u"message": u"Hello World",
        u"log.level": u"INFO",
        u"logger.name": u"test_logs_in_context",
        u"thread.name": u"MainThread",
    }


class TestException(ValueError):
    pass


def test_newrelic_logger_error(log_buffer):
    try:
        raise TestException
    except TestException:
        _logger.exception(u"oops")

    log_buffer.seek(0)
    message = json.load(log_buffer)

    timestamp = message.pop("timestamp")
    thread_id = message.pop("thread.id")
    filename = message.pop("file.name")
    line_number = message.pop("line.number")

    assert type(timestamp) is int
    assert type(thread_id) is int
    assert filename.endswith("/test_logs_in_context.py")
    assert type(line_number) is int

    assert message == {
        u"entity.type": u"SERVICE",
        u"message": u"oops",
        u"log.level": u"ERROR",
        u"logger.name": u"test_logs_in_context",
        u"thread.name": u"MainThread",
        u"error.class": u"test_logs_in_context.TestException",
        u"error.message": u"",
    }


EXPECTED_KEYS_TXN = (
    "trace.id",
    "span.id",
    "entity.name",
    "entity.type",
    "entity.guid",
)

EXPECTED_KEYS_NO_TXN = EXPECTED_KEYS_TRACE_ENDED = ("entity.type",)


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
