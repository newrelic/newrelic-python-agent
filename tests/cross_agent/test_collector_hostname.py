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
import multiprocessing
import os
import pytest
import sys
import tempfile

try:
    # python 2.x
    reload
except NameError:
    # python 3.x
    from imp import reload


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures',
    'collector_hostname.json'))

_parameters_list = ['config_file_key', 'config_override_host',
        'env_key', 'env_override_host', 'hostname']
_parameters = ','.join(_parameters_list)


def _load_tests():
    with open(FIXTURE, 'r') as fh:
        js = fh.read()
    return json.loads(js)


def _parametrize_test(test):
    return tuple([test.get(f, None) for f in _parameters_list])


_tests_json = _load_tests()
_collector_hostname_tests = [_parametrize_test(t) for t in _tests_json]
_collector_hostname_ids = [t.get('name', None) for t in _tests_json]


def _test_collector_hostname(config_file_key=None, config_override_host=None,
        env_key=None, env_override_host=None, hostname=None, queue=None):

    try:
        ini_contents = '[newrelic]'

        if 'NEW_RELIC_HOST' in os.environ:
            del os.environ['NEW_RELIC_HOST']
        if 'NEW_RELIC_LICENSE_KEY' in os.environ:
            del os.environ['NEW_RELIC_LICENSE_KEY']

        if env_override_host:
            os.environ['NEW_RELIC_HOST'] = env_override_host
        if env_key:
            os.environ['NEW_RELIC_LICENSE_KEY'] = env_key

        if config_file_key:
            ini_contents += '\nlicense_key = %s' % config_file_key
        if config_override_host:
            ini_contents += '\nhost = %s' % config_override_host

        import newrelic.config as config
        import newrelic.core.config as core_config
        reload(core_config)
        reload(config)

        ini_file = tempfile.NamedTemporaryFile()
        ini_file.write(ini_contents.encode('utf-8'))
        ini_file.seek(0)

        config.initialize(ini_file.name)
        settings = core_config.global_settings()
        assert settings.host == hostname

    except:
        if queue:
            queue.put(sys.exc_info()[1])
        raise

    if queue:
        queue.put('PASS')


@pytest.mark.parametrize(_parameters, _collector_hostname_tests,
        ids=_collector_hostname_ids)
def test_collector_hostname(config_file_key, config_override_host, env_key,
        env_override_host, hostname):

    # We run the actual test in a subprocess because we are editing the
    # settings we need to connect to the data collector. With the wrong
    # settings, our requires_data_collector fixture will fail on any tests that
    # run after this one.

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=_test_collector_hostname,
            kwargs={'config_file_key': config_file_key, 'config_override_host':
                config_override_host, 'env_key': env_key, 'env_override_host':
                env_override_host, 'hostname': hostname, 'queue': queue})
    process.start()
    result = queue.get(timeout=2)

    assert result == 'PASS'
