import sys
import os
import ConfigParser

from _newrelic import *

# Read in and apply agent configuration.

_LOG_LEVELS = {
    'ERROR' : LOG_ERROR,
    'INFO' : LOG_INFO,
    'WARNING': LOG_WARNING,
    'VERBOSE' : LOG_VERBOSE,
    'DEBUG' : LOG_DEBUG,
    'VERBOSEDEBUG': LOG_VERBOSEDEBUG,
}

_CONFIG_VALUES = {
    'app_name': str,
    'monitor_mode': lambda x: x.lower() != 'false',
    'log_file': str,
    'log_level': _LOG_LEVELS.__getitem__,
}

_settings = settings()

_config_file = os.environ.get('NEWRELIC_CONFIG', None)

if _config_file:
    _config_object = ConfigParser.SafeConfigParser()
    _config_object.read([_config_file])
    for key, format in _CONFIG_VALUES.iteritems():
        string = _config_object.get('newrelic', key, None)
        if string is not None:
            try:
                value = format(string)
            except:
                raise RuntimeError('Invalid configuration entry with name '
                                   '"%s" and value "%s".' % (key, string))
            setattr(_settings, key, value)

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
