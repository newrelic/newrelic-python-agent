import logging
import pytest

from newrelic.api.log import NewRelicContextFormatter

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
