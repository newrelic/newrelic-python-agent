import os
import pytest
import tempfile

from newrelic.agent import function_wrapper, global_settings, initialize
from newrelic.core.data_collector import (ApplicationSession,
        remove_ignored_configs)

# these will be reloaded for each test
import newrelic.config
import newrelic.core.config

try:
    # python 2.x
    reload
except NameError:
    # python 3.x
    from imp import reload

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser

INI_FILE_WITHOUT_UTIL_CONF = b"""
[newrelic]
"""

INI_FILE_WITH_UTIL_CONF = b"""
[newrelic]

utilization.billing_hostname = file-hostname
"""

ENV_WITHOUT_UTIL_CONF = {}
ENV_WITH_UTIL_CONF = {'NEW_RELIC_UTILIZATION_BILLING_HOSTNAME': 'env-hostname'}

INITIAL_ENV = os.environ

# Tests for loading settings and testing for values precedence

def reset_agent_config(ini_contents, env_dict):
    @function_wrapper
    def reset(wrapped, instance, args, kwargs):
        os.environ.update(env_dict)

        # wrap in try/except so env vars are always reset
        try:
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
        except:
            raise
        finally:
            os.environ.clear()
            os.environ = INITIAL_ENV

        return returned
    return reset

@reset_agent_config(INI_FILE_WITHOUT_UTIL_CONF, ENV_WITH_UTIL_CONF)
def test_billing_hostname_from_env_vars():
    settings = global_settings()
    assert settings.utilization.billing_hostname == 'env-hostname'

    local_config, = ApplicationSession._create_connect_payload(
            '', [], [], newrelic.core.config.global_settings_dump())
    util_conf = local_config['utilization'].get('config')
    assert util_conf == {'hostname': 'env-hostname'}

@reset_agent_config(INI_FILE_WITH_UTIL_CONF, ENV_WITH_UTIL_CONF)
def test_billing_hostname_precedence():
    # ini-file takes precedence over env vars
    settings = global_settings()
    assert settings.utilization.billing_hostname == 'file-hostname'

    local_config, = ApplicationSession._create_connect_payload(
            '', [], [], newrelic.core.config.global_settings_dump())
    util_conf = local_config['utilization'].get('config')
    assert util_conf == {'hostname': 'file-hostname'}

@reset_agent_config(INI_FILE_WITHOUT_UTIL_CONF, ENV_WITHOUT_UTIL_CONF)
def test_billing_hostname_with_blank_ini_file_no_env():
    settings = global_settings()
    assert settings.utilization.billing_hostname == None

    # if no utilization config settings are set, the 'config' section is not in
    # the payload at all
    local_config, = ApplicationSession._create_connect_payload(
            '', [], [], newrelic.core.config.global_settings_dump())
    util_conf = local_config['utilization'].get('config')
    assert util_conf == None

@reset_agent_config(INI_FILE_WITH_UTIL_CONF, ENV_WITHOUT_UTIL_CONF)
def test_billing_hostname_with_set_in_ini_not_in_env():
    settings = global_settings()
    assert settings.utilization.billing_hostname == 'file-hostname'

    local_config, = ApplicationSession._create_connect_payload(
            '', [], [], newrelic.core.config.global_settings_dump())
    util_conf = local_config['utilization'].get('config')
    assert util_conf == {'hostname': 'file-hostname'}

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
def test_something_more(server_settings):
    fixed_settings = remove_ignored_configs(server_settings)
    agent_config = fixed_settings.get('agent_config', {})
    assert 'utilization.billing_hostname' not in agent_config
