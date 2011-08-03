""" This module provides a structure to hang the configuration settings. We
use an empty class structure and manually populate it. The global defaults
will be overlaid with any settings from the local agent configuration file.
For a specific application we will then deep copy the global default
settings and then overlay that with application settings obtained from the
server side core application. Finally, to allow for local testing and
debugging, for selected override configuration settings, we will apply back
the global defaults or those from local agent configuration.

TODO - Still need to incorporate into here a version of existing code used
to read in agent configuration file with C version of agent. But then, could
leave all the code dealing with reading of configuration file where is.

"""

import string
import copy

# The Settings objects and the global default settings. We created a
# distinct type for each category of settings so that an error when
# accessing a non existant settings is more descriptive and identifies
# the category of settings.

class Settings(object):
    def __repr__(self):
        return repr(self.__dict__)

class TransactionTracerSettings(Settings): pass
class ErrorCollectorSettings(Settings): pass
class BrowserMonitorSettings(Settings): pass
class TransactionNameSettings(Settings): pass
class RumSettings(Settings): pass
class DebugSettings(Settings): pass

_settings = Settings()
_settings.transaction_tracer = TransactionTracerSettings()
_settings.error_collector = ErrorCollectorSettings()
_settings.browser_monitoring = BrowserMonitorSettings()
_settings.transaction_name = TransactionNameSettings()
_settings.rum = RumSettings()
_settings.debug = DebugSettings()

_settings.license_key = None

_settings.host = 'collector.newrelic.com'
_settings.port = 80

_settings.proxy_host = None
_settings.proxy_port = None
_settings.proxy_user = None
_settings.proxy_pass = None

_settings.app_name = 'Python Application'

_settings.monitor_mode = True

_settings.apdex_t = 0.5
_settings.capture_params = True
_settings.ignored_params = []
_settings.sampling_rate = 0

_settings.transaction_tracer.enabled = True
_settings.transaction_tracer.transaction_threshold = 'apdex_f'
_settings.transaction_tracer.record_sql = 'obfuscated'
_settings.transaction_tracer.stack_trace_threshold = 0.5

_settings.error_collector.enabled = True
_settings.error_collector.ignore_errors = []

_settings.browser_monitoring.auto_instrument = True

_settings.transaction_name.limit = 500

_settings.debug.local_settings_overrides = []

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

# A cache of the application settings objects. This is the settings
# objects created when a snapshot of global default settings is created
# and overlaid with server side settings received from the core
# application. It must be saved here explicitly when created and then
# dropped from the cache when any connection to the core application for
# the reporting application has been lost or an internal restart is
# triggered. This is necessary as the presence of the application
# configuration object is used by the higher instrumentation layer to
# determine if the reporting application is active and whether any metrics
# should be collected. Note that the name used as key should be the
# application name alone and not the list of application names which
# includes the names of additional applications when reporting to a
# cluster.

_application_settings = {}

def application_settings(name):
    """Return a application settings object or None if there is no
    established connection for the reporting application with the core
    application.

    """

    return _application_settings.get(name, None)

def save_application_settings(name, settings_object):
    """Save the application settings object. Any prior cached settings will
    be replaced, although by rights there should never be a prior cached
    entry as it should have been dropped if a prior established connection
    for the reporting application with the core application has been lost
    or a forced internal restart of the agent was triggered.

    """

    _application_settings[name] = settings_object

def drop_application_settings(name):
    """Drop the application settings object. This would be done if a prior
    established connection for the reporting application with the core
    application had been lost or a forced internal restart of the agent was
    triggered.

    """

    del _application_settings[name]

# Creation of an application settings object from global default settings
# and any server side configuration settings.

def apply_config_setting(settings_object, name, value):
    """Apply a setting to the settings object where name is a dotted path.

    >>> name = 'browser_monitoring.auto_instrument'
    >>> value = False
    >>>
    >>> global_settings = global_settings()
    >>> _apply_config_setting(global_settings, name, value)

    """

    target = settings_object
    fields = string.splitfields(name, '.', 1)

    while len(fields) > 1:
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

    if transaction_tracer.transaction_threshold == 'apdex_f':
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

     # Overlay with server side configuration settings.

     for (name, value) in server_side_config.items():
         apply_config_setting(settings_snapshot, name, value)

     # Update any dynamically calculated settings.

     update_dynamic_settings(settings_snapshot)

     # Reapply on top any local setting overrides.

     for name in _settings.debug.local_settings_overrides:
         value = fetch_config_setting(_settings, name)
         apply_config_setting(settings_snapshot, name, value)

     return settings_snapshot





"""
import collections

AgentConfig = collections.namedtuple('AgentConfig', ['all_settings','server_settings','apdex_t','apdex_f','sampling_rate','transaction_tracer','transaction_name_limit'])
TransactionTracerConfig = collections.namedtuple('TransactionTracerConfig', ['enabled','transaction_threshold','record_sql','stack_trace_threshold'])

_config_defaults = {"apdex_t":0.5,"sampling_rate":0,
                    "transaction_tracer.enabled":True,                    
                    "transaction_tracer.transaction_threshold":"apdex_f",
                    "transaction_tracer.record_sql":"obfuscated",
                    "transaction_tracer.stack_trace_threshold":0.5,
                    "transaction_name.limit":500}


def create_configuration(config_dict={}):
    c = _config_defaults.copy() # clone the defaults
    c.update(config_dict) # merge in the user settings
    
    tt_settings = TransactionTracerConfig(enabled=c["transaction_tracer.enabled"],
                        transaction_threshold=_process_transaction_threshold(c,c["transaction_tracer.transaction_threshold"]),
                        record_sql=_process_record_sql(c["transaction_tracer.record_sql"]),
                        stack_trace_threshold=c["transaction_tracer.stack_trace_threshold"]) 
    
    return AgentConfig(server_settings=config_dict,all_settings=c,
                       apdex_t=c["apdex_t"],apdex_f=c["apdex_t"]*4,
                       sampling_rate=c["sampling_rate"],
                       transaction_tracer=tt_settings,
                       transaction_name_limit=c["transaction_name.limit"])

def _process_transaction_threshold(all_settings, threshold):
    if threshold is "apdex_f":
        return all_settings["apdex_t"]*4
    else:
        return threshold
    
def _process_record_sql(val):
#    from newrelic.config import _RECORD_SQL
#    return _RECORD_SQL[val]
    return val
"""
