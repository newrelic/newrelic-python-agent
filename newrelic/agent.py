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

_process_import_hook('django', 'newrelic.imports.framework.django')

_process_import_hook('flask', 'newrelic.imports.framework.flask')

_process_import_hook('gluon.compileapp', 'newrelic.imports.framework.web2py')
_process_import_hook('gluon.main', 'newrelic.imports.framework.web2py')

_process_import_hook('pylons.wsgiapp','newrelic.imports.framework.pylons')
_process_import_hook('pylons.controllers.core',
                     'newrelic.imports.framework.pylons')

_process_import_hook('cx_Oracle', 'newrelic.imports.database.dbapi2')
_process_import_hook('MySQLdb', 'newrelic.imports.database.dbapi2')
_process_import_hook('postgresql.interface.proboscis.dbapi2',
                     'newrelic.imports.database.dbapi2')
_process_import_hook('psycopg2', 'newrelic.imports.database.dbapi2')
_process_import_hook('pysqlite2.dbapi2', 'newrelic.imports.database.dbapi2')
_process_import_hook('sqlite3.dbapi2', 'newrelic.imports.database.dbapi2')

_process_import_hook('memcache', 'newrelic.imports.memcache.memcache')
_process_import_hook('pylibmc', 'newrelic.imports.memcache.pylibmc')

_process_import_hook('jinja2.environment', 'newrelic.imports.template.jinja2')

_process_import_hook('mako.runtime', 'newrelic.imports.template.mako')

_process_import_hook('genshi.template.base', 'newrelic.imports.template.genshi')

_process_import_hook('feedparser', 'newrelic.imports.external.feedparser')

# Setup database traces defined in configuration file.

def _database_trace_import_hook(object_path, sql):
    def _instrument(target):
        wrap_database_trace(target, object_path, sql)
    return _instrument

for section in _config_object.sections():
    if section.startswith('database-trace:'):
        try:
            enabled = _config_object.getboolean(section, 'enabled')
            function = _config_object.get(section, 'function')
            sql = _config_object.get(section, 'sql')
        except ConfigParser.NoOptionError:
            pass
        else:
            if enabled:
                parts = function.split(':')
                if len(parts) == 2:
                    module, object_path = parts
                    if sql.startswith('lambda '):
                        vars = { "callable_name": callable_name,
                                 "import_module": import_module, }
                        sql = eval(sql, vars)
                    hook = _database_trace_import_hook(object_path, sql)
                    register_import_hook(module, hook)

# Setup external traces defined in configuration file.

def _external_trace_import_hook(object_path, library, url):
    def _instrument(target):
        wrap_external_trace(target, object_path, library, url)
    return _instrument

for section in _config_object.sections():
    if section.startswith('external-trace:'):
        try:
            enabled = _config_object.getboolean(section, 'enabled')
            function = _config_object.get(section, 'function')
            library = _config_object.get(section, 'library')
            url = _config_object.get(section, 'url')
        except ConfigParser.NoOptionError:
            pass
        else:
            if enabled:
                parts = function.split(':')
                if len(parts) == 2:
                    module, object_path = parts
                    if url.startswith('lambda '):
                        vars = { "callable_name": callable_name,
                                 "import_module": import_module, }
                        url = eval(url, vars)
                    hook = _external_trace_import_hook(object_path, library,
                                                       url)
                    register_import_hook(module, hook)

# Setup function traces defined in configuration file.

def _function_trace_import_hook(object_path, name, scope, interesting):
    def _instrument(target):
        wrap_function_trace(target, object_path, name, scope, interesting)
    return _instrument

for section in _config_object.sections():
    if section.startswith('function-trace:'):
        try:
            enabled = _config_object.getboolean(section, 'enabled')
            function = _config_object.get(section, 'function')
        except ConfigParser.NoOptionError:
            pass
        else:
            if enabled:
                name = None
                scope = 'Function'
                interesting = True

                if _config_object.has_option(section, 'name'):
                    name = _config_object.get(section, 'name')
                if _config_object.has_option(section, 'scope'):
                    scope = _config_object.get(section, 'scope')
                if _config_object.has_option(section, 'interesting'):
                    interesting = _config_object.getboolean(section,
                                                            'interesting')

                parts = function.split(':')
                if len(parts) == 2:
                    module, object_path = parts
                    if name.startswith('lambda '):
                        vars = { "callable_name": callable_name,
                                 "import_module": import_module, }
                        name = eval(name, vars)
                    hook = _function_trace_import_hook(object_path, name,
                                                       scope, interesting)
                    register_import_hook(module, hook)

# Setup memcache traces defined in configuration file.

def _memcache_trace_import_hook(object_path, command):
    def _instrument(target):
        wrap_memcache_trace(target, object_path, command)
    return _instrument

for section in _config_object.sections():
    if section.startswith('memcache-trace:'):
        try:
            enabled = _config_object.getboolean(section, 'enabled')
            function = _config_object.get(section, 'function')
            command = _config_object.get(section, 'command')
        except ConfigParser.NoOptionError:
            pass
        else:
            if enabled:
                parts = function.split(':')
                if len(parts) == 2:
                    module, object_path = parts
                    if command.startswith('lambda '):
                        vars = { "callable_name": callable_name,
                                 "import_module": import_module, }
                        command = eval(command, vars)
                    hook = _memcache_trace_import_hook(object_path, command)
                    register_import_hook(module, hook)

# Setup name transaction wrapper defined in configuration file.

def _name_transaction_import_hook(object_path, name, scope):
    def _instrument(target):
        wrap_name_transaction(target, object_path, name, scope)
    return _instrument

for section in _config_object.sections():
    if section.startswith('name-transaction:'):
        try:
            enabled = _config_object.getboolean(section, 'enabled')
            function = _config_object.get(section, 'function')
        except ConfigParser.NoOptionError:
            pass
        else:
            if enabled:
                name = None
                scope = 'Function'

                if _config_object.has_option(section, 'name'):
                    name = _config_object.get(section, 'name')
                if _config_object.has_option(section, 'scope'):
                    scope = _config_object.get(section, 'scope')

                parts = function.split(':')
                if len(parts) == 2:
                    module, object_path = parts
                    if name.startswith('lambda '):
                        vars = { "callable_name": callable_name,
                                 "import_module": import_module, }
                        name = eval(name, vars)
                    hook = _name_transaction_import_hook(object_path, name,
                                                         scope)
                    register_import_hook(module, hook)

