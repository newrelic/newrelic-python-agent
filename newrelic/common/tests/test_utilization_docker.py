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

example_procfile_a = b'''
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
example_procfile_b = b'''
9:perf_event:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
8:blkio:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
7:net_cls:/
6:freezer:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
5:devices:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
4:memory:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
3:cpuacct:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
2:cpu:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
1:cpuset:/
'''
example_procfile_c = b'''
8:perf_event:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
7:blkio:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
6:net_cls:/
5:freezer:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
4:devices:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
3:memory:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
2:cpuacct:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
1:cpu,cpuset:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
'''
example_procfile_d = b'''
8:perf_event:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
7:blkio:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
6:net_cls:/
5:freezer:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
4:devices:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
3:memory:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
2:cpuacct:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
1:cpuset,cpu:/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2
'''
missing_cpu = b'OHAI. This file is a disaster'
a = '/docker/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2'
b = '/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2'
c = '/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2'
d = '/basher/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf59d8a870b2'


def _bind_open(name, *args, **kwargs):
    return name


@pytest.mark.parametrize('case', [
    (example_procfile_a, a),
    (example_procfile_b, b),
    (example_procfile_c, c),
    (example_procfile_d, d),
    (missing_cpu, None),
])
def test_fetch_file_valid(case):
    f, expected = case
    fake_open = mock.mock_open(read_data=f)
    lines = [l.encode('UTF-8')
            for l in f.decode('utf-8').split('\n')]
    file_iter = iter(lines)
    fake_open.return_value.__iter__ = lambda self: file_iter

    with mock.patch('newrelic.common.utilization_docker.open', fake_open,
            create=True):
        result = ud.DockerUtilization.fetch()

    # check that open is called once
    assert fake_open.call_count == 1

    # check that the correct file was opened
    args, kwargs = fake_open.call_args
    name = _bind_open(*args, **kwargs)
    assert name == '/proc/self/cgroup'

    # check that the correct line was processed
    assert result == expected


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


# Get Values

def test_get_values_none():
    result = ud.DockerUtilization.get_values(None)
    assert result is None


def test_get_values_valid():
    s = '/docker/47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf5'
    result = ud.DockerUtilization.get_values(s)

    assert result == {
            'id': '47cbd16b77c50cbf71401c069cd2189f0e659af17d5a2daca3bddf5'
    }


def test_get_values_endswith_slash():
    result = ud.DockerUtilization.get_values('/')
    # both of these are acceptable responses
    assert result is None or result == {'id': ''}


def test_get_values_no_slash():
    result = ud.DockerUtilization.get_values('  ')
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
