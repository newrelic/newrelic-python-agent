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
    nr_admin = os.path.join(os.environ['TOX_ENV_DIR'], 'bin', 'newrelic-admin')
    gunicorn = os.path.join(os.environ['TOX_ENV_DIR'], 'bin', 'gunicorn')

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
                'NEW_RELIC_CONFIG_FILE': 'config.ini',
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
