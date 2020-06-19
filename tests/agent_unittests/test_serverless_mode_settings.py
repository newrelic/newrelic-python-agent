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

from newrelic.api.application import register_application
from newrelic.api.background_task import background_task
from testing_support.validators.validate_serverless_payload import (
        validate_serverless_payload)

INI_FILE_EMPTY = """
[newrelic]
""".encode('utf-8')

INI_FILE_SERVERLESS_MODE = """
[newrelic]
serverless_mode.enabled = true
""".encode('utf-8')

INI_FILE_APDEX_T = """
[newrelic]
apdex_t = 0.33
""".encode('utf-8')

INI_FILE_APP_NAME = """
[newrelic]
serverless_mode.enabled = True
app_name = a;b
""".encode('utf-8')

NON_SERVERLESS_MODE_ENV = {
    'NEW_RELIC_SERVERLESS_MODE_ENABLED': 'false',
}

SERVERLESS_MODE_ENV = {
    'NEW_RELIC_SERVERLESS_MODE_ENABLED': 'true',
}

DT_ENV = {
    'NEW_RELIC_ACCOUNT_ID': 'account_id',
    'NEW_RELIC_PRIMARY_APPLICATION_ID': 'application_id',
    'NEW_RELIC_TRUSTED_ACCOUNT_KEY': 'trusted_key',
}

APP_NAME_ENV = {
    'NEW_RELIC_APP_NAME': 'c;d'
}


@pytest.mark.parametrize('ini,env,serverless_mode', [
    # 1. serverless mode in config file (this trumps all)
    (INI_FILE_SERVERLESS_MODE, NON_SERVERLESS_MODE_ENV, True),

    # 2. if all else fails, NEW_RELIC_SERVERLESS_MODE_ENABLED should work
    (INI_FILE_EMPTY, SERVERLESS_MODE_ENV, True),

    # 3. Default is false
    (INI_FILE_EMPTY, {}, False),
])
def test_serverless_mode_environment(ini, env, serverless_mode,
        global_settings):
    settings = global_settings()
    assert settings.serverless_mode.enabled == serverless_mode


@pytest.mark.parametrize('ini,env,value', [
    # 1. apdex_t set in config file (this trumps all)
    (INI_FILE_APDEX_T, {'NEW_RELIC_APDEX_T': 0.25}, 0.33),

    # 2. lambda environment variable should force serverless mode on
    (INI_FILE_EMPTY, {'NEW_RELIC_APDEX_T': 0.25}, 0.25),

    # 3. Default is what's in config.py
    (INI_FILE_EMPTY, {}, 0.5),
])
def test_serverless_apdex_t(ini, env, value, global_settings):
    settings = global_settings()
    assert settings.apdex_t == value


@pytest.mark.parametrize('ini,env,values', [
    (INI_FILE_EMPTY, NON_SERVERLESS_MODE_ENV, (
            None, 'Unknown', None)),
    (INI_FILE_SERVERLESS_MODE, DT_ENV, (
            'account_id', 'application_id', 'trusted_key')),
])
def test_serverless_dt_environment(ini, env, values, global_settings):
    settings = global_settings()

    assert settings.account_id == values[0]
    assert settings.primary_application_id == values[1]
    assert settings.trusted_account_key == values[2]


# The purpose of test_serverless_app_names is to ensure that if the customer
# ever tries to specify multiple application names when serverless_mode = True,
# the agent will never output more than one payload.

@pytest.mark.parametrize('ini,env,register_name,handler_name', (
    # multiple app names specified via the newrelic.ini config file
    (INI_FILE_APP_NAME, {}, None, None),

    # multiple app names specified via the NEW_RELIC_APP_NAME env variable
    (INI_FILE_SERVERLESS_MODE, APP_NAME_ENV, None, None),

    # multiple app names specified via a string passed to register_application
    (INI_FILE_SERVERLESS_MODE, {}, 'e;f', None),

    # multiple app names specified via a string passed to transaction decorator
    (INI_FILE_SERVERLESS_MODE, {}, None, 'h;i'),
))
def test_serverless_mutli_app_names(ini, env, register_name, handler_name,
                                    global_settings):
    application = handler_name or register_application(register_name or None)

    @validate_serverless_payload()
    @background_task(application=application)
    def _test_serverless_app_names():
        pass

    _test_serverless_app_names()
