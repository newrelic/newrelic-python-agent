import logging
import pytest

from newrelic.api.log import NewRelicContextFormatter
from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace
from newrelic.agent import get_linking_metadata

try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

_logger = logging.getLogger(__name__)


@pytest.fixture
def log_buffer(caplog):
    buf = StringIO()

    _formatter = NewRelicContextFormatter('%(module)s %(message)s')
    _handler = logging.StreamHandler(buf)
    _handler.setFormatter(_formatter)

    _logger.addHandler(_handler)
    caplog.set_level(logging.INFO, logger=__name__)

    yield buf

    _logger.removeHandler(_handler)


def test_newrelic_logger(log_buffer):
    _logger.info(u"Hello World")

    log_buffer.seek(0)
    text = log_buffer.read()

    assert text == 'test_logs_in_context Hello World\n'


EXPECTED_KEYS_TXN = [
    "trace.id",
    "span.id",
    "entity.name",
    "entity.type",
    "entity.guid",
    "hostname",
]

EXPECTED_KEYS_TRACE_ENDED = ["entity.type", "hostname"]

EXPECTED_KEYS_NO_TXN = ["entity.type", "hostname"]


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
