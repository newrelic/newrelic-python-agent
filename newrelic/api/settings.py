import os

import newrelic.core.config

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

settings = newrelic.core.config.global_settings

RECORDSQL_OFF = 'off'
RECORDSQL_RAW = 'raw'
RECORDSQL_OBFUSCATED = 'obfuscated'

if _agent_mode not in ('julunggul',):
    import _newrelic
    settings = _newrelic.settings
    RECORDSQL_OFF = _newrelic.RECORDSQL_OFF
    RECORDSQL_RAW = _newrelic.RECORDSQL_RAW
    RECORDSQL_OBFUSCATED = _newrelic.RECORDSQL_OBFUSCATED
