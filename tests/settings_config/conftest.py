import sys
import tempfile
import pytest
from testing_support.fixtures import code_coverage_fixture

_coverage_source = [
    'newrelic.config',
    'newrelic.core.config',
    'newrelic.core.environment',
]

code_coverage = code_coverage_fixture(source=_coverage_source)


try:
    # python 2.x
    reload
except NameError:
    # python 3.x
    from imp import reload


class FakeProtos(object):
    Span = object()


sys.modules['grpc'] = object()
sys.modules['newrelic.core.infinite_tracing_pb2'] = FakeProtos


@pytest.fixture(scope='function')
def global_settings(request, monkeypatch):
    ini_contents = request.getfixturevalue('ini')

    monkeypatch.delenv('NEW_RELIC_HOST', raising=False)
    monkeypatch.delenv('NEW_RELIC_LICENSE_KEY', raising=False)

    if 'env' in request.funcargnames:
        env = request.getfixturevalue('env')
        for k, v in env.items():
            monkeypatch.setenv(k, v)

    import newrelic.config as config
    import newrelic.core.config as core_config
    reload(core_config)
    reload(config)

    ini_file = tempfile.NamedTemporaryFile()
    ini_file.write(ini_contents)
    ini_file.seek(0)

    config.initialize(ini_file.name)

    yield core_config.global_settings
