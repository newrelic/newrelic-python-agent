import os
import pytest
import random
import socket
import time
from testing_support.fixtures import TerminatingPopen
from testing_support.util import get_open_port


aiohttp = pytest.importorskip('aiohttp')
from urllib.request import urlopen
version_info = tuple(int(_) for _ in aiohttp.__version__.split('.')[:2])


@pytest.mark.skipif(version_info < (3, 1),
        reason='aiohttp app factories were implement in 3.1')
@pytest.mark.parametrize('nr_enabled', (True, False))
def test_aiohttp_app_factory(nr_enabled):
    nr_admin = os.path.join(os.environ['TOX_ENVDIR'], 'bin', 'newrelic-admin')
    gunicorn = os.path.join(os.environ['TOX_ENVDIR'], 'bin', 'gunicorn')

    # Restart the server if it dies during testing
    for _ in range(5):
        PORT = get_open_port()
        cmd = [gunicorn, '-b', '127.0.0.1:%d' % PORT, '--worker-class',
                'aiohttp.GunicornWebWorker', 'async_app:app_factory']

        if nr_enabled:
            env = {
                'NEW_RELIC_ENABLED': 'true',
                'NEW_RELIC_HOST': 'staging-collector.newrelic.com',
                'NEW_RELIC_APP_NAME': 'Python Agent Test (gunicorn)',
                'NEW_RELIC_LOG': 'stderr',
                'NEW_RELIC_LOG_LEVEL': 'debug',
                'NEW_RELIC_STARTUP_TIMEOUT': '10.0',
                'NEW_RELIC_SHUTDOWN_TIMEOUT': '10.0',
            }
            new_cmd = [nr_admin, 'run-program']
            new_cmd.extend(cmd)
            cmd = new_cmd
        else:
            env = {}

        # Wait for gunicorn to start up
        with TerminatingPopen(cmd, env=env):
            for _ in range(50):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.connect(('127.0.0.1', PORT))
                    s.close()
                    break
                except socket.error:
                    pass

                time.sleep(0.1)
            else:
                continue

            with urlopen('http://127.0.0.1:%d' % PORT) as resp:
                assert resp.getcode() == 200
                assert resp.read() == b'PONG'

        # test passed
        break
    else:
        assert False, 'Gunicorn test did not run'
