import pytest

INI_FILE_EMPTY = """
[newrelic]
""".encode('utf-8')

INI_FILE_SERVERLESS_MODE = """
[newrelic]
serverless_mode = true
""".encode('utf-8')

SERVERLESS_MODE_ENV = {
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
    (INI_FILE_SERVERLESS_MODE, SERVERLESS_MODE_ENV, True),

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


@pytest.mark.parametrize('ini,env', [
    (INI_FILE_EMPTY, DT_ENV),
])
def test_serverless_dt_environment(ini, env, global_settings):
    settings = global_settings()
    assert settings.account_id == 'account_id'
    assert settings.primary_application_id == 'application_id'
    assert settings.trusted_account_key == 'trusted_key'
