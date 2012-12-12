"""This module provides functions to collect information about the operating
system, Python and hosting environment.

"""

import sys
import os
import platform

from newrelic.core.samplers import cpu_count

def environment_settings():
    """Returns an array of arrays of environment settings

    """

    env = []

    # Agent information.

    import newrelic

    env.append(('Agent Version', '.'.join(map(str, newrelic.version_info))))

    if 'NEW_RELIC_ADMIN_COMMAND' in os.environ:
        env.append(('Admin Command', os.environ['NEW_RELIC_ADMIN_COMMAND']))
        del os.environ['NEW_RELIC_ADMIN_COMMAND']

    # System information.

    env.append(('Arch', platform.machine()))
    env.append(('OS', platform.system()))
    env.append(('OS version', platform.release()))
    env.append(('CPU Count', cpu_count()))

    # Python information.

    env.append(('Python Program Name', sys.argv[0]))

    env.append(('Python Executable', sys.executable))

    env.append(('Python Home', os.environ.get('PYTHONHOME', '')))
    env.append(('Python Path', os.environ.get('PYTHONPATH', '')))

    env.append(('Python Prefix', sys.prefix))
    env.append(('Python Exec Prefix', sys.exec_prefix))

    # TODO May be too sensitive and UI truncates information.

    #env.append(('Python Module Path', str(sys.path)))

    env.append(('Python Version', sys.version))
    env.append(('Python Platform', sys.platform))

    env.append(('Python Max Unicode', sys.maxunicode))

    try:
	# This may fail if using package Python and the
	# developer package for Python isn't also installed.

        import distutils.sysconfig

        # TODO The UI truncates information.

        args = distutils.sysconfig.get_config_var('CONFIG_ARGS')
        #env.append(('Python Config Args', args))

    except:
        pass

    # Extensions information.

    extensions = []

    try:
        import newrelic.core._thread_utilization
        extensions.append('newrelic.core._thread_utilization')
    except:
        pass

    try:
        import newrelic.lib.simplejson._speedups
        extensions.append('newrelic.lib.simplejson._speedups')
    except:
        pass

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

    # TODO This produces too much. Can be over 1000 modules for a Django
    # application. Try restricting it to just top level modules and no
    # sub modules in packages, plus drop any builtin modules. Bit hard
    # to restrict it further because hard under virtual environments to
    # try and identify what modules may be part of the actual Python
    # installation and perhaps dropped.

    #env.append(('Plugin List', list(sys.modules.keys())))

    #env.append(('Plugin List', filter(
    #        lambda x: x.find('.') == -1, sys.modules.keys())))

    plugins = []

    for name, module in sys.modules.items():
        if name.find('.') == -1 and hasattr(module, '__file__'):
            try:
                import pkg_resources
                version = pkg_resources.get_distribution(name).version
                if version:
                    name = '%s (%s)' % (name, version)
            except:
                pass
            plugins.append(name)

    env.append(('Plugin List', plugins))

    return env
