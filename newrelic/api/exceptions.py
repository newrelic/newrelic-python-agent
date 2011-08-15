import os

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

class ConfigurationError(Exception): pass
class InstrumentationError(Exception): pass

if not _agent_mode in ('julunggul',):
    import _newrelic
    ConfigurationError = _newrelic.ConfigurationError
    InstrumentationError = _newrelic.InstrumentationError
