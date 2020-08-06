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
import tempfile

from newrelic.common.object_wrapper import function_wrapper
from newrelic.core.agent_protocol import AgentProtocol
from newrelic.config import initialize

# these will be reloaded for each test
import newrelic.config
import newrelic.core.config

# the specific methods imported here will not be changed when the modules are
# reloaded
from newrelic.core.config import (_remove_ignored_configs,
        finalize_application_settings, _environ_as_int, _environ_as_float,
        global_settings)

try:
    # python 2.x
    reload
except NameError:
    # python 3.x
    from imp import reload

INI_FILE_WITHOUT_UTIL_CONF = b"""
[newrelic]
"""

INI_FILE_WITH_UTIL_CONF = b"""
[newrelic]

utilization.billing_hostname = file-hostname
"""

INI_FILE_WITH_BAD_UTIL_CONF = b"""
[newrelic]

utilization.billing_hostname = file-hostname
utilization.logical_processors = not-a-number
utilization.total_ram_mib = 12345
"""

ENV_WITHOUT_UTIL_CONF = {}
ENV_WITH_UTIL_CONF = {'NEW_RELIC_UTILIZATION_BILLING_HOSTNAME': 'env-hostname'}
ENV_WITH_BAD_UTIL_CONF = {
    'NEW_RELIC_UTILIZATION_LOGICAL_PROCESSORS': 'notanum',
    'NEW_RELIC_UTILIZATION_BILLING_HOSTNAME': 'env-hostname',
    'NEW_RELIC_UTILIZATION_TOTAL_RAM_MIB': '98765',
}
ENV_WITH_HEROKU = {'NEW_RELIC_HEROKU_USE_DYNO_NAMES': 'false',
        'NEW_RELIC_HEROKU_DYNO_NAME_PREFIXES_TO_SHORTEN': 'meow wruff'}

INITIAL_ENV = os.environ

# Tests for loading settings and testing for values precedence


class Environ(object):
    def __init__(self, env_dict):
        self.env_dict = {}
        for key in env_dict.keys():
            self.env_dict[key] = str(env_dict[key])

    def __enter__(self):
        os.environ.update(self.env_dict)

    def __exit__(self, *args, **kwargs):
        os.environ.clear()
        os.environ = INITIAL_ENV


def reset_agent_config(ini_contents, env_dict):
    @function_wrapper
    def reset(wrapped, instance, args, kwargs):
        with Environ(env_dict):
            ini_file = tempfile.NamedTemporaryFile()
            ini_file.write(ini_contents)
            ini_file.seek(0)

            # clean settings cache and reload env vars
            # Note that reload can at times work in unexpected ways. All that
            # is required here is that the globals (such as
            # newrelic.core.config._settings) be reset.
            #
            # From python docs (2.x and 3.x)
            # "When a module is reloaded, its dictionary (containing the
            # module's global variables) is retained. Redefinitions of names
            # will override the old definitions, so this is generally not a
            # problem."
            reload(newrelic.core.config)
            reload(newrelic.config)
            initialize(ini_file.name)
            returned = wrapped(*args, **kwargs)

        return returned
    return reset


@reset_agent_config(INI_FILE_WITHOUT_UTIL_CONF, ENV_WITHOUT_UTIL_CONF)
def test_heroku_default():
    settings = global_settings()
    assert settings.heroku.use_dyno_names is True
    assert settings.heroku.dyno_name_prefixes_to_shorten in \
            (['scheduler', 'run'], ['run', 'scheduler'])


@reset_agent_config(INI_FILE_WITHOUT_UTIL_CONF, ENV_WITH_HEROKU)
def test_heroku_override():
    settings = global_settings()
    assert settings.heroku.use_dyno_names is False
    assert settings.heroku.dyno_name_prefixes_to_shorten in \
            (['meow', 'wruff'], ['wruff', 'meow'])


@reset_agent_config(INI_FILE_WITHOUT_UTIL_CONF, ENV_WITH_UTIL_CONF)
def test_billing_hostname_from_env_vars():
    settings = global_settings()
    assert settings.utilization.billing_hostname == 'env-hostname'

    local_config, = AgentProtocol._connect_payload(
            '', [], [], settings)
    util_conf = local_config['utilization'].get('config')
    assert util_conf == {'hostname': 'env-hostname'}


@reset_agent_config(INI_FILE_WITH_UTIL_CONF, ENV_WITH_UTIL_CONF)
def test_billing_hostname_precedence():
    # ini-file takes precedence over env vars
    settings = global_settings()
    assert settings.utilization.billing_hostname == 'file-hostname'

    local_config, = AgentProtocol._connect_payload(
            '', [], [], settings)
    util_conf = local_config['utilization'].get('config')
    assert util_conf == {'hostname': 'file-hostname'}


@reset_agent_config(INI_FILE_WITHOUT_UTIL_CONF, ENV_WITHOUT_UTIL_CONF)
def test_billing_hostname_with_blank_ini_file_no_env():
    settings = global_settings()
    assert settings.utilization.billing_hostname is None

    # if no utilization config settings are set, the 'config' section is not in
    # the payload at all
    local_config, = AgentProtocol._connect_payload(
            '', [], [], settings)
    util_conf = local_config['utilization'].get('config')
    assert util_conf is None


@reset_agent_config(INI_FILE_WITH_UTIL_CONF, ENV_WITHOUT_UTIL_CONF)
def test_billing_hostname_with_set_in_ini_not_in_env():
    settings = global_settings()
    assert settings.utilization.billing_hostname == 'file-hostname'

    local_config, = AgentProtocol._connect_payload(
            '', [], [], settings)
    util_conf = local_config['utilization'].get('config')
    assert util_conf == {'hostname': 'file-hostname'}


@reset_agent_config(INI_FILE_WITH_BAD_UTIL_CONF, ENV_WITHOUT_UTIL_CONF)
def test_bad_value_in_ini_file():
    settings = global_settings()
    assert settings.utilization.logical_processors == 0

    local_config, = AgentProtocol._connect_payload(
            '', [], [], settings)
    util_conf = local_config['utilization'].get('config')
    assert util_conf == {'hostname': 'file-hostname', 'total_ram_mib': 12345}


@reset_agent_config(INI_FILE_WITHOUT_UTIL_CONF, ENV_WITH_BAD_UTIL_CONF)
def test_bad_value_in_env_var():
    settings = global_settings()
    assert settings.utilization.logical_processors == 0

    local_config, = AgentProtocol._connect_payload(
            '', [], [], settings)
    util_conf = local_config['utilization'].get('config')
    assert util_conf == {'hostname': 'env-hostname', 'total_ram_mib': 98765}


# Tests for combining with server side settings

_server_side_config_settings_util_conf = [
    {
        'foo': 123,
        'bar': 456,
        'agent_config': {
            'utilization.billing_hostname': 'server-side-hostname'
        },
    },
    {
        'foo': 123,
        'bar': 456,
        'agent_config': {
            'baz': 789,
        },
    },
    {
        'foo': 123,
        'bar': 456,
    },
]


@pytest.mark.parametrize('server_settings',
        _server_side_config_settings_util_conf)
def test_remove_ignored_configs(server_settings):
    fixed_settings = _remove_ignored_configs(server_settings)
    agent_config = fixed_settings.get('agent_config', {})
    assert 'utilization.billing_hostname' not in agent_config


@reset_agent_config(INI_FILE_WITH_UTIL_CONF, ENV_WITHOUT_UTIL_CONF)
@pytest.mark.parametrize('server_settings',
        _server_side_config_settings_util_conf)
def test_finalize_application_settings(server_settings):
    settings = global_settings()

    finalize_application_settings(server_side_config=server_settings,
            settings=settings)

    # hostname set in ini_file and not in env vars
    assert settings.utilization.billing_hostname == 'file-hostname'


# Tests for _environ_as_int

_tests_environ_as_int = [
    {
        'name': 'test no env var set, no default requested',
        'envvar_set': False,
        'envvar_val': None,  # None set
        'default': None,  # None requested
        'expected_value': 0,
    },
    {
        'name': 'test no env var set, default requested',
        'envvar_set': False,
        'envvar_val': None,  # None set
        'default': 123,
        'expected_value': 123,
    },
    {
        'name': 'test env var is not an int, no default requested',
        'envvar_set': True,
        'envvar_val': 'testing',
        'default': None,  # None requested
        'expected_value': 0,
    },
    {
        'name': 'test env var is not an int, default requested',
        'envvar_set': True,
        'envvar_val': 'testing-more',
        'default': 1234,
        'expected_value': 1234,
    },
    {
        'name': 'test env var is an int',
        'envvar_set': True,
        'envvar_val': 7239,
        'default': None,  # None requested
        'expected_value': 7239,
    },
]


_tests_environ_as_float = [
    {
        'name': 'test no env var set, no default requested',
        'envvar_set': False,
        'envvar_val': None,  # None set
        'default': None,  # None requested
        'expected_value': 0.0,
    },
    {
        'name': 'test no env var set, default requested',
        'envvar_set': False,
        'envvar_val': None,  # None set
        'default': 123.0,
        'expected_value': 123.0,
    },
    {
        'name': 'test env var is not a float, no default requested',
        'envvar_set': True,
        'envvar_val': 'testing',
        'default': None,  # None requested
        'expected_value': 0.0,
    },
    {
        'name': 'test env var is not a number, default requested',
        'envvar_set': True,
        'envvar_val': 'testing-more',
        'default': 1234.0,
        'expected_value': 1234.0,
    },
    {
        'name': 'test env var is an int, not float',
        'envvar_set': True,
        'envvar_val': '7239',
        'default': None,  # None requested
        'expected_value': 7239.0,
    },
    {
        'name': 'test env var is a float',
        'envvar_set': True,
        'envvar_val': '7239.23234',
        'default': None,  # None requested
        'expected_value': 7239.23234,
    },
]


def _test_environ(env_type, test):
    env = {'TESTING': test['envvar_val']} if test['envvar_set'] else {}
    default = test['default']
    with Environ(env):
        if default:
            val = env_type('TESTING', default=default)
        else:
            val = env_type('TESTING')
    assert val == test['expected_value']


@pytest.mark.parametrize('test', _tests_environ_as_int)
def test__environ_as_int(test):
    _test_environ(_environ_as_int, test)


@pytest.mark.parametrize('test', _tests_environ_as_float)
def test__environ_as_float(test):
    _test_environ(_environ_as_float, test)
