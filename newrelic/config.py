import os
import sys
import string
import ConfigParser

import _newrelic

import newrelic.profile

__all__ = [ 'initialize', 'filter_app_factory' ]

# Register our importer which implements post import hooks for
# triggering of callbacks to monkey patch modules before import
# returns them to caller.

sys.meta_path.insert(0, _newrelic.ImportHookFinder())

# Names of configuration file and deployment environment. This
# will be overridden by the load_configuration() function when
# configuration is loaded.

_config_file = None
_environment = None
_ignore_errors = True

# This is the actual internal settings object. Options which
# are read from the configuration file will be applied to this.

_settings = _newrelic.settings()

# Use the raw config parser as we want to avoid interpolation
# within values. This avoids problems when writing lambdas
# within the actual configuration file for options which value
# can be dynamically calculated at time wrapper is executed.
# This configuration object can be used by the instrumentation
# modules to look up customised settings defined in the loaded
# configuration file.

_config_object = ConfigParser.RawConfigParser()

# Cache of the parsed global settings found in the configuration
# file. We cache these so can dump them out to the log file once
# all the settings have been read.

_cache_object = []

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

# Processing of a single setting from configuration file.

def _raise_configuration_error(section, option=None):
    _newrelic.log(_newrelic.LOG_ERROR, 'CONFIGURATION ERROR')
    _newrelic.log(_newrelic.LOG_ERROR, 'Section = %s' % section)

    if option is None:
        options = _config_object.options(section)

        _newrelic.log(_newrelic.LOG_ERROR, 'Options = %s' % options)

        _newrelic.log_exception(*sys.exc_info())

        if not _ignore_errors:
            raise _newrelic.ConfigurationError('Invalid configuration '
                    'for section "%s". Check New Relic agent log file '
                    'for further details.' % section)

    else:
        _newrelic.log(_newrelic.LOG_ERROR, 'Option = %s' % option)

        _newrelic.log_exception(*sys.exc_info())

        if not _ignore_errors:
            raise _newrelic.ConfigurationError('Invalid configuration '
                    'for option "%s" in section "%s". Check New Relic '
                    'agent log file for further details.' % (option, section))

def _process_setting(section, option, getter, mapper):
    try:
	# The type of a value is dictated by the getter
	# function supplied.

        value = getattr(_config_object, getter)(section, option)

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

        target = _settings
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

        _cache_object.append((option, value))

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
# deployment environment. Can also indicate whether configuration
# and instrumentation errors should raise an exception or not.

_configuration_done = False

def _load_configuration(config_file=None, environment=None,
        ignore_errors=True):

    global _configuration_done

    global _config_file
    global _environment
    global _ignore_errors

    # Check whether initialisation has been done previously. If
    # it has then raise a configuration error if it was against
    # a different configuration. Otherwise just return. We don't
    # check at this time if an incompatible configuration has
    # been read from a different sub interpreter. If this occurs
    # then results will be undefined. Use from different sub
    # interpreters of the same process is not recommended.

    if _configuration_done:
        if _config_file != config_file or _environment != environment:
            raise _newrelic.ConfigurationError('Configuration has '
                    'already been done against differing configuration '
                    'file or environment. Prior configuration file used '
                    'was "%s" and environment "%s".' % (_config_file,
                    _environment))
        else:
            return

    _configuration_done = True

    # Update global variables tracking what configuration file and
    # environment was used, plus whether errors are to be ignored.

    _config_file = config_file
    _environment = environment
    _ignore_errors = ignore_errors

    # If no configuration file then nothing more to be done.

    if not config_file:
        _newrelic.log(_newrelic.LOG_DEBUG, "no agent configuration file")
        return

    _newrelic.log(_newrelic.LOG_DEBUG, "agent configuration file was %s",
            config_file)

    # Now read in the configuration file. Cache the config file
    # name in internal settings object as indication of succeeding.

    if not _config_object.read([config_file]):
        raise _newrelic.ConfigurationError('Unable to open configuration '
                 'file %s.' % config_file)

    _settings.config_file = config_file

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
        _settings.environment = environment
        _process_configuration('newrelic:%s' % environment)

    # Log details of the configuration options which were
    # read and the values they have as would be applied
    # against the internal settings object.

    for option, value in _cache_object:
        _newrelic.log(_newrelic.LOG_DEBUG, "agent config %s = %s" %
                (option, repr(value)))

# Generic error reporting functions.

def _raise_instrumentation_error(type, locals):
    _newrelic.log(_newrelic.LOG_ERROR, 'INSTRUMENTATION ERROR')
    _newrelic.log(_newrelic.LOG_ERROR, 'Type = %s' % type)
    _newrelic.log(_newrelic.LOG_ERROR, 'Locals = %s' % locals)

    _newrelic.log_exception(*sys.exc_info())

    if not _ignore_errors:
        raise _newrelic.InstrumentationError('Failure when instrumenting code. '
                'Check New Relic agent log file for further details.')

# Registration of module import hooks defined in configuration file.

def _module_import_hook(module, function):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_DEBUG, "instrument module %s" %
                ((target, module, function),))

        try:
            getattr(_newrelic.import_module(module), function)(target)
        except:
            _raise_instrumentation_error('import-hook', locals())

    return _instrument

def _process_module_configuration():
    for section in _config_object.sections():
        if not section.startswith('import-hook:'):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            execute = _config_object.get(section, 'execute')
            fields = string.splitfields(execute, ':', 1)
            module = fields[0]
            function = 'instrument'
            if len(fields) != 1:
                function = fields[1]

            target = string.splitfields(section, ':', 1)[1]

            _newrelic.log(_newrelic.LOG_DEBUG, "register module %s" %
                    ((target, module, function),))

            hook = _module_import_hook(module, function)
            _newrelic.register_import_hook(target, hook)
        except:
            _raise_configuration_error(section)

# Setup wsgi application wrapper defined in configuration file.

def _wsgi_application_import_hook(object_path, application):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_DEBUG, "wrap wsgi-application %s" %
                ((target, object_path, application),))

        try:
            _newrelic.wrap_wsgi_application(target, object_path, application)
        except:
            _raise_instrumentation_error('wsgi-application', locals())

    return _instrument

def _process_wsgi_application_configuration():
    for section in _config_object.sections():
        if not section.startswith('wsgi-application:'):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            application = None

            if _config_object.has_option(section, 'application'):
                application = _config_object.get(section, 'application')

            _newrelic.log(_newrelic.LOG_DEBUG,
                    "register wsgi-application %s" % ((module,
                    object_path, application),))

            hook = _wsgi_application_import_hook(object_path, application)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup background task wrapper defined in configuration file.

def _background_task_import_hook(object_path, application, name, scope):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_DEBUG, "wrap background-task %s" %
                ((target, object_path, application, name, scope),))

        try:
            _newrelic.wrap_background_task(target, object_path,
                    application, name, scope)
        except:
            _raise_instrumentation_error('background-task', locals())

    return _instrument

def _process_background_task_configuration():
    for section in _config_object.sections():
        if not section.startswith('background-task:'):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            application = None
            name = None
            scope = 'Function'

            if _config_object.has_option(section, 'application'):
                application = _config_object.get(section, 'application')
            if _config_object.has_option(section, 'name'):
                name = _config_object.get(section, 'name')
            if _config_object.has_option(section, 'scope'):
                scope = _config_object.get(section, 'scope')

            if name and name.startswith('lambda '):
                vars = { "callable_name": _newrelic.callable_name }
                name = eval(name, vars)

            _newrelic.log(_newrelic.LOG_DEBUG, "register background-task %s" %
                    ((module, object_path, application, name, scope),))

            hook = _background_task_import_hook(object_path,
                  application, name, scope)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup database traces defined in configuration file.

def _database_trace_import_hook(object_path, sql):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_DEBUG, "wrap database-trace %s" %
                ((target, object_path, sql),))

        try:
            _newrelic.wrap_database_trace(target, object_path, sql)
        except:
            _raise_instrumentation_error('database-trace', locals())

    return _instrument

def _process_database_trace_configuration():
    for section in _config_object.sections():
        if not section.startswith('database-trace:'):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            sql = _config_object.get(section, 'sql')

            if sql.startswith('lambda '):
                vars = { "callable_name": _newrelic.callable_name }
                sql = eval(sql, vars)

            _newrelic.log(_newrelic.LOG_DEBUG, "register database-trace %s" %
                    ((module, object_path, sql),))

            hook = _database_trace_import_hook(object_path, sql)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup external traces defined in configuration file.

def _external_trace_import_hook(object_path, library, url):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_DEBUG, "wrap external-trace %s" %
                ((target, object_path, library, url),))

        try:
            _newrelic.wrap_external_trace(target, object_path, library, url)
        except:
            _raise_instrumentation_error('external-trace', locals())

    return _instrument

def _process_external_trace_configuration():
    for section in _config_object.sections():
        if not section.startswith('external-trace:'):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            library = _config_object.get(section, 'library')
            url = _config_object.get(section, 'url')

            if url.startswith('lambda '):
                vars = { "callable_name": _newrelic.callable_name }
                url = eval(url, vars)

            _newrelic.log(_newrelic.LOG_DEBUG, "register external-trace %s" %
                    ((module, object_path, library, url),))

            hook = _external_trace_import_hook(object_path, library, url)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup function traces defined in configuration file.

def _function_trace_import_hook(object_path, name, scope, interesting):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_DEBUG, "wrap function-trace %s" %
                ((target, object_path, name, scope, interesting),))

        try:
            _newrelic.wrap_function_trace(target, object_path, name,
                    scope, interesting)
        except:
            _raise_instrumentation_error('function-trace', locals())

    return _instrument

def _process_function_trace_configuration():
    for section in _config_object.sections():
        if not section.startswith('function-trace:'):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            name = None
            scope = 'Function'
            interesting = True

            if _config_object.has_option(section, 'name'):
                name = _config_object.get(section, 'name')
            if _config_object.has_option(section, 'scope'):
                scope = _config_object.get(section, 'scope')
            if _config_object.has_option(section, 'interesting'):
                interesting = _config_object.getboolean(section, 'interesting')

            if name and name.startswith('lambda '):
                vars = { "callable_name": _newrelic.callable_name }
                name = eval(name, vars)

            _newrelic.log(_newrelic.LOG_DEBUG, "register function-trace %s" %
                    ((module, object_path, name, scope, interesting),))

            hook = _function_trace_import_hook(object_path, name,
                                               scope, interesting)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup memcache traces defined in configuration file.

def _memcache_trace_import_hook(object_path, command):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_DEBUG, "wrap memcache-trace %s" %
                ((target, object_path, command),))

        try:
            _newrelic.wrap_memcache_trace(target, object_path, command)
        except:
            _raise_instrumentation_error('memcache-trace', locals())

    return _instrument

def _process_memcache_trace_configuration():
    for section in _config_object.sections():
        if not section.startswith('memcache-trace:'):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            command = _config_object.get(section, 'command')

            if command.startswith('lambda '):
                vars = { "callable_name": _newrelic.callable_name }
                command = eval(command, vars)

            _newrelic.log(_newrelic.LOG_DEBUG, "register memcache-trace %s" %
                    ((module, object_path, command),))

            hook = _memcache_trace_import_hook(object_path, command)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup name transaction wrapper defined in configuration file.

def _name_transaction_import_hook(object_path, name, scope):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_DEBUG, "wrap name-transaction %s" %
                ((target, object_path, name, scope),))

        try:
            _newrelic.wrap_name_transaction(target, object_path, name, scope)
        except:
            _raise_instrumentation_error('name-transaction', locals())

    return _instrument

def _process_name_transaction_configuration():
    for section in _config_object.sections():
        if not section.startswith('name-transaction:'):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            name = None
            scope = 'Function'

            if _config_object.has_option(section, 'name'):
                name = _config_object.get(section, 'name')
            if _config_object.has_option(section, 'scope'):
                scope = _config_object.get(section, 'scope')

            if name and name.startswith('lambda '):
                vars = { "callable_name": _newrelic.callable_name }
                name = eval(name, vars)

            _newrelic.log(_newrelic.LOG_DEBUG, "register name-transaction %s" %
                    ((module, object_path, name, scope),))

            hook = _name_transaction_import_hook(object_path, name,
                                                 scope)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup error trace wrapper defined in configuration file.

def _error_trace_import_hook(object_path, ignore_errors):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_DEBUG, "wrap error-trace %s" %
                ((target, object_path, ignore_errors),))

        try:
            _newrelic.wrap_error_trace(target, object_path, ignore_errors)
        except:
            _raise_instrumentation_error('error-trace', locals())

    return _instrument

def _process_error_trace_configuration():
    for section in _config_object.sections():
        if not section.startswith('error-trace:'):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            ignore_errors = []

            if _config_object.has_option(section, 'ignore_errors'):
                ignore_errors = _config_object.get(section,
                        'ignore_errors').split()

            _newrelic.log(_newrelic.LOG_DEBUG, "register error-trace %s" %
                  ((module, object_path, ignore_errors),))

            hook = _error_trace_import_hook(object_path, ignore_errors)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup function profiler defined in configuration file.

def _function_profile_import_hook(object_path, interesting, depth):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_DEBUG, "wrap function-profile %s" %
                ((target, object_path, interesting, depth),))

        try:
            newrelic.profile.wrap_function_profile(target,
                    object_path, interesting, depth)
        except:
            _raise_instrumentation_error('function-profile', locals())

    return _instrument

def _process_function_profile_configuration():
    for section in _config_object.sections():
        if not section.startswith('function-profile:'):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            interesting = False
            depth = 5

            if _config_object.has_option(section, 'interesting'):
                interesting = _config_object.getboolean(section,
                                                        'interesting')
            if _config_object.has_option(section, 'depth'):
                depth = _config_object.getint(section, 'depth')

            _newrelic.log(_newrelic.LOG_DEBUG, "register function-profile %s" %
                    ((module, object_path, interesting, depth),))

            hook = _function_profile_import_hook(object_path,
                                                 interesting, depth)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

def _process_module_definition(target, module, function='instrument'):
    enabled = True
    execute = None

    try:
        section = 'import-hook:%s' % target
        if _config_object.has_section(section):
            enabled = _config_object.getboolean(section, 'enabled')
    except ConfigParser.NoOptionError:
        pass
    except:
        _raise_configuration_error(section)

    try:
        if _config_object.has_option(section, 'execute'):
            execute = _config_object.get(section, 'execute')

        if enabled and not execute:
            _newrelic.log(_newrelic.LOG_DEBUG, "register module %s" %
                    ((target, module, function),))

            _newrelic.register_import_hook(target,
                    _module_import_hook(module, function))
    except:
        _raise_configuration_error(section)

def _process_module_builtin_defaults():
    _process_module_definition('django.core.handlers.base',
            'newrelic.imports.framework.django')
    _process_module_definition('django.core.urlresolvers',
            'newrelic.imports.framework.django')
    _process_module_definition('django.core.handlers.wsgi',
            'newrelic.imports.framework.django')
    _process_module_definition('django.template',
            'newrelic.imports.framework.django')
    _process_module_definition('django.core.servers.basehttp',
            'newrelic.imports.framework.django')

    _process_module_definition('flask',
            'newrelic.imports.framework.flask')
    _process_module_definition('flask.app',
            'newrelic.imports.framework.flask')

    _process_module_definition('gluon.compileapp',
            'newrelic.imports.framework.web2py',
            'instrument_gluon_compileapp')
    _process_module_definition('gluon.restricted',
            'newrelic.imports.framework.web2py',
            'instrument_gluon_restricted')
    _process_module_definition('gluon.main',
            'newrelic.imports.framework.web2py',
            'instrument_gluon_main')
    _process_module_definition('gluon.template',
            'newrelic.imports.framework.web2py',
            'instrument_gluon_template')
    _process_module_definition('gluon.tools',
            'newrelic.imports.framework.web2py',
            'instrument_gluon_tools')
    _process_module_definition('gluon.http',
            'newrelic.imports.framework.web2py',
            'instrument_gluon_http')

    _process_module_definition('gluon.contrib.feedparser',
            'newrelic.imports.external.feedparser')
    _process_module_definition('gluon.contrib.memcache.memcache',
            'newrelic.imports.memcache.memcache')

    _process_module_definition('pylons.wsgiapp',
            'newrelic.imports.framework.pylons')
    _process_module_definition('pylons.controllers.core',
            'newrelic.imports.framework.pylons')
    _process_module_definition('pylons.templating',
            'newrelic.imports.framework.pylons')

    _process_module_definition('cx_Oracle',
            'newrelic.imports.database.dbapi2')
    _process_module_definition('MySQLdb',
            'newrelic.imports.database.dbapi2')
    _process_module_definition('postgresql.interface.proboscis.dbapi2',
            'newrelic.imports.database.dbapi2')
    _process_module_definition('psycopg2',
            'newrelic.imports.database.dbapi2')
    _process_module_definition('pysqlite2.dbapi2',
            'newrelic.imports.database.dbapi2')
    _process_module_definition('sqlite3.dbapi2',
            'newrelic.imports.database.dbapi2')

    _process_module_definition('memcache',
            'newrelic.imports.memcache.memcache')
    _process_module_definition('pylibmc',
            'newrelic.imports.memcache.pylibmc')

    _process_module_definition('jinja2.environment',
            'newrelic.imports.template.jinja2')

    _process_module_definition('mako.runtime',
            'newrelic.imports.template.mako')

    _process_module_definition('genshi.template.base',
            'newrelic.imports.template.genshi')

    _process_module_definition('feedparser',
            'newrelic.imports.external.feedparser')

    _process_module_definition('xmlrpclib',
            'newrelic.imports.external.xmlrpclib')

_instrumentation_done = False

def _setup_instrumentation():

    global _instrumentation_done

    if _instrumentation_done:
        return

    _instrumentation_done = True

    _process_module_configuration()
    _process_module_builtin_defaults()

    _process_wsgi_application_configuration()
    _process_background_task_configuration()

    _process_database_trace_configuration()
    _process_external_trace_configuration()
    _process_function_trace_configuration()
    _process_memcache_trace_configuration()

    _process_name_transaction_configuration()

    _process_error_trace_configuration()

    _process_function_profile_configuration()

def initialize(config_file=None, environment=None, ignore_errors=True):
    _load_configuration(config_file, environment, ignore_errors)
    _setup_instrumentation()

def filter_app_factory(app, global_conf, config_file, environment=None):
    initialize(config_file, environment)
    return _newrelic.WSGIApplicationWrapper(app)
