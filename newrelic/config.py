import os
import sys
import string
import ConfigParser

import _newrelic

__all__ = [ 'load_configuration', 'config_file', 'config_environment',
           'config_object', 'settings_object' ]

# Names of configuration file and deployment environment. This
# will be overridden by the load_configuration() function when
# configuration is loaded.

config_file = None
config_environment = None
config_ignore_errors = True

# This is the actual internal settings object. Options which
# are read from the configuration file will be applied to this.

settings_object = _newrelic.settings()

# Use the raw config parser as we want to avoid interpolation
# within values. This avoids problems when writing lambdas
# within the actual configuration file for options which value
# can be dynamically calculated at time wrapper is executed.
# This configuration object can be used by the instrumentation
# modules to look up customised settings defined in the loaded
# configuration file.

config_object = ConfigParser.RawConfigParser()

# Define some mapping functions to convert raw values read from
# configuration file into the internal types expected by the
# internal configuration settings object.

_LOG_LEVEL = {
    'ERROR' : _newrelic.LOG_ERROR,
    'WARNING': _newrelic.LOG_WARNING,
    'INFO' : _newrelic.LOG_INFO,
    'VERBOSE' : _newrelic.LOG_VERBOSE,
    'DEBUG' : _newrelic.LOG_DEBUG,
    'VERBOSEDEBUG': _newrelic.LOG_VERBOSEDEBUG,
}

_RECORD_SQL = {
    "off": _newrelic.RECORDSQL_OFF,
    "raw": _newrelic.RECORDSQL_RAW,
    "obfuscated": _newrelic.RECORDSQL_OBFUSCATED,
}

def _map_log_level(s):
    return _LOG_LEVEL[s.upper()]

def _map_ignored_params(s):
    return s.split()

def _map_transaction_threshold(s):
    if s == 'apdex_f':
        return None
    return float(s)

def _map_record_sql(s):
    return _RECORD_SQL[s]

def _map_ignore_errors(s):
    return s.split()

# Cache of the parsed global settings found in the configuration
# file. We cache these so can dump them out to the log file once
# all the settings have been read.

_config_global_settings = []

# Processing of a single setting from configuration file.

def _raise_configuration_error(section, option):
    _newrelic.log(_newrelic.LOG_ERROR, 'CONFIGURATION ERROR')
    _newrelic.log(_newrelic.LOG_ERROR, 'Section = %s' % section)
    _newrelic.log(_newrelic.LOG_ERROR, 'Option = %s' % option)

    _newrelic.log_exception(*sys.exc_info())

    if not newrelic.config.config_ignore_errors:
        raise _newrelic.ConfigurationError('Invalid configuration '
                'for option "%s" in section "%s". Check New Relic '
                'agent log file for further details.' % (option, section))

def _process_setting(section, option, getter, mapper):
    try:
	# The type of a value is dictated by the getter
	# function supplied.

        value = getattr(config_object, getter)(section, option)

	# The getter parsed the value okay but want to
	# pass this through a mapping function to change
	# it to internal value suitable for internal
	# settings object. This is usually one where the
        # value was a string.

        if mapper:
            value = mapper(value)

        # Now need to apply the option from the
        # configuration file to the internal settings
        # object. Walk the object path and assign it.

        target = settings_object
        fields = string.splitfields(option, '.', 1) 

        while True:
            if len(fields) == 1:
                setattr(target, fields[0], value)
                break
            else:
                target = getattr(target, fields[0])
                fields = string.splitfields(fields[1], '.', 1)

        # Cache the configuration so can be dumped out to
        # log file when whole main configuraiton has been
        # processed. This ensures that the log file and log
        # level entries have been set.

        _config_global_settings.append((option, value))

    except ConfigParser.NoOptionError:
        pass

    except:
        _raise_configuration_error(section, option)

# Processing of all the settings for specified section except
# for log file and log level which are applied separately to
# ensure they are set as soon as possible.

def _process_configuration(section):
    _process_setting(section, 'app_name',
                     'get', None)
    _process_setting(section, 'monitor_mode',
                     'getboolean', None)
    _process_setting(section, 'capture_params',
                     'getboolean', None)
    _process_setting(section, 'ignored_params',
                     'get', _map_ignored_params)
    _process_setting(section, 'transaction_tracer.enabled',
                     'getboolean', None)
    _process_setting(section, 'transaction_tracer.transaction_threshold',
                     'get', _map_transaction_threshold)
    _process_setting(section, 'transaction_tracer.record_sql',
                     'get', _map_record_sql)
    _process_setting(section, 'transaction_tracer.stack_trace_threshold',
                     'getfloat', None)
    _process_setting(section, 'transaction_tracer.expensive_nodes_limit',
                     'getint', None)
    _process_setting(section, 'transaction_tracer.expensive_node_minimum',
                     'getfloat', None)
    _process_setting(section, 'error_collector.enabled',
                     'getboolean', None),
    _process_setting(section, 'error_collector.ignore_errors',
                     'get', _map_ignore_errors)
    _process_setting(section, 'browser_monitoring.auto_instrument',
                     'getboolean', None)
    _process_setting(section, 'local_daemon.socket_path',
                     'get', None)
    _process_setting(section, 'local_daemon.synchronous_startup',
                     'getboolean', None)
    _process_setting(section, 'debug.dump_metric_table',
                     'getboolean', None)
    _process_setting(section, 'debug.sql_statement_parsing',
                     'getboolean', None)

# Loading of configuration from specified file and for specified
# deployment environment.

def load_configuration(file=None, environment=None, ignore_errors=True):

    global config_file
    global config_environment
    global config_ignore_errors

    # If no file is specified then attempt to determine name of
    # the config file from environment variable. Same for the
    # name of any deployment environment override. If that still
    # doesn't yield any configuration file name, then we stop
    # here meaning that inbuilt defaults will be used instead.

    if not file:
        file = os.environ.get('NEWRELIC_CONFIG_FILE', None)
        environment = os.environ.get('NEWRELIC_ENVIRONMENT', None)
        errors = os.environ.get('NEWRELIC_EXCEPTIONS', '')

        if errors.lower() == 'raise':
            config_ignore_errors = False
        else:
            config_ignore_errors = True

    if not file:
        return

    # Ensure that configuration hasn't already been read from
    # within this interpreter. We don't check at this time if an
    # incompatible configuration has been read from a different
    # sub interpreter. If this occurs then results will be
    # undefined. Use from different sub interpreters of the same
    # process is not recommended.

    if config_file:
        raise _newrelic.ConfigurationError('Configuration file %s has '
                'already been read.' % repr(config_file))

    # Update global variables tracking what configuration file
    # and environment was used.

    config_file = file
    config_environment = environment

    # Now read in the configuration file. Cache the config file
    # name in internal settings object as indication of succeeding.

    if not config_object.read([config_file]):
        raise _newrelic.ConfigurationError('Unable to open configuration '
                 'file %s.' % _config_file)

    settings_object.config_file = file

    # Must process log file entries first so that errors with
    # the remainder will get logged if log file is defined.

    _process_setting('newrelic', 'log_file',
                     'get', None)
    _process_setting('newrelic', 'log_level',
                     'get', _map_log_level)

    if environment:
        _process_setting('newrelic:%s' % environment,
                         'log_file', 'get', None)
        _process_setting('newrelic:%s' % environment ,
                         'log_level', 'get', _map_log_level)

    # Now process the remainder of the global configuration
    # settings.

    _process_configuration('newrelic')

    # And any overrides specified with a section corresponding
    # to a specific deployment environment.

    if environment:
        settings_object.config_environment = environment
        _process_configuration('newrelic:%s' % environment)

    # Log details of the configuration options which were
    # read and the values they have as would be applied
    # against the internal settings object.

    for option, value in _config_global_settings:
        _newrelic.log(_newrelic.LOG_INFO, "agent config %s = %s" %
                (option, repr(value)))

def filter_app_factory(app, global_conf, config_file, environment=None):
    load_configuration(config_file, environment)
    import newrelic.agent
    return newrelic.agent.WSGIApplicationWrapper(app)
