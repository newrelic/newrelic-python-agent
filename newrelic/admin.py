import os
import sys
import time
import logging

_commands = {}

def command(name, options='', desc=''):
    def wrapper(func):
        if name:
            _commands[name] = (func, options, desc)
        return func
    return wrapper

def usage(name):
    print 'Usage: newrelic-admin %s %s' % (name, _commands[name][1])

def initialize_logging():
    import newrelic.core.log_file

    newrelic.core.log_file.initialize()

    # Send any errors or warnings to standard output as well so more
    # obvious as use may have trouble finding the relevant messages in
    # the agent log as it will be full of debug output as well.

    class FilteredStreamHandler(logging.StreamHandler):
        def emit(self, record):
            if len(logging.root.handlers) != 0:
                return

            if record.name.startswith('newrelic.lib'):
                return

            if record.levelno < logging.WARNING:
                return

            return logging.StreamHandler.emit(self, record)

    _stdout_logger = logging.getLogger('newrelic')
    _stdout_handler = FilteredStreamHandler(sys.stdout)
    _stdout_format = '%(levelname)s - %(message)s\n'
    _stdout_formatter = logging.Formatter(_stdout_format)
    _stdout_handler.setFormatter(_stdout_formatter)
    _stdout_logger.addHandler(_stdout_handler)

@command(None)
def help(args):
    if not args:
        print 'Usage: newrelic-admin command [options]'
        print
        print "Type 'newrelic-admin help <command>'",
        print "for help on a specific command."
        print
        print "Available commands are:"

        commands = sorted(_commands.keys())
        for name in commands:
            print ' ', name

    else:
        name = args[0]

        if name not in _commands:
            print "Unknown command '%s'." % name,
            print "Type 'newrelic-admin help' for usage."

        else:
            print 'Usage: newrelic-admin %s %s' % (name, _commands[name][1])
            if _commands[name][2]:
                print
                print _commands[name][2]

@command('generate-config', 'license_key [output_file]',
"""Generates a sample agent configuration file for <license_key>.""")
def generate_config(args):
    if len(args) == 0:
        usage('generate-config')
        return

    import newrelic

    config_file = os.path.join(os.path.dirname(
            newrelic.__file__), 'newrelic.ini')

    content = open(config_file, 'r').read()

    if len(args) >= 1:
        content = content.replace('*** REPLACE ME ***', args[0])

    if len(args) >= 2 and args[1] != '-':
        output_file = open(args[1], 'w')
        output_file.write(content)
        output_file.close()
    else:
        print content

@command('validate-config', 'config_file [log_file]',
"""Validates the syntax of <config_file>. Also tests connectivity to New
Relic core application by connecting to the account corresponding to the
license key listed in the configuration file, and reporting test data under
the application name 'Python Agent Test'.""")
def validate_config(args):
    if len(args) == 0:
        usage('validate-config')
        return

    import newrelic.api.settings
    import newrelic.api.function_trace
    import newrelic.api.error_trace
    import newrelic.api.web_transaction
    import newrelic.api.background_task
    import newrelic.api.application

    import newrelic.config
    import newrelic.agent

    _settings = newrelic.api.settings.settings()

    if len(args) >= 2:
        _settings.log_file = args[1]
    else:
        _settings.log_file = '/tmp/python-agent-test.log'

    _settings.log_level = logging.DEBUG

    try:
        os.unlink(_settings.log_file)
    except:
        pass

    initialize_logging()

    _logger = logging.getLogger(__name__)
    _logger.debug('Starting agent validation.')

    config_file = args[0]

    if config_file == '-':
        config_file = None

    newrelic.agent.initialize(config_file, ignore_errors=False,
               log_file=_settings.log_file, log_level=_settings.log_level)

    app_name = os.environ.get('NEW_RELIC_TEST_APP_NAME', 'Python Agent Test')

    _settings.app_name = app_name
    _settings.transaction_tracer.transaction_threshold = 0
    _settings.capture_params = True
    _settings.shutdown_timeout = 30.0

    _settings.debug.log_data_collector_calls = True
    _settings.debug.log_malformed_json_data = True

    @newrelic.api.function_trace.function_trace()
    def _function1():
        time.sleep(0.1)

    @newrelic.api.function_trace.function_trace()
    def _function2():
        for i in range(10):
            _function1()

    @newrelic.api.error_trace.error_trace()
    @newrelic.api.function_trace.function_trace()
    def _function3():
        raise RuntimeError('error')
     
    @newrelic.api.web_transaction.wsgi_application()
    def _wsgi_application(environ, start_response):
        status = '200 OK'
        output = 'Hello World!'

        response_headers = [('Content-type', 'text/plain'),
                            ('Content-Length', str(len(output)))]
        start_response(status, response_headers)

        for i in range(10):
            _function1()

        _function2()

        try:
            _function3()
        except:
            pass

        return [output]

    @newrelic.api.background_task.background_task()
    def _background_task():
        for i in range(10):
            _function1()

        _function2()

        try:
            _function3()
        except:
            pass

    def _start_response(*args):
        pass


    print
    print 'Running Python agent test.'
    print
    print 'Look for data in the New Relic UI under the application:'
    print
    print '  %s' % _settings.app_name
    print
    print 'Any significant errors in performing the test will be shown'
    print 'below. If no errors occured and data is still not getting'
    print 'through to the UI after 5 minutes then check the log file:'
    print
    print '  %s' % _settings.log_file
    print
    print 'for debugging information. Supply the log file to New Relic'
    print 'support if requesting help with resolving any issues with'
    print 'the test not reporting data to the New Relic UI.'
    print

    _logger.debug('Register test application.')

    _logger.debug('Collector host is %r.', _settings.host)
    _logger.debug('Collector port is %r.', _settings.port)

    _logger.debug('Proxy host is %r.', _settings.proxy_host)
    _logger.debug('Proxy port is %r.', _settings.proxy_port)
    _logger.debug('Proxy user is %r.', _settings.proxy_user)

    _logger.debug('SSL enabled is %r.', _settings.ssl)

    _logger.debug('License key is %r.', _settings.license_key)

    _application = newrelic.api.application.application_instance()

    _timeout = 30.0

    _start = time.time()
    _status = _application.activate(timeout=_timeout)
    _end = time.time()

    _duration = _end - _start

    if not _application.active:
        _logger.error('Unable to register application for test, '
            'connection could not be established within %s seconds.',
            _timeout)
        return

    _logger.debug('Registration took %s seconds.', _duration)

    _logger.debug('Run the validation test.')

    _environ = { 'SCRIPT_NAME': '', 'PATH_INFO': '/test',
                 'QUERY_STRING': 'key=value' }

    _iterable = _wsgi_application(_environ, _start_response)
    _iterable.close()

    #_background_task()

@command('local-config', 'config_file [log_file]',
"""Dumps out the local agent configuration after having loaded the settings
from <config_file>.""")
def local_config(args):
    if len(args) == 0:
        usage('local-config')
        return

    import newrelic.core.config

    import newrelic.api.settings

    import newrelic.agent

    _settings = newrelic.api.settings.settings()

    if len(args) >= 2:
        _settings.log_file = args[1]
    else:
        _settings.log_file = '/tmp/python-agent-test.log'

    _settings.log_level = logging.DEBUG

    try:
        os.unlink(_settings.log_file)
    except:
        pass

    initialize_logging()

    _logger = logging.getLogger(__name__)

    config_file = args[0]

    if config_file == '-':
        config_file = None

    newrelic.agent.initialize(config_file, ignore_errors=False,
               log_file=_settings.log_file, log_level=_settings.log_level)

    config = newrelic.core.config.flatten_settings(_settings)

    keys = config.keys()
    keys.sort()

    for key in keys:
        print '%s = %s' % (key, repr(config[key]))

@command('server-config', 'config_file [log_file]',
"""Dumps out the agent configuration after having loaded the settings
from <config_file>, registered the application and then merged the server
side configuration. The application name as specified in the agent
configuration file is used.""")
def remote_config(args):
    if len(args) == 0:
        usage('server-config')
        return

    import newrelic.core.config

    import newrelic.api.settings

    import newrelic.agent

    _settings = newrelic.api.settings.settings()

    if len(args) >= 2:
        _settings.log_file = args[1]
    else:
        _settings.log_file = '/tmp/python-agent-test.log'

    _settings.log_level = logging.DEBUG

    try:
        os.unlink(_settings.log_file)
    except:
        pass

    initialize_logging()

    _logger = logging.getLogger(__name__)

    config_file = args[0]

    if config_file == '-':
        config_file = None

    newrelic.agent.initialize(config_file, ignore_errors=False,
               log_file=_settings.log_file, log_level=_settings.log_level)

    _application = newrelic.api.application.application_instance()

    _timeout = 30.0

    _start = time.time()
    _status = _application.activate(timeout=_timeout)
    _end = time.time()

    _duration = _end - _start

    if not _application.active:
        _logger.error('Unable to register application for test, '
            'connection could not be established within %s seconds.',
            _timeout)
        return

    _logger.debug('Registration took %s seconds.', _duration)

    config = newrelic.core.config.flatten_settings(_application.settings)

    keys = config.keys()
    keys.sort()

    for key in keys:
        print '%s = %s' % (key, repr(config[key]))

@command('license-key', 'config_file [log_file]',
"""Prints out the account license key after having loaded the settings
from <config_file>.""")
def license_key(args):
    if len(args) == 0:
        usage('local-config')
        return

    import newrelic.core.config

    import newrelic.api.settings

    import newrelic.agent

    _settings = newrelic.api.settings.settings()

    if len(args) >= 2:
        _settings.log_file = args[1]
    else:
        _settings.log_file = '/tmp/python-agent-test.log'

    _settings.log_level = logging.DEBUG

    try:
        os.unlink(_settings.log_file)
    except:
        pass

    initialize_logging()

    _logger = logging.getLogger(__name__)

    config_file = args[0]

    if config_file == '-':
        config_file = None

    newrelic.agent.initialize(config_file, ignore_errors=False,
               log_file=_settings.log_file, log_level=_settings.log_level)

    print 'license_key = %s' % repr(_settings.license_key)

@command('network-config', 'config_file [log_file]',
"""Prints out the network configuration after having loaded the settings
from <config_file>.""")
def network_config(args):
    if len(args) == 0:
        usage('network-config')
        return

    import newrelic.core.config

    import newrelic.api.settings

    import newrelic.agent

    _settings = newrelic.api.settings.settings()

    if len(args) >= 2:
        _settings.log_file = args[1]
    else:
        _settings.log_file = '/tmp/python-agent-test.log'

    _settings.log_level = logging.DEBUG

    try:
        os.unlink(_settings.log_file)
    except:
        pass

    initialize_logging()

    _logger = logging.getLogger(__name__)

    config_file = args[0]

    if config_file == '-':
        config_file = None

    newrelic.agent.initialize(config_file, ignore_errors=False,
               log_file=_settings.log_file, log_level=_settings.log_level)

    print 'host = %s' % repr(_settings.host)
    print 'port = %s' % repr(_settings.port)
    print 'proxy_host = %s' % repr(_settings.proxy_host)
    print 'proxy_port = %s' % repr(_settings.proxy_port)
    print 'proxy_user = %s' % repr(_settings.proxy_user)
    print 'proxy_pass = %s' % repr(_settings.proxy_pass)
    print 'ssl = %s' % repr(_settings.ssl)

@command('rum-header', '',
"""Prints out the RUM header.""")
def rum_footer(args):
    if len(args) != 0:
        usage('rum-header')
        return

    import newrelic.api.web_transaction

    print newrelic.api.web_transaction._rum_header_fragment

@command('rum-footer', 'config_file path [log_file]',
"""Prints out the RUM footer for a resource with the supplied path.
The application name as specified in the agent configuration file is
used.""")
def rum_footer(args):
    if len(args) < 2:
        usage('rum-footer')
        return

    import newrelic.core.config

    import newrelic.api.settings

    import newrelic.agent

    _settings = newrelic.api.settings.settings()

    if len(args) >= 3:
        _settings.log_file = args[2]
    else:
        _settings.log_file = '/tmp/python-agent-test.log'

    _settings.log_level = logging.DEBUG

    try:
        os.unlink(_settings.log_file)
    except:
        pass

    initialize_logging()

    _logger = logging.getLogger(__name__)

    config_file = args[0]

    if config_file == '-':
        config_file = None

    newrelic.agent.initialize(config_file, ignore_errors=False,
               log_file=_settings.log_file, log_level=_settings.log_level)

    _application = newrelic.api.application.application_instance()

    _timeout = 30.0

    _start = time.time()
    _status = _application.activate(timeout=_timeout)
    _end = time.time()

    _duration = _end - _start

    if not _application.active:
        _logger.error('Unable to register application test, '
            'connection could not be established within %s seconds.',
            _timeout)
        return

    import newrelic.api.web_transaction

    footer = newrelic.api.web_transaction._rum_footer_long_fragment

    metric = 'WebTransaction/Static/%s' % args[1]

    name = newrelic.api.web_transaction._obfuscate(metric,
            _application.settings.license_key)

    print str(footer % (_application.settings.episodes_file,
        _application.settings.beacon, _application.settings.browser_key,
        _application.settings.application_id, name, 0, 0))

@command('run-python', '...',
"""Executes the Python interpreter with the supplied arguments but forces
the initialisation of the agent automatically at startup.
         
If using an agent configuration file the path to the file should be
supplied by the environment variable NEW_RELIC_CONFIG_FILE. Alternatively,
just the licence key, application and log file details can be supplied via
environment variables NEW_RELIC_LICENSE_KEY, NEW_RELIC_APP_NAME and
NEW_RELIC_LOG.""")
def run_python(args):
    import newrelic

    root_directory = os.path.dirname(newrelic.__file__)
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
            print 'NEWRELIC: %s (%d) - %s' % (time.strftime(
                    '%Y-%m-%d %H:%M:%S', time.localtime()),
                    os.getpid(), text)

        _log('New Relic Admin Script (%s)', newrelic.version)

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

@command('run-program', '...',
"""Executes the command line but forces the initialisation of the agent
automatically at startup.
         
If using an agent configuration file the path to the file should be
supplied by the environment variable NEW_RELIC_CONFIG_FILE. Alternatively,
just the licence key, application and log file details can be supplied via
environment variables NEW_RELIC_LICENSE_KEY, NEW_RELIC_APP_NAME and
NEW_RELIC_LOG.""")
def run_program(args):
    if len(args) == 0:
        print "Type 'newrelic-admin help run-program' for usage."
        sys.exit(1)

    import newrelic

    root_directory = os.path.dirname(newrelic.__file__)
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

    program_exe_path = args[0]

    # If not an absolute or relative path, then we need to
    # see if program can be found in PATH. Note that can
    # be found in current working directory even though '.'
    # not in PATH.

    if not os.path.dirname(program_exe_path):
        program_search_path = os.environ.get('PATH', '').split(':')
        for path in program_search_path:
            path = os.path.join(path, program_exe_path)
            if os.path.exists(path) and os.access(path, os.X_OK):
                program_exe_path = path
                break

    debug_startup = os.environ.get('NEW_RELIC_STARTUP_DEBUG',
            'off').lower() in ('on', 'true', '1')

    if debug_startup:
        import time

        def _log(text, *args):
            text = text % args
            print 'NEWRELIC: %s (%d) - %s' % (time.strftime(
                    '%Y-%m-%d %H:%M:%S', time.localtime()),
                    os.getpid(), text)

        _log('New Relic Admin Script (%s)', newrelic.version)

        _log('working_directory = %r', os.getcwd())
        _log('current_command = %r', sys.argv)

        for name in sorted(os.environ.keys()):
            if name.startswith('NEW_RELIC_') or name.startswith('PYTHON'):
                _log('%s = %r', name, os.environ.get(name))

        _log('root_directory = %r', root_directory) 
        _log('boot_directory = %r', boot_directory) 

        if local_sitecustomize is not None:
            _log('local_sitecustomize = %r', local_sitecustomize.__file__) 

        _log('program_exe_path = %r', program_exe_path) 
        _log('execl_arguments = %r', [program_exe_path]+args) 

    os.execl(program_exe_path, *args)

@command('debug-console', 'config_file [session_log]',
"""Runs the client for the embedded agent debugging console.
""")
def debug_console(args):
    if len(args) == 0:
        usage('agent-console')
        return

    import newrelic.console

    config_file = args[0]
    log_object = None

    if len(args) >= 2:
        log_object = open(args[1], 'w')

    shell = newrelic.console.ClientShell(config_file, log=log_object)
    shell.cmdloop()

def main():
    if len(sys.argv) == 1:
        print "Type 'newrelic-admin help' for usage."
        sys.exit(1)

    try:
        command = sys.argv[1]

        if command != 'help':
            function = _commands[command][0]
        else:
            function = help
    except:
        print "Unknown command '%s'." % command,
        print "Type 'newrelic-admin help' for usage."
        sys.exit(1)

    function(sys.argv[2:])

if __name__ == '__main__':
    main()
