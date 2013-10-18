from __future__ import print_function

from newrelic.admin import command, usage

@command('run-python', '...',
"""Executes the Python interpreter with the supplied arguments but forces
the initialisation of the agent automatically at startup.

If using an agent configuration file the path to the file should be
supplied by the environment variable NEW_RELIC_CONFIG_FILE. Alternatively,
just the licence key, application and log file details can be supplied via
environment variables NEW_RELIC_LICENSE_KEY, NEW_RELIC_APP_NAME and
NEW_RELIC_LOG.""")
def run_python(args):
    import os
    import sys

    from newrelic import version, __file__ as root_directory
    root_directory = os.path.dirname(root_directory)
    boot_directory = os.path.join(root_directory, 'bootstrap')

    if 'PYTHONPATH' in os.environ:
        python_path = "%s:%s" % (boot_directory, os.environ['PYTHONPATH'])
    else:
        python_path = boot_directory

    os.environ['PYTHONPATH'] = python_path

    os.environ['NEW_RELIC_ADMIN_COMMAND'] = repr(sys.argv)

    # We want to still call any local sitecustomize.py file
    # that we are overriding.

    local_sitecustomize = None

    if 'NEW_RELIC_SITE_CUSTOMIZE' in os.environ:
        del os.environ['NEW_RELIC_SITE_CUSTOMIZE']

    if 'sitecustomize' in sys.modules:
        local_sitecustomize = sys.modules['sitecustomize']
        if hasattr(local_sitecustomize, '__file__'):
            os.environ['NEW_RELIC_SITE_CUSTOMIZE'] = (
                    local_sitecustomize.__file__)
        else:
            local_sitecustomize = None

    # Heroku does not set #! line on installed Python scripts
    # correctly and instead does an activate_this fiddle once
    # script has started. The value of sys.executable is
    # therefore wrong. Need to do a fiddle here to ensure we
    # pick up the Python executable in the same directory as
    # this script in preference to that used to execute this
    # script.

    bin_directory = os.path.dirname(sys.argv[0])

    if bin_directory:
        python_exe = os.path.basename(sys.executable)
        python_exe_path = os.path.join(bin_directory, python_exe)
        if (not os.path.exists(python_exe_path) or
                not os.access(python_exe_path, os.X_OK)):
            python_exe_path = sys.executable
    else:
        python_exe_path = sys.executable

    debug_startup = os.environ.get('NEW_RELIC_STARTUP_DEBUG',
            'off').lower() in ('on', 'true', '1')

    if debug_startup:
        import time

        def _log(text, *args):
            text = text % args
            print('NEWRELIC: %s (%d) - %s' % (time.strftime(
                    '%Y-%m-%d %H:%M:%S', time.localtime()),
                    os.getpid(), text))

        _log('New Relic Admin Script (%s)', version)

        _log('working_directory = %r', os.getcwd())
        _log('current_command = %r', sys.argv)

        for name in sorted(os.environ.keys()):
            if name.startswith('NEW_RELIC_') or name.startswith('PYTHON'):
                _log('%s = %r', name, os.environ.get(name))

        _log('root_directory = %r', root_directory)
        _log('boot_directory = %r', boot_directory)

        if local_sitecustomize is not None:
            _log('local_sitecustomize = %r', local_sitecustomize.__file__)

        _log('python_exe_path = %r', python_exe_path)
        _log('execl_arguments = %r', [python_exe_path, python_exe_path]+args)

    os.execl(python_exe_path, python_exe_path, *args)
