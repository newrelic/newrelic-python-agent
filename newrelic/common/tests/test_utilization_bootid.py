import mock
import pytest
import newrelic.packages.six as six

from newrelic.core.stats_engine import CustomMetrics
from newrelic.core.internal_metrics import InternalTraceContext
import newrelic.common.system_info as si


@pytest.fixture
def validate_error_metric_forgone():
    internal_metrics = CustomMetrics()
    with InternalTraceContext(internal_metrics):
        yield

    assert list(internal_metrics.metrics()) == []


@pytest.fixture
def validate_error_metric_exists():
    internal_metrics = CustomMetrics()
    with InternalTraceContext(internal_metrics):
        yield

    assert 'Supportability/utilization/boot_id/error' in internal_metrics


@pytest.fixture
def linux_platform():
    original = si.sys.platform
    si.sys.platform = 'linux'
    yield
    si.sys.platform = original


@pytest.fixture
def non_linux_platform():
    original = si.sys.platform
    si.sys.platform = 'Teletype Model 43'
    yield
    si.sys.platform = original


# Test file fetch

example_bootid_file = b'12de7c83-742b-4d8c-9870-7d2627980875'


def _bind_open(name, *args, **kwargs):
    return name


def test_fetch_file_exists_on_linux(linux_platform,
        validate_error_metric_forgone):

    fake_open = mock.mock_open(read_data=example_bootid_file)
    lines = [l.encode('utf-8')
            for l in example_bootid_file.decode('utf-8').split('\n')]
    file_iter = iter(lines)

    # come on python... seriously?
    fake_open.return_value.__iter__ = lambda self: file_iter
    fake_open.return_value.readline = lambda: next(file_iter)

    with mock.patch('newrelic.common.system_info.open', fake_open,
            create=True):
        result = si.BootIdUtilization.fetch()

    # check that open is called once
    assert fake_open.call_count == 1

    # check that the correct file was opened
    args, kwargs = fake_open.call_args
    name = _bind_open(*args, **kwargs)
    assert name == '/proc/sys/kernel/random/boot_id'

    # check that the correct line was processed
    assert result == '12de7c83-742b-4d8c-9870-7d2627980875'


def test_fetch_file_missing_on_linux(linux_platform,
        validate_error_metric_exists):

    fake_open = mock.mock_open(read_data=example_bootid_file)
    if six.PY3:
        fake_open.side_effect = FileNotFoundError # NOQA
    else:
        fake_open.side_effect = IOError

    with mock.patch('newrelic.common.system_info.open', fake_open,
            create=True):
        result = si.BootIdUtilization.fetch()

    # check that open is called once
    assert fake_open.call_count == 1

    # check that the correct file was opened
    args, kwargs = fake_open.call_args
    name = _bind_open(*args, **kwargs)
    assert name == '/proc/sys/kernel/random/boot_id'

    # check that the result is None
    assert result is None


@pytest.mark.parametrize('file_exists', [
    True,
    False,
])
def test_fetch_on_non_linux_file_exists(non_linux_platform,
        validate_error_metric_forgone, file_exists):

    fake_open = mock.mock_open(read_data=example_bootid_file)

    if file_exists:
        lines = [l.encode('utf-8')
                for l in example_bootid_file.decode('utf-8').split('\n')]
        file_iter = iter(lines)

        # come on python... seriously?
        fake_open.return_value.__iter__ = lambda self: file_iter
        fake_open.return_value.readline = lambda: next(file_iter)
    else:
        if six.PY3:
            fake_open.side_effect = FileNotFoundError # NOQA
        else:
            fake_open.side_effect = IOError

    with mock.patch('newrelic.common.system_info.open', fake_open,
            create=True):
        result = si.BootIdUtilization.fetch()

    assert fake_open.call_count == 0
    assert result is None


# Get Values

def test_get_values_none():
    result = si.BootIdUtilization.get_values(None)
    assert result is None


def test_get_values_valid():
    result = si.BootIdUtilization.get_values('bannana')
    assert result == 'bannana'


def test_get_values_long():
    result = si.BootIdUtilization.get_values('0' * 200)
    assert result == ('0' * 200)


# Sanitize

def test_sanitize_none(validate_error_metric_forgone):
    result = si.BootIdUtilization.sanitize(None)
    assert result is None


def test_sanitize_valid(validate_error_metric_forgone):
    result = si.BootIdUtilization.sanitize('   size-10-boots   ')
    assert result == 'size-10-boots'


def test_sanitize_invalid(validate_error_metric_exists):
    # these boots are too big, they don't fit
    boot = '   size-%s-boots   ' % ('9' * 128)
    result = si.BootIdUtilization.sanitize(boot)

    # result truncates
    assert len(result) == 128

    # result stripped prior to truncation
    number_of_nines = 128 - len('size-')
    suffix = '9' * number_of_nines
    assert result == ('size-%s' % suffix)
