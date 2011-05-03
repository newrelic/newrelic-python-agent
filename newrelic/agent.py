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
    return _LOG_LEVEL[s]

def _map_ignored_params(s):
    return map(string.strip, s.split(','))

def _map_transaction_threshold(s):
    if s == 'apdex_f':
        return None
    return float(s)

def _map_record_sql(s):
    return _RECORD_SQL[s]

def _map_ignore_errors(s):
    return map(string.strip, s.split(','))

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
    _process_setting(section, 'app_name', 'get', None)
    _process_setting(section, 'monitor_mode', 'getboolean', None)
    _process_setting(section, 'log_file', 'get', None)
    _process_setting(section, 'log_level', 'get', _map_log_level)
    _process_setting(section, 'capture_params', 'getboolean', None)
    _process_setting(section, 'ignored_params', 'get', _map_ignored_params)
    _process_setting(section, 'transaction_tracer.enabled', 'getboolean', None)
    _process_setting(section, 'transaction_tracer.transaction_threshold',
                     'get', _map_transaction_threshold)
    _process_setting(section, 'transaction_tracer.record_sql',
                     'get', _map_record_sql)
    _process_setting(section, 'transaction_tracer.stack_trace_threshold',
                     'getfloat', None)
    _process_setting(section, 'error_collector.enabled', 'getboolean', None),
    _process_setting(section, 'error_collector.ignore_errors',
                     'get', _map_ignore_errors)
    _process_setting(section, 'debug.dump_metric_table', 'getboolean', None)
    _process_setting(section, 'debug.sql_statement_parsing',
                     'getboolean', None)

if _config_file:
    if not _config_object.read([_config_file]):
        raise IOError('unable to open file %s' % _config_file)
    _process_configuration('newrelic')
    if _config_environment:
        _process_configuration('newrelic:%s' % _config_environment)

# Setup instrumentation by triggering off module imports.

sys.meta_path.insert(0, ImportHookFinder())

def _hook(hook_module_name):
    def _instrument(module):
        hook_module = __import__(hook_module_name)
        for name in hook_module_name.split('.')[1:]:
            hook_module = getattr(hook_module, name)
        hook_module.instrument(module)
    return _instrument

register_import_hook('django', _hook('newrelic.framework_django'))
register_import_hook('flask', _hook('newrelic.framework_flask'))

register_import_hook('gluon.compileapp', _hook('newrelic.framework_web2py'))
register_import_hook('gluon.main', _hook('newrelic.framework_web2py'))

register_import_hook('cx_Oracle', _hook('newrelic.database_dbapi2'))
register_import_hook('MySQLdb', _hook('newrelic.database_dbapi2'))
register_import_hook('psycopg', _hook('newrelic.database_dbapi2'))
register_import_hook('psycopg2', _hook('newrelic.database_dbapi2'))
register_import_hook('pysqlite2', _hook('newrelic.database_dbapi2'))
register_import_hook('sqlite3', _hook('newrelic.database_dbapi2'))

register_import_hook('jinja2', _hook('newrelic.template_jinja2'))

register_import_hook('feedparser', _hook('newrelic.external_feedparser'))
