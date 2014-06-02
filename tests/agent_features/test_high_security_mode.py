import os
import pytest

from newrelic.core.config import (global_settings, Settings,
    apply_config_setting)

from newrelic.config import apply_local_high_security_mode_setting

def test_hsm_default():
    # Global default should always be off.

    settings = global_settings()
    assert 'NEW_RELIC_HIGH_SECURITY_MODE' not in os.environ
    assert settings.high_security is False

_hsm_settings = [
    {
        'ssl': True,
        'capture_params': True,
        'transaction_tracer.record_sql': 'raw',
    },
    {
        'ssl': False,
        'capture_params': True,
        'transaction_tracer.record_sql': 'raw',
    },
    {
        'ssl': True,
        'capture_params': False,
        'transaction_tracer.record_sql': 'raw',
    },
    {
        'ssl': True,
        'capture_params': True,
        'transaction_tracer.record_sql': 'obfuscated',
    },
    {
        'ssl': True,
        'capture_params': True,
        'transaction_tracer.record_sql': 'off',
    },
]

def parameterize_hsm_settings():
    settings_object_list = []
    for settings in _hsm_settings:
        settings_object = Settings()
        for name, value in settings.items():
            apply_config_setting(settings_object, name, value)
        settings_object_list.append(settings_object)
    return pytest.mark.parametrize('settings', settings_object_list)

@parameterize_hsm_settings()
def test_local_hsm_setting_override(settings):
    apply_local_high_security_mode_setting(settings)
    assert settings.ssl
    assert not settings.capture_params
    assert settings.transaction_tracer.record_sql in ('off', 'obfuscated')
