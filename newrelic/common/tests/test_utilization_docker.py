import mock
import pytest
import newrelic.packages.six as six

from newrelic.core.stats_engine import CustomMetrics
from newrelic.core.internal_metrics import InternalTraceContext
import newrelic.common.utilization_docker as ud


@pytest.fixture
def validate_error_metric_forgone(exist=True):
    internal_metrics = CustomMetrics()
    with InternalTraceContext(internal_metrics):
        yield

    assert list(internal_metrics.metrics()) == []


@pytest.fixture
def validate_error_metric_exists(exist=True):
    internal_metrics = CustomMetrics()
    with InternalTraceContext(internal_metrics):
        yield

    assert 'Supportability/utilization/docker/error' in internal_metrics


# Test file fetch

example_procfile = '''
9:perf_event:/docker/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
8:blkio:/docker/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
7:net_cls:/
6:freezer:/docker/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
5:devices:/docker/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
4:memory:/docker/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
3:cpuacct:/docker/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
2:cpu:/docker/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
1:cpuset:/
'''

missing_cpu_procfile = 'OHAI. This file is a disaster'


def test_fetch_file_exists():
    fake_open = mock.mock_open(read_data=example_procfile)
    file_iter = iter(example_procfile.split('\n'))
    fake_open.return_value.__iter__ = lambda self: file_iter

    with mock.patch('newrelic.common.utilization_docker.open', fake_open,
            create=True):
        result = ud.DockerUtilization.fetch()

    # check that open is called once
    assert fake_open.call_count == 1

    # check that the correct file was opened
    assert fake_open.call_args[0][0] == '/proc/self/cgroup'

    # check that the correct line was processed
    s = ('2:cpu:/docker/'
            '47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2')
    assert result == s


@mock.patch.object(ud, 'open', create=True)
def test_fetch_file_missing(fake_open):
    if six.PY3:
        fake_open.side_effect = FileNotFoundError # NOQA
    else:
        fake_open.side_effect = IOError

    result = ud.DockerUtilization.fetch()

    # check that open is called once
    assert fake_open.call_count == 1

    assert result is None


def test_fetch_cpu_line_missing():
    fake_open = mock.mock_open(read_data=example_procfile)
    file_iter = iter(missing_cpu_procfile.split('\n'))
    fake_open.return_value.__iter__ = lambda self: file_iter

    with mock.patch('newrelic.common.utilization_docker.open', fake_open,
            create=True):
        result = ud.DockerUtilization.fetch()

    # check that open is called once
    assert fake_open.call_count == 1

    # check that the correct file was opened
    assert fake_open.call_args[0][0] == '/proc/self/cgroup'

    # check that the line is missing
    assert result is None


# Get Values

def test_get_values_none():
    result = ud.DockerUtilization.get_values(None)
    assert result is None


def test_get_values_valid():
    s = '2:cpu:/docker/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf5'
    result = ud.DockerUtilization.get_values(s)

    assert result == {
            'id': '47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf5'
    }


def test_get_values_endswith_slash():
    result = ud.DockerUtilization.get_values('2:cpu:/')
    # both of these are acceptable responses
    assert result is None or result == {'id': ''}


def test_get_values_no_slash():
    result = ud.DockerUtilization.get_values('2:cpu:  ')
    # both of these are acceptable responses
    assert result is None or result == {'id': ''}


# Valid Chars

def test_valid_chars_none(validate_error_metric_forgone):
    result = ud.DockerUtilization.valid_chars(None)
    assert result is False


def test_valid_chars_true(validate_error_metric_forgone):
    result = ud.DockerUtilization.valid_chars('abc123')
    assert result is True


def test_valid_chars_invalid(validate_error_metric_exists):
    result = ud.DockerUtilization.valid_chars('cats')
    assert result is False


# Valid Length

def test_valid_length_none(validate_error_metric_forgone):
    result = ud.DockerUtilization.valid_length(None)
    assert result is False


def test_valid_length_true(validate_error_metric_forgone):
    data = '0' * 64
    result = ud.DockerUtilization.valid_length(data)
    assert result is True


def test_valid_length_less_than(validate_error_metric_exists):
    data = '0' * 63
    result = ud.DockerUtilization.valid_length(data)
    assert result is False


def test_valid_length_greater_than(validate_error_metric_exists):
    data = '0' * 65
    result = ud.DockerUtilization.valid_length(data)
    assert result is False


def test_valid_length_0(validate_error_metric_exists):
    data = ''
    result = ud.DockerUtilization.valid_length(data)
    assert result is False
