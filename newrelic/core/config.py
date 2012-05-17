""" This module provides a structure to hang the configuration settings. We
use an empty class structure and manually populate it. The global defaults
will be overlaid with any settings from the local agent configuration file.
For a specific application we will then deep copy the global default
settings and then overlay that with application settings obtained from the
server side core application. Finally, to allow for local testing and
debugging, for selected override configuration settings, we will apply back
the global defaults or those from local agent configuration.

"""

import os
import logging
import string
import copy

# The Settings objects and the global default settings. We create a
# distinct type for each sub category of settings that the agent knows
# about so that an error when accessing a non existant setting is more
# descriptive and identifies the category of settings. When applying
# server side configuration we create normal Settings object for new
# sub categories we don't know about.

class Settings(object):
    def __repr__(self):
        return repr(self.__dict__)

class TransactionTracerSettings(Settings): pass
class ErrorCollectorSettings(Settings): pass
class BrowserMonitorSettings(Settings): pass
class TransactionNameSettings(Settings): pass
class TransactionMetricsSettings(Settings): pass
class RumSettings(Settings): pass
class SlowSqlSettings(Settings): pass
class AgentLimitsSettings(Settings): pass
class ConsoleSettings(Settings): pass
class DebugSettings(Settings): pass

_settings = Settings()
_settings.transaction_tracer = TransactionTracerSettings()
_settings.error_collector = ErrorCollectorSettings()
_settings.browser_monitoring = BrowserMonitorSettings()
_settings.transaction_name = TransactionNameSettings()
_settings.transaction_metrics = TransactionMetricsSettings()
_settings.rum = RumSettings()
_settings.slow_sql = SlowSqlSettings()
_settings.agent_limits = AgentLimitsSettings()
_settings.console = ConsoleSettings()
_settings.debug = DebugSettings()

_settings.log_file = os.environ.get('NEW_RELIC_LOG', None)

_LOG_LEVEL = {
    'CRITICAL' : logging.CRITICAL,
    'ERROR' : logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO' : logging.INFO,
    'DEBUG' : logging.DEBUG,
}

_settings.log_level = os.environ.get('NEW_RELIC_LOG_LEVEL', 'INFO').upper()

if _settings.log_level in _LOG_LEVEL:
    _settings.log_level = _LOG_LEVEL[_settings.log_level]
else:
    _settings.log_level = logging.INFO

_settings.license_key = os.environ.get('NEW_RELIC_LICENSE_KEY', None)

_settings.ssl = False

_settings.host = os.environ.get('NEW_RELIC_HOST', 'collector.newrelic.com')
_settings.port = int(os.environ.get('NEW_RELIC_PORT', '0'))

_settings.proxy_host = None
_settings.proxy_port = None
_settings.proxy_user = None
_settings.proxy_pass = None

_settings.app_name = os.environ.get('NEW_RELIC_APP_NAME', 'Python Application')

_settings.monitor_mode = True

_settings.collect_errors = True
_settings.collect_traces = True

_settings.apdex_t = 0.5

_settings.capture_params = False
_settings.ignored_params = []

_settings.capture_environ = True
_settings.include_environ = [ 'REQUEST_METHOD', 'HTTP_USER_AGENT',
                              'HTTP_REFERER', 'CONTENT_TYPE',
                              'CONTENT_LENGTH' ]

_settings.sampling_rate = 0
_settings.shutdown_timeout = 2.5

_settings.beacon = None
_settings.application_id = None
_settings.browser_key = None
_settings.episodes_url = None

_settings.transaction_tracer.enabled = True
_settings.transaction_tracer.transaction_threshold = None
_settings.transaction_tracer.record_sql = 'obfuscated'
_settings.transaction_tracer.stack_trace_threshold = 0.5
_settings.transaction_tracer.explain_enabled = True
_settings.transaction_tracer.explain_threshold = 0.5
_settings.transaction_tracer.function_trace = []

_settings.error_collector.enabled = True
_settings.error_collector.capture_source = False
_settings.error_collector.ignore_errors = []

_settings.browser_monitoring.auto_instrument = True

_settings.transaction_name.limit = None
_settings.transaction_name.naming_scheme = None

_settings.rum.enabled = True
_settings.rum.load_episodes_file = True

_settings.slow_sql.enabled = True

_settings.transaction_metrics.overflow_minimum = 5
_settings.transaction_metrics.overflow_maximum = 10
#_settings.transaction_metrics.overflow_threshold = 0.05
_settings.transaction_metrics.overflow_threshold = 0.0

_settings.agent_limits.transaction_traces_nodes = 10000
_settings.agent_limits.sql_query_length_maximum = 16384
_settings.agent_limits.slow_sql_stack_trace = 30
_settings.agent_limits.sql_explain_plans = 30
_settings.agent_limits.slow_sql_data = 10
_settings.agent_limits.merge_stats_maximum = 5

_settings.console.listener_socket = None
_settings.console.allow_interpreter_cmd = False

_settings.debug.ignore_all_server_settings = False
_settings.debug.local_settings_overrides = []

_settings.debug.log_data_collector_calls = False
_settings.debug.log_data_collector_payloads = False
_settings.debug.log_malformed_json_data = False

def global_settings():
    """This returns the default global settings. Generally only used
    directly in test scripts and test harnesses or when applying global
    settings from agent configuration file. Making changes to the settings
    object returned by this function will not have any effect on any
    applications that have already been initialised. This is because when
    the settings are obtained from the core application a snapshot of these
    settings will be taken.

    >>> global_settings = global_settings()
    >>> global_settings.browser_monitoring.auto_instrument = False
    >>> global_settings.browser_monitoring.auto_instrument
    False

    """

    return _settings

def flatten_settings(settings):
    """This returns dictionary of settings flattened into a single
    key namespace rather than nested hierarchy.

    """

    def _flatten(settings, name, object):
        for key, value in object.__dict__.items():
            if isinstance(value, Settings):
                if name:
                    _flatten(settings, '%s.%s' % (name, key), value)
                else:
                    _flatten(settings, key, value)
            else:
                if name:
                    settings['%s.%s' % (name, key)] = value
                else:
                    settings[key] = value

        return settings

    return _flatten({}, None, settings)

def global_settings_dump():
    """This returns dictionary of global settings flattened into a single
    key namespace rather than nested hierarchy. This is used to send the
    global settings configuration back to core application.

    """

    settings = flatten_settings(_settings)

    # Strip out any sensitive settings as can be sent unencrypted.
    # The license key is being sent already, but no point sending
    # it again.

    del settings['license_key']

    del settings['proxy_user']
    del settings['proxy_pass']

    return settings

# Creation of an application settings object from global default settings
# and any server side configuration settings.

def apply_config_setting(settings_object, name, value):
    """Apply a setting to the settings object where name is a dotted path.
    If there is no pre existing settings object for a sub category then
    one will be created and added automatically.

    >>> name = 'browser_monitoring.auto_instrument'
    >>> value = False
    >>>
    >>> global_settings = global_settings()
    >>> _apply_config_setting(global_settings, name, value)

    """

    target = settings_object
    fields = string.splitfields(name, '.', 1)

    while len(fields) > 1:
        if not hasattr(target, fields[0]):
            setattr(target, fields[0], Settings())
        target = getattr(target, fields[0])
        fields = string.splitfields(fields[1], '.', 1)

    setattr(target, fields[0], value)

def fetch_config_setting(settings_object, name):
    """Fetch a setting from the settings object where name is a dotted path.

    >>> name = 'browser_monitoring.auto_instrument'
    >>>
    >>> global_settings = global_settings()
    >>> _fetch_config_setting(global_settings, name)
    'browser_monitoring.auto_instrument'

    """

    target = settings_object
    fields = string.splitfields(name, '.', 1)

    target = getattr(target, fields[0])

    while len(fields) > 1:
        fields = string.splitfields(fields[1], '.', 1)
        target = getattr(target, fields[0])

    return target

def update_dynamic_settings(settings_object):
    """Updates any dynamically calculated settings values. This would
    generally be applied on a copy of the global default settings and
    not directly.

    >>> settings_snapshot = copy.deepcopy(_settings)
    >>> update_dynamic_settings(settings_snapshot)

    """

    settings_object.apdex_f = 4 * settings_object.apdex_t

    transaction_tracer = settings_object.transaction_tracer

    if transaction_tracer.transaction_threshold is None:
        transaction_tracer.transaction_threshold = settings_object.apdex_f

def create_settings_snapshot(server_side_config={}):
     """Create a snapshot of the global default settings and overlay it
     with any server side configuration settings. Any local settings
     overrides to take precedence over server side configuration settings
     will then be reapplied to the copy. Note that the intention is that
     the resulting settings object will be cached for subsequent use
     within the application object the settings pertain to.

     >>> server_config = { 'browser_monitoring.auto_instrument': False }
     >>>
     >>> settings_snapshot = create_settings_snapshot(server_config)

     """

     settings_snapshot = copy.deepcopy(_settings)

     # Break out the server side agent config settings which
     # are stored under 'agent_config' key.

     agent_config = server_side_config.pop('agent_config', {})

     # Remap as necessary any server side agent config settings.

     # TODO This needs to be broken out into separate routine and
     # used also when reading in local agent configuration file.

     if 'transaction_tracer.transaction_threshold' in agent_config:
         value = agent_config['transaction_tracer.transaction_threshold']
         if value == 'apdex_f':
             agent_config['transaction_tracer.transaction_threshold'] = None

     # Overlay with global server side configuration settings.

     for (name, value) in server_side_config.items():
         apply_config_setting(settings_snapshot, name, value)

     # Overlay with agent server side configuration settings.
     # Assuming for now that agent service side configuration
     # can always take precedence over the global server side
     # configuration settings.

     for (name, value) in agent_config.items():
         apply_config_setting(settings_snapshot, name, value)

     # Update any dynamically calculated settings.

     update_dynamic_settings(settings_snapshot)

     # Reapply on top any local setting overrides.

     for name in _settings.debug.local_settings_overrides:
         value = fetch_config_setting(_settings, name)
         apply_config_setting(settings_snapshot, name, value)

     return settings_snapshot
