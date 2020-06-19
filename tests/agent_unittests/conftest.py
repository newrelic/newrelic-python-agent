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

import pytest
import sys
import tempfile
from newrelic.core.agent import agent_instance
from testing_support.fixtures import collector_agent_registration_fixture

_default_settings = {
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True,
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (agent_unittests)',
        default_settings=_default_settings)


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

    original = {}
    for attr in dir(core_config):
        original[attr] = getattr(core_config, attr)

    agent = agent_instance()
    original_agent_config = agent._config

    reload(core_config)
    reload(config)

    ini_file = tempfile.NamedTemporaryFile()
    ini_file.write(ini_contents)
    ini_file.seek(0)

    config.initialize(ini_file.name)

    agent._config = core_config.global_settings()

    yield core_config.global_settings

    monkeypatch.undo()
    for attr_name, attr_value in original.items():
        setattr(core_config, attr_name, attr_value)
    agent._config = original_agent_config
    reload(config)
