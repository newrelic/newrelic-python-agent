"""This module provides functions to collect information about the operating
system, Python and hosting environment.

"""

import newrelic

from ..common.system_info import (total_physical_memory,
    logical_processor_count, physical_processor_count)

import sys
import os
import platform

try:
    import pkg_resources
except ImportError:
    pass

try:
    import newrelic.core._thread_utilization
except ImportError:
    pass

def environment_settings():
    """Returns an array of arrays of environment settings

    """

    env = []

    # Agent information.

    env.append(('Agent Version', '.'.join(map(str, newrelic.version_info))))

    if 'NEW_RELIC_ADMIN_COMMAND' in os.environ:
        env.append(('Admin Command', os.environ['NEW_RELIC_ADMIN_COMMAND']))
        del os.environ['NEW_RELIC_ADMIN_COMMAND']

    # System information.

    env.append(('Arch', platform.machine()))
    env.append(('OS', platform.system()))
    env.append(('OS version', platform.release()))

    env.append(('Total Physical Memory (MB)', total_physical_memory()))
    env.append(('Logical Processors', logical_processor_count()))
    env.append(('Physical Processors', physical_processor_count()))

    # Python information.

    env.append(('Python Program Name', sys.argv[0]))

    env.append(('Python Executable', sys.executable))

    env.append(('Python Home', os.environ.get('PYTHONHOME', '')))
    env.append(('Python Path', os.environ.get('PYTHONPATH', '')))

    env.append(('Python Prefix', sys.prefix))
    env.append(('Python Exec Prefix', sys.exec_prefix))

    env.append(('Python Runtime', '.'.join(platform.python_version_tuple())))

    env.append(('Python Implementation', platform.python_implementation()))
    env.append(('Python Version', sys.version))

    env.append(('Python Platform', sys.platform))

    env.append(('Python Max Unicode', sys.maxunicode))

    # Extensions information.

    extensions = []

    if 'newrelic.core._thread_utilization' in sys.modules:
        extensions.append('newrelic.core._thread_utilization')

    env.append(('Compiled Extensions', ', '.join(extensions)))

    # Dispatcher information.

    dispatcher = []

    if not dispatcher and 'mod_wsgi' in sys.modules:
        mod_wsgi = sys.modules['mod_wsgi']
        if hasattr(mod_wsgi, 'process_group'):
            if mod_wsgi.process_group == '':
                dispatcher.append(('Dispatcher', 'Apache/mod_wsgi (embedded)'))
            else:
                dispatcher.append(('Dispatcher', 'Apache/mod_wsgi (daemon)'))
        else:
            dispatcher.append(('Dispatcher', 'Apache/mod_wsgi'))
        if hasattr(mod_wsgi, 'version'):
            dispatcher.append(('Dispatcher Version', str(mod_wsgi.version)))

    if not dispatcher and 'uwsgi' in sys.modules:
        dispatcher.append(('Dispatcher', 'uWSGI'))
        uwsgi = sys.modules['uwsgi']
        if hasattr(uwsgi, 'version'):
            dispatcher.append(('Dispatcher Version', uwsgi.version))

    if not dispatcher and 'flup.server.fcgi' in sys.modules:
        dispatcher.append(('Dispatcher', 'flup/fastcgi (threaded)'))

    if not dispatcher and 'flup.server.fcgi_fork' in sys.modules:
        dispatcher.append(('Dispatcher', 'flup/fastcgi (prefork)'))

    if not dispatcher and 'flup.server.scgi' in sys.modules:
        dispatcher.append(('Dispatcher', 'flup/scgi (threaded)'))

    if not dispatcher and 'flup.server.scgi_fork' in sys.modules:
        dispatcher.append(('Dispatcher', 'flup/scgi (prefork)'))

    if not dispatcher and 'flup.server.ajp' in sys.modules:
        dispatcher.append(('Dispatcher', 'flup/ajp (threaded)'))

    if not dispatcher and 'flup.server.ajp_fork' in sys.modules:
        dispatcher.append(('Dispatcher', 'flup/ajp (forking)'))

    if not dispatcher and 'flup.server.cgi' in sys.modules:
        dispatcher.append(('Dispatcher', 'flup/cgi'))

    if not dispatcher and 'tornado' in sys.modules:
        dispatcher.append(('Dispatcher', 'tornado'))
        tornado = sys.modules['tornado']
        if hasattr(tornado, 'version_info'):
            dispatcher.append(('Dispatcher Version',
                               str(tornado.version_info)))

    if not dispatcher and 'gunicorn' in sys.modules:
        if 'gunicorn.workers.ggevent' in sys.modules:
            dispatcher.append(('Dispatcher', 'gunicorn (gevent)'))
        elif 'gunicorn.workers.geventlet' in sys.modules:
            dispatcher.append(('Dispatcher', 'gunicorn (eventlet)'))
        else:
            dispatcher.append(('Dispatcher', 'gunicorn'))
        gunicorn = sys.modules['gunicorn']
        if hasattr(gunicorn, '__version__'):
            dispatcher.append(('Dispatcher Version', gunicorn.__version__))

    env.extend(dispatcher)

    # Module information.

    plugins = []

    # Using six to create create a snapshot of sys.modules can occassionally
    # fail in a rare case when modules are imported in parallel by different
    # threads. This is because list(six.iteritems(sys.modules)) results in
    # list(iter(sys.modules.iteritems())), which means sys.modules could change
    # between the time when the iterable is handed over from the iter() to
    # list().
    #
    # TL;DR: Do NOT use six module for the following iteration.

    for name, module in list(sys.modules.items()):
        if name.startswith('newrelic.hooks.'):
            plugins.append(name)

        elif name.find('.') == -1 and hasattr(module, '__file__'):
            try:
                if 'pkg_resources' in sys.modules:
                    version = pkg_resources.get_distribution(name).version
                    if version:
                        name = '%s (%s)' % (name, version)
            except Exception:
                pass
            plugins.append(name)

    env.append(('Plugin List', plugins))

    return env
