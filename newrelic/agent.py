import sys
import os
import string
import ConfigParser

from _newrelic import *

# Read in and apply agent configuration.

_LOG_LEVEL = {
    'ERROR' : LOG_ERROR,
    'INFO' : LOG_INFO,
    'WARNING': LOG_WARNING,
    'VERBOSE' : LOG_VERBOSE,
    'DEBUG' : LOG_DEBUG,
    'VERBOSEDEBUG': LOG_VERBOSEDEBUG,
}

_RECORD_SQL = {
    "off": RECORDSQL_OFF,
    "raw": RECORDSQL_RAW,
    "obfuscated": RECORDSQL_OBFUSCATED,
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

_settings = settings()

_config_file = os.environ.get('NEWRELIC_CONFIG_FILE', None)
_config_environment = os.environ.get('NEWRELIC_ENVIRONMENT', None)
_config_object = ConfigParser.SafeConfigParser()

def _process_setting(section, option, getter, mapper):
    try:
        value = getattr(_config_object, getter)(section, option)
    except ConfigParser.NoOptionError:
        pass
    else:
        try:
            if mapper:
                value = mapper(value)
        except:
            raise ValueError('Invalid configuration entry with name '
                               '"%s" and value "%s".' % (option, value))
        else:
            target = _settings
            parts = string.splitfields(option, '.', 1) 
            while True:
                if len(parts) == 1:
                    setattr(target, parts[0], value)
                    break
                else:
                    target = getattr(target, parts[0])
                    parts = string.splitfields(parts[1], '.', 1)

def _process_configuration(section):
    _process_setting(section, 'app_name',
                     'get', None)
    _process_setting(section, 'monitor_mode',
                     'getboolean', None)
    _process_setting(section, 'log_file',
                     'get', None)
    _process_setting(section, 'log_level',
                     'get', _map_log_level)
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
    _process_setting(section, 'local_daemon.socket_timeout',
                     'getint', None)
    _process_setting(section, 'debug.dump_metric_table',
                     'getboolean', None)
    _process_setting(section, 'debug.sql_statement_parsing',
                     'getboolean', None)

if _config_file:
    if not _config_object.read([_config_file]):
        raise IOError('unable to open file %s' % _config_file)

    # Although we have read the configuration here, only process
    # it if this hasn't already been done previously.

    if _settings.config_file is None:
        _settings.config_file = _config_file
        _process_configuration('newrelic')
        if _config_environment:
            _settings.environment = _config_environment
            _process_configuration('newrelic:%s' % _config_environment)
    else:
        assert _settings.config_file == _config_file
        assert _settings.environment == _config_environment

# Setup instrumentation by triggering off module imports.

sys.meta_path.insert(0, ImportHookFinder())

def _import_hook(module, function):
    def _instrument(target):
        getattr(import_module(module), function)(target)
    return _instrument

def _process_import_hook(target, module, function='instrument'):
    enabled = True
    section = 'import-hook:%s' % target
    if _config_object.has_section(section):
        try:
            enabled = _config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
    if enabled and not _config_object.has_option(section, 'execute'):
        register_import_hook(target, _import_hook(module, function))

for section in _config_object.sections():
    if section.startswith('import-hook:'):
        target = section.split(':')[1]
        try:
            enabled = _config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        else:
            if enabled:
                try:
                    parts = _config_object.get(section, 'execute').split(':')
                except ConfigParser.NoOptionError:
                    pass
                else:
                    if len(parts) == 1:
                        hook = _import_hook(parts[0], 'instrument')
                    else:
                        hook = _import_hook(parts[0], parts[1])
                    register_import_hook(target, hook)

_process_import_hook('django', 'newrelic.framework_django')

_process_import_hook('flask', 'newrelic.framework_flask')

_process_import_hook('gluon.compileapp', 'newrelic.framework_web2py')
_process_import_hook('gluon.main', 'newrelic.framework_web2py')

_process_import_hook('cx_Oracle', 'newrelic.database_dbapi2')
_process_import_hook('MySQLdb', 'newrelic.database_dbapi2')
_process_import_hook('psycopg', 'newrelic.database_dbapi2')
_process_import_hook('psycopg2', 'newrelic.database_dbapi2')
_process_import_hook('pysqlite2', 'newrelic.database_dbapi2')
_process_import_hook('sqlite3', 'newrelic.database_dbapi2')

_process_import_hook('memcache', 'newrelic.memcache_memcache')
_process_import_hook('pylibmc', 'newrelic.memcache_pylibmc')

_process_import_hook('jinja2', 'newrelic.template_jinja2')

_process_import_hook('feedparser', 'newrelic.external_feedparser')
