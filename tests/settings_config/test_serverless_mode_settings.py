import pytest

INI_FILE_EMPTY = """
[newrelic]
""".encode('utf-8')

INI_FILE_SERVERLESS_MODE = """
[newrelic]
serverless_mode = true
""".encode('utf-8')

INI_FILE_APDEX_T = """
[newrelic]
apdex_t = 0.33
""".encode('utf-8')

NON_SERVERLESS_MODE_ENV = {
    'NEW_RELIC_SERVERLESS_MODE': 'false',
}

LAMBDA_ENV = {
    'AWS_LAMBDA_FUNCTION_NAME': 'cookies',
}

ALL_ENV = {
    'NEW_RELIC_SERVERLESS_MODE': 'false',
    'AWS_LAMBDA_FUNCTION_NAME': 'cookies',
}

DT_ENV = {
    'NEW_RELIC_ACCOUNT_ID': 'account_id',
    'NEW_RELIC_PRIMARY_APPLICATION_ID': 'application_id',
    'NEW_RELIC_TRUSTED_ACCOUNT_KEY': 'trusted_key',
}


@pytest.mark.parametrize('ini,env,serverless_mode', [
    # 1. serverless mode in config file (this trumps all)
    (INI_FILE_SERVERLESS_MODE, NON_SERVERLESS_MODE_ENV, True),

    # 2. serverless mode in the env variable should override any other env
    # variables
    (INI_FILE_EMPTY, ALL_ENV, False),

    # 3. lambda environment variable should force serverless mode on
    (INI_FILE_EMPTY, LAMBDA_ENV, True),

    # 4. Default is false
    (INI_FILE_EMPTY, {}, False),
])
def test_serverless_mode_environment(ini, env, serverless_mode,
        global_settings):
    settings = global_settings()
    assert settings.serverless_mode == serverless_mode


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
    (INI_FILE_SERVERLESS_MODE, LAMBDA_ENV, (
            None, 'Unknown', None, True)),
    (INI_FILE_EMPTY, NON_SERVERLESS_MODE_ENV, (
            None, 'Unknown', None, False)),
    (INI_FILE_SERVERLESS_MODE, DT_ENV, (
            'account_id', 'application_id', 'trusted_key', True)),
])
def test_serverless_dt_environment(ini, env, values, global_settings):
    settings = global_settings()

    assert settings.account_id == values[0]
    assert settings.primary_application_id == values[1]
    assert settings.trusted_account_key == values[2]

    assert settings.serverless_mode == values[3]
