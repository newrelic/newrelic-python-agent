import sys
import string
import ConfigParser

import _newrelic
import newrelic.config
import newrelic.tools.profile
import newrelic.utils.importlib

config_object = newrelic.config.config_object

# Register our importer which implements post import hooks for
# triggering of callbacks to monkey patch modules before import
# returns them to caller.

sys.meta_path.insert(0, _newrelic.ImportHookFinder())

# Generic error reporting functions.

def _raise_instrumentation_error(type, locals):
    _newrelic.log(_newrelic.LOG_ERROR, 'INSTRUMENTATION ERROR')
    _newrelic.log(_newrelic.LOG_ERROR, 'Type = %s' % type)
    _newrelic.log(_newrelic.LOG_ERROR, 'Locals = %s' % locals)

    _newrelic.log_exception(*sys.exc_info())

    if not newrelic.config.config_ignore_errors:
        raise _newrelic.InstrumentationError('Failure when instrumenting code. '
                'Check New Relic agent log file for further details.')

def _raise_configuration_error(section, options):
    options = config_object.options(section)

    _newrelic.log(_newrelic.LOG_ERROR, 'CONFIGURATION ERROR')
    _newrelic.log(_newrelic.LOG_ERROR, 'Section = %s' % section)
    _newrelic.log(_newrelic.LOG_ERROR, 'Options = %s' % options)

    _newrelic.log_exception(*sys.exc_info())

    if not newrelic.config.config_ignore_errors:
        raise _newrelic.ConfigurationError('Invalid configuration '
                'for section "%s". Check New Relic agent log file '
                'for further details.' % section)

# Registration of module import hooks defined in configuration file.

def _module_import_hook(module, function):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "instrument module %s" %
                ((target, module, function),))

        try:
            newrelic.utils.importlib.import_object(module, function)(target)
        except:
            _raise_instrumentation_error('import-hook', locals())

    return _instrument

def _process_module_configuration():
    for section in config_object.sections():
        if not section.startswith('import-hook:'):
            continue

        enabled = False

        try:
            enabled = config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            execute = config_object.get(section, 'execute')
            fields = string.splitfields(execute, ':', 1)
            module = fields[0]
            function = 'instrument'
            if len(fields) != 1:
                function = fields[1]

            target = string.splitfields(section, ':', 1)[1]

            _newrelic.log(_newrelic.LOG_INFO, "register module %s" %
                    ((target, module, function),))

            hook = _module_import_hook(module, function)
            _newrelic.register_import_hook(target, hook)
        except:
            _raise_configuration_error(section)

# Setup wsgi application wrapper defined in configuration file.

def _wsgi_application_import_hook(object_path, application):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap wsgi-application %s" %
                ((target, object_path, application),))

        try:
            _newrelic.wrap_wsgi_application(target, object_path, application)
        except:
            _raise_instrumentation_error('wsgi-application', locals())

    return _instrument

def _process_wsgi_application_configuration():
    for section in config_object.sections():
        if not section.startswith('wsgi-application:'):
            continue

        enabled = False

        try:
            enabled = config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            application = None

            if config_object.has_option(section, 'application'):
                application = config_object.get(section, 'application')

            _newrelic.log(_newrelic.LOG_INFO,
                    "register wsgi-application %s" % ((module,
                    object_path, application),))

            hook = _wsgi_application_import_hook(object_path, application)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup background task wrapper defined in configuration file.

def _background_task_import_hook(object_path, application, name, scope):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap background-task %s" %
                ((target, object_path, application, name, scope),))

        try:
            _newrelic.wrap_background_task(target, object_path,
                    application, name, scope)
        except:
            _raise_instrumentation_error('background-task', locals())

    return _instrument

def _process_background_task_configuration():
    for section in config_object.sections():
        if not section.startswith('background-task:'):
            continue

        enabled = False

        try:
            enabled = config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            application = None
            name = None
            scope = 'Function'

            if config_object.has_option(section, 'application'):
                application = config_object.get(section, 'application')
            if config_object.has_option(section, 'name'):
                name = config_object.get(section, 'name')
            if config_object.has_option(section, 'scope'):
                scope = config_object.get(section, 'scope')

            if name and name.startswith('lambda '):
                vars = { "callable_name": _newrelic.callable_name }
                name = eval(name, vars)

            _newrelic.log(_newrelic.LOG_INFO, "register background-task %s" %
                    ((module, object_path, application, name, scope),))

            hook = _background_task_import_hook(object_path,
                  application, name, scope)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup database traces defined in configuration file.

def _database_trace_import_hook(object_path, sql):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap database-trace %s" %
                ((target, object_path, sql),))

        try:
            _newrelic.wrap_database_trace(target, object_path, sql)
        except:
            _raise_instrumentation_error('database-trace', locals())

    return _instrument

def _process_database_trace_configuration():
    for section in config_object.sections():
        if not section.startswith('database-trace:'):
            continue

        enabled = False

        try:
            enabled = config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            sql = config_object.get(section, 'sql')

            if sql.startswith('lambda '):
                vars = { "callable_name": _newrelic.callable_name }
                sql = eval(sql, vars)

            _newrelic.log(_newrelic.LOG_INFO, "register database-trace %s" %
                    ((module, object_path, sql),))

            hook = _database_trace_import_hook(object_path, sql)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup external traces defined in configuration file.

def _external_trace_import_hook(object_path, library, url):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap external-trace %s" %
                ((target, object_path, library, url),))

        try:
            _newrelic.wrap_external_trace(target, object_path, library, url)
        except:
            _raise_instrumentation_error('external-trace', locals())

    return _instrument

def _process_external_trace_configuration():
    for section in config_object.sections():
        if not section.startswith('external-trace:'):
            continue

        enabled = False

        try:
            enabled = config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            library = config_object.get(section, 'library')
            url = config_object.get(section, 'url')

            if url.startswith('lambda '):
                vars = { "callable_name": _newrelic.callable_name }
                url = eval(url, vars)

            _newrelic.log(_newrelic.LOG_INFO, "register external-trace %s" %
                    ((module, object_path, library, url),))

            hook = _external_trace_import_hook(object_path, library, url)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup function traces defined in configuration file.

def _function_trace_import_hook(object_path, name, scope, interesting):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap function-trace %s" %
                ((target, object_path, name, scope, interesting),))

        try:
            _newrelic.wrap_function_trace(target, object_path, name,
                    scope, interesting)
        except:
            _raise_instrumentation_error('function-trace', locals())

    return _instrument

def _process_function_trace_configuration():
    for section in config_object.sections():
        if not section.startswith('function-trace:'):
            continue

        enabled = False

        try:
            enabled = config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            name = None
            scope = 'Function'
            interesting = True

            if config_object.has_option(section, 'name'):
                name = config_object.get(section, 'name')
            if config_object.has_option(section, 'scope'):
                scope = config_object.get(section, 'scope')
            if config_object.has_option(section, 'interesting'):
                interesting = config_object.getboolean(section, 'interesting')

            if name and name.startswith('lambda '):
                vars = { "callable_name": _newrelic.callable_name }
                name = eval(name, vars)

            _newrelic.log(_newrelic.LOG_INFO, "register function-trace %s" %
                    ((module, object_path, name, scope, interesting),))

            hook = _function_trace_import_hook(object_path, name,
                                               scope, interesting)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup memcache traces defined in configuration file.

def _memcache_trace_import_hook(object_path, command):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap memcache-trace %s" %
                ((target, object_path, command),))

        try:
            _newrelic.wrap_memcache_trace(target, object_path, command)
        except:
            _raise_instrumentation_error('memcache-trace', locals())

    return _instrument

def _process_memcache_trace_configuration():
    for section in config_object.sections():
        if not section.startswith('memcache-trace:'):
            continue

        enabled = False

        try:
            enabled = config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            command = config_object.get(section, 'command')

            if command.startswith('lambda '):
                vars = { "callable_name": _newrelic.callable_name }
                command = eval(command, vars)

            _newrelic.log(_newrelic.LOG_INFO, "register memcache-trace %s" %
                    ((module, object_path, command),))

            hook = _memcache_trace_import_hook(object_path, command)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup name transaction wrapper defined in configuration file.

def _name_transaction_import_hook(object_path, name, scope):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap name-transaction %s" %
                ((target, object_path, name, scope),))

        try:
            _newrelic.wrap_name_transaction(target, object_path, name, scope)
        except:
            _raise_instrumentation_error('name-transaction', locals())

    return _instrument

def _process_name_transaction_configuration():
    for section in config_object.sections():
        if not section.startswith('name-transaction:'):
            continue

        enabled = False

        try:
            enabled = config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            name = None
            scope = 'Function'

            if config_object.has_option(section, 'name'):
                name = config_object.get(section, 'name')
            if config_object.has_option(section, 'scope'):
                scope = config_object.get(section, 'scope')

            if name and name.startswith('lambda '):
                vars = { "callable_name": _newrelic.callable_name }
                name = eval(name, vars)

            _newrelic.log(_newrelic.LOG_INFO, "register name-transaction %s" %
                    ((module, object_path, name, scope),))

            hook = _name_transaction_import_hook(object_path, name,
                                                 scope)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup error trace wrapper defined in configuration file.

def _error_trace_import_hook(object_path, ignore_errors):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap error-trace %s" %
                ((target, object_path, ignore_errors),))

        try:
            _newrelic.wrap_error_trace(target, object_path, ignore_errors)
        except:
            _raise_instrumentation_error('error-trace', locals())

    return _instrument

def _process_error_trace_configuration():
    for section in config_object.sections():
        if not section.startswith('error-trace:'):
            continue

        enabled = False

        try:
            enabled = config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            ignore_errors = []

            if config_object.has_option(section, 'ignore_errors'):
                ignore_errors = config_object.get(section,
                        'ignore_errors').split()

            _newrelic.log(_newrelic.LOG_INFO, "register error-trace %s" %
                  ((module, object_path, ignore_errors),))

            hook = _error_trace_import_hook(object_path, ignore_errors)
            _newrelic.register_import_hook(module, hook)
        except:
            _raise_configuration_error(section)

# Setup function profiler defined in configuration file.

def _function_profile_import_hook(object_path, interesting, depth):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap function-profile %s" %
                ((target, object_path, interesting, depth),))

        try:
            newrelic.tools.profile.wrap_function_profile(target,
                    object_path, interesting, depth)
        except:
            _raise_instrumentation_error('function-profile', locals())

    return _instrument

def _process_function_profile_configuration():
    for section in config_object.sections():
        if not section.startswith('function-profile:'):
            continue

        enabled = False

        try:
            enabled = config_object.getboolean(section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
        except:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = config_object.get(section, 'function')
            (module, object_path) = string.splitfields(function, ':', 1)

            interesting = False
            depth = 5

            if config_object.has_option(section, 'interesting'):
                interesting = config_object.getboolean(section,
                                                        'interesting')
            if config_object.has_option(section, 'depth'):
                depth = config_object.getint(section, 'depth')

            _newrelic.log(_newrelic.LOG_INFO, "register function-profile %s" %
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
        if config_object.has_section(section):
            enabled = config_object.getboolean(section, 'enabled')
    except ConfigParser.NoOptionError:
        pass
    except:
        _raise_configuration_error(section)

    try:
        if config_object.has_option(section, 'execute'):
            execute = config_object.get(section, 'execute')

        if enabled and not execute:
            _newrelic.log(_newrelic.LOG_INFO, "register module %s" %
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

def setup_instrumentation():
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
