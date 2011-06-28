import sys
import ConfigParser

import _newrelic
import newrelic.profile
import newrelic.config

# Setup instrumentation mechanism by installing import hook which
# implements post import hooks for triggering

sys.meta_path.insert(0, _newrelic.ImportHookFinder())

def _import_hook(module, function):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "execute import-hook %s" %
                ((target, module, function),))
        getattr(_newrelic.import_module(module), function)(target)
    return _instrument

def _process_import_hook(target, module, function='instrument'):
    enabled = True
    section = 'import-hook:%s' % target
    if newrelic.config.config_object.has_section(section):
        try:
            enabled = newrelic.config.config_object.getboolean(
                    section, 'enabled')
        except ConfigParser.NoOptionError:
            pass
    if enabled and not newrelic.config.config_object.has_option(
            section, 'execute'):
        _newrelic.register_import_hook(target, _import_hook(module, function))
        _newrelic.log(_newrelic.LOG_INFO, "register import-hook %s" % ((target,
                module, function),))

def _process_import_hook_configuration():
    for section in newrelic.config.config_object.sections():
        if section.startswith('import-hook:'):
            target = section.split(':')[1]
            try:
                enabled = newrelic.config.config_object.getboolean(
                        section, 'enabled')
            except ConfigParser.NoOptionError:
                pass
            else:
                if enabled:
                    try:
                        parts = newrelic.config.config_object.get(
                                section, 'execute').split(':')
                    except ConfigParser.NoOptionError:
                        pass
                    else:
                        module = parts[0]
                        function = 'instrument'
                        if len(parts) != 1:
                            function = parts[1]
                        _newrelic.register_import_hook(target, _import_hook(
                                module, function))
                        _newrelic.log(_newrelic.LOG_INFO,
                                "register import-hook %s" % ((target,
                                module, function),))

def _process_import_hook_builtin_defaults():
    _process_import_hook('django.core.handlers.base',
                         'newrelic.imports.framework.django')
    _process_import_hook('django.core.urlresolvers',
                         'newrelic.imports.framework.django')
    _process_import_hook('django.core.handlers.wsgi',
                         'newrelic.imports.framework.django')
    _process_import_hook('django.template',
                         'newrelic.imports.framework.django')
    _process_import_hook('django.core.servers.basehttp',
                         'newrelic.imports.framework.django')

    _process_import_hook('flask', 'newrelic.imports.framework.flask')
    _process_import_hook('flask.app', 'newrelic.imports.framework.flask')

    _process_import_hook('gluon.compileapp',
                         'newrelic.imports.framework.web2py',
                         'instrument_gluon_compileapp')
    _process_import_hook('gluon.restricted',
                         'newrelic.imports.framework.web2py',
                         'instrument_gluon_restricted')
    _process_import_hook('gluon.main',
                         'newrelic.imports.framework.web2py',
                         'instrument_gluon_main')
    _process_import_hook('gluon.template',
                         'newrelic.imports.framework.web2py',
                         'instrument_gluon_template')
    _process_import_hook('gluon.tools',
                         'newrelic.imports.framework.web2py',
                         'instrument_gluon_tools')
    _process_import_hook('gluon.http',
                         'newrelic.imports.framework.web2py',
                         'instrument_gluon_http')

    _process_import_hook('gluon.contrib.feedparser',
                         'newrelic.imports.external.feedparser')
    _process_import_hook('gluon.contrib.memcache.memcache',
                         'newrelic.imports.memcache.memcache')

    _process_import_hook('pylons.wsgiapp','newrelic.imports.framework.pylons')
    _process_import_hook('pylons.controllers.core',
                         'newrelic.imports.framework.pylons')
    _process_import_hook('pylons.templating', 'newrelic.imports.framework.pylons')

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

    _process_import_hook('xmlrpclib', 'newrelic.imports.external.xmlrpclib')

# Setup wsgi application wrapper defined in configuration file.

def _wsgi_application_import_hook(object_path, application):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap wsgi-application %s" % ((object_path,
                application),))
        _newrelic.wrap_wsgi_application(target, object_path, application)
    return _instrument

def _process_wsgi_application_configuration():
    for section in newrelic.config.config_object.sections():
        if section.startswith('wsgi-application:'):
            try:
                enabled = newrelic.config.config_object.getboolean(section, 'enabled')
                function = newrelic.config.config_object.get(section, 'function')
            except ConfigParser.NoOptionError:
                pass
            else:
                if enabled:
                    application = None

                    if newrelic.config.config_object.has_option(section, 'application'):
                        application = newrelic.config.config_object.get(section, 'application')

                    parts = function.split(':')
                    if len(parts) == 2:
                        module, object_path = parts
                        hook = _wsgi_application_import_hook(object_path,
                                                             application)
                        _newrelic.register_import_hook(module, hook)
                        _newrelic.log(_newrelic.LOG_INFO, "register wsgi-application %s" % ((module,
                                object_path, application),))

# Setup background task wrapper defined in configuration file.

def _background_task_import_hook(object_path, application, name, scope):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap background-task %s" % ((object_path,
                application, name, scope),))
        _newrelic.wrap_background_task(target, object_path, application, name, scope)
    return _instrument

def _process_background_task_configuration():
    for section in newrelic.config.config_object.sections():
        if section.startswith('background-task:'):
            try:
                enabled = newrelic.config.config_object.getboolean(section, 'enabled')
                function = newrelic.config.config_object.get(section, 'function')
            except ConfigParser.NoOptionError:
                pass
            else:
                if enabled:
                    application = None
                    name = None
                    scope = 'Function'

                    if newrelic.config.config_object.has_option(section, 'application'):
                        application = newrelic.config.config_object.get(section, 'application')
                    if newrelic.config.config_object.has_option(section, 'name'):
                        name = newrelic.config.config_object.get(section, 'name')
                    if newrelic.config.config_object.has_option(section, 'scope'):
                        scope = newrelic.config.config_object.get(section, 'scope')

                    parts = function.split(':')
                    if len(parts) == 2:
                        module, object_path = parts
                        if name and name.startswith('lambda '):
                            vars = { "callable_name": _newrelic.callable_name,
                                     "import_module": _newrelic.import_module, }
                            name = eval(name, vars)
                        hook = _background_task_import_hook(object_path,
                                                            application,
                                                            name, scope)
                        _newrelic.register_import_hook(module, hook)
                        _newrelic.log(_newrelic.LOG_INFO, "register background-task %s" % ((module,
                                object_path, application, name, scope),))

# Setup database traces defined in configuration file.

def _database_trace_import_hook(object_path, sql):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap database-trace %s" % ((object_path, sql),))
        _newrelic.wrap_database_trace(target, object_path, sql)
    return _instrument

def _process_database_trace_configuration():
    for section in newrelic.config.config_object.sections():
        if section.startswith('database-trace:'):
            try:
                enabled = newrelic.config.config_object.getboolean(section, 'enabled')
                function = newrelic.config.config_object.get(section, 'function')
                sql = newrelic.config.config_object.get(section, 'sql')
            except ConfigParser.NoOptionError:
                pass
            else:
                if enabled:
                    parts = function.split(':')
                    if len(parts) == 2:
                        module, object_path = parts
                        if sql.startswith('lambda '):
                            vars = { "callable_name": _newrelic.callable_name,
                                     "import_module": _newrelic.import_module, }
                            sql = eval(sql, vars)
                        hook = _database_trace_import_hook(object_path, sql)
                        _newrelic.register_import_hook(module, hook)
                        _newrelic.log(_newrelic.LOG_INFO, "register database-trace %s" % ((module,
                                object_path, sql),))

# Setup external traces defined in configuration file.

def _external_trace_import_hook(object_path, library, url):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap external-trace %s" % ((object_path,
                library, url),))
        _newrelic.wrap_external_trace(target, object_path, library, url)
    return _instrument

def _process_external_trace_configuration():
    for section in newrelic.config.config_object.sections():
        if section.startswith('external-trace:'):
            try:
                enabled = newrelic.config.config_object.getboolean(section, 'enabled')
                function = newrelic.config.config_object.get(section, 'function')
                library = newrelic.config.config_object.get(section, 'library')
                url = newrelic.config.config_object.get(section, 'url')
            except ConfigParser.NoOptionError:
                pass
            else:
                if enabled:
                    parts = function.split(':')
                    if len(parts) == 2:
                        module, object_path = parts
                        if url.startswith('lambda '):
                            vars = { "callable_name": _newrelic.callable_name,
                                     "import_module": _newrelic.import_module, }
                            url = eval(url, vars)
                        hook = _external_trace_import_hook(object_path, library,
                                                           url)
                        _newrelic.register_import_hook(module, hook)
                        _newrelic.log(_newrelic.LOG_INFO, "register external-trace %s" % ((module,
                                object_path, library, url),))

# Setup function traces defined in configuration file.

def _function_trace_import_hook(object_path, name, scope, interesting):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap function-trace %s" % ((object_path,
                name, scope, interesting),))
        _newrelic.wrap_function_trace(target, object_path, name, scope, interesting)
    return _instrument

def _process_function_trace_configuration():
    for section in newrelic.config.config_object.sections():
        if section.startswith('function-trace:'):
            try:
                enabled = newrelic.config.config_object.getboolean(section, 'enabled')
                function = newrelic.config.config_object.get(section, 'function')
            except ConfigParser.NoOptionError:
                pass
            else:
                if enabled:
                    name = None
                    scope = 'Function'
                    interesting = True

                    if newrelic.config.config_object.has_option(section, 'name'):
                        name = newrelic.config.config_object.get(section, 'name')
                    if newrelic.config.config_object.has_option(section, 'scope'):
                        scope = newrelic.config.config_object.get(section, 'scope')
                    if newrelic.config.config_object.has_option(section, 'interesting'):
                        interesting = newrelic.config.config_object.getboolean(section,
                                                                'interesting')

                    parts = function.split(':')
                    if len(parts) == 2:
                        module, object_path = parts
                        if name and name.startswith('lambda '):
                            vars = { "callable_name": _newrelic.callable_name,
                                     "import_module": _newrelic.import_module, }
                            name = eval(name, vars)
                        hook = _function_trace_import_hook(object_path, name,
                                                           scope, interesting)
                        _newrelic.register_import_hook(module, hook)
                        _newrelic.log(_newrelic.LOG_INFO, "register function-trace %s" % ((module,
                                object_path, name, scope, interesting),))

# Setup memcache traces defined in configuration file.

def _memcache_trace_import_hook(object_path, command):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap memcache-trace %s" % ((object_path, command),))
        _newrelic.wrap_memcache_trace(target, object_path, command)
    return _instrument

def _process_memcache_trace_configuration():
    for section in newrelic.config.config_object.sections():
        if section.startswith('memcache-trace:'):
            try:
                enabled = newrelic.config.config_object.getboolean(section, 'enabled')
                function = newrelic.config.config_object.get(section, 'function')
                command = newrelic.config.config_object.get(section, 'command')
            except ConfigParser.NoOptionError:
                pass
            else:
                if enabled:
                    parts = function.split(':')
                    if len(parts) == 2:
                        module, object_path = parts
                        if command.startswith('lambda '):
                            vars = { "callable_name": _newrelic.callable_name,
                                     "import_module": _newrelic.import_module, }
                            command = eval(command, vars)
                        hook = _memcache_trace_import_hook(object_path, command)
                        _newrelic.register_import_hook(module, hook)
                        _newrelic.log(_newrelic.LOG_INFO, "register memcache-trace %s" % ((module,
                                object_path, command),))

# Setup name transaction wrapper defined in configuration file.

def _name_transaction_import_hook(object_path, name, scope):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap name-transaction %s" % ((object_path,
                name, scope),))
        _newrelic.wrap_name_transaction(target, object_path, name, scope)
    return _instrument

def _process_name_transaction_configuration():
    for section in newrelic.config.config_object.sections():
        if section.startswith('name-transaction:'):
            try:
                enabled = newrelic.config.config_object.getboolean(section, 'enabled')
                function = newrelic.config.config_object.get(section, 'function')
            except ConfigParser.NoOptionError:
                pass
            else:
                if enabled:
                    name = None
                    scope = 'Function'

                    if newrelic.config.config_object.has_option(section, 'name'):
                        name = newrelic.config.config_object.get(section, 'name')
                    if newrelic.config.config_object.has_option(section, 'scope'):
                        scope = newrelic.config.config_object.get(section, 'scope')

                    parts = function.split(':')
                    if len(parts) == 2:
                        module, object_path = parts
                        if name and name.startswith('lambda '):
                            vars = { "callable_name": _newrelic.callable_name,
                                     "import_module": _newrelic.import_module, }
                            name = eval(name, vars)
                        hook = _name_transaction_import_hook(object_path, name,
                                                             scope)
                        _newrelic.register_import_hook(module, hook)
                        _newrelic.log(_newrelic.LOG_INFO, "register name-transaction %s" % ((module,
                                object_path, name, scope),))

# Setup error trace wrapper defined in configuration file.

def _error_trace_import_hook(object_path, ignore_errors):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap error-trace %s" % ((object_path,
                ignore_errors),))
        _newrelic.wrap_error_trace(target, object_path, ignore_errors)
    return _instrument

def _process_error_trace_configuration():
    for section in newrelic.config.config_object.sections():
        if section.startswith('error-trace:'):
            try:
                enabled = newrelic.config.config_object.getboolean(section, 'enabled')
                function = newrelic.config.config_object.get(section, 'function')
            except ConfigParser.NoOptionError:
                pass
            else:
                if enabled:
                    ignore_errors = []

                    if newrelic.config.config_object.has_option(section, 'ignore_errors'):
                        ignore_errors = newrelic.config.config_object.get(section,
                                'ignore_errors').split()

                    parts = function.split(':')
                    if len(parts) == 2:
                        module, object_path = parts
                        hook = _error_trace_import_hook(object_path, ignore_errors)
                        _newrelic.register_import_hook(module, hook)
                        _newrelic.log(_newrelic.LOG_INFO, "register error-trace %s" % ((module,
                              object_path, ignore_errors),))

# Setup function profiler defined in configuration file.

def _function_profile_import_hook(object_path, interesting, depth):
    def _instrument(target):
        _newrelic.log(_newrelic.LOG_INFO, "wrap function-profile %s" % ((object_path,
                interesting, depth),))
        newrelic.profile.wrap_function_profile(target, object_path, interesting, depth)
    return _instrument

def _process_function_profile_configuration():
    for section in newrelic.config.config_object.sections():
        if section.startswith('function-profile:'):
            try:
                enabled = newrelic.config.config_object.getboolean(section, 'enabled')
                function = newrelic.config.config_object.get(section, 'function')
            except ConfigParser.NoOptionError:
                pass
            else:
                if enabled:
                    interesting = False
                    depth = 5

                    if newrelic.config.config_object.has_option(section, 'interesting'):
                        interesting = newrelic.config.config_object.getboolean(section,
                                                                'interesting')
                    if newrelic.config.config_object.has_option(section, 'depth'):
                        depth = newrelic.config.config_object.getint(section, 'depth')

                    parts = function.split(':')
                    if len(parts) == 2:
                        module, object_path = parts
                        hook = _function_profile_import_hook(object_path,
                                                             interesting, depth)
                        _newrelic.register_import_hook(module, hook)
                        _newrelic.log(_newrelic.LOG_INFO, "register function-profile %s" % ((module,
                                object_path, interesting, depth),))

def setup_instrumentation():
    _process_import_hook_configuration()
    _process_import_hook_builtin_defaults()
    _process_wsgi_application_configuration()
    _process_background_task_configuration()
    _process_database_trace_configuration()
    _process_external_trace_configuration()
    _process_function_trace_configuration()
    _process_memcache_trace_configuration()
    _process_name_transaction_configuration()
    _process_error_trace_configuration()
    _process_function_profile_configuration()
