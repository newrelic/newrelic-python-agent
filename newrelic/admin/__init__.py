from __future__ import print_function

import sys
import logging

_builtin_plugins = [
    'data_source',
    'debug_console',
    'generate_config',
    'license_key',
    'local_config',
    'network_config',
    'rum_footer',
    'rum_header',
    'run_program',
    'run_python',
    'server_config',
    'validate_config'
]

_commands = {}

def command(name, options='', description='', hidden=False):
    def wrapper(callback):
        callback.name = name
        callback.options = options
        callback.description = description
        callback.hidden = hidden
        _commands[name] = callback
        return callback
    return wrapper

def usage(name):
    details = _commands[name]
    print('Usage: newrelic-admin %s %s' % (name, details.options))

@command('help', '[command]', hidden=True)
def help(args):
    if not args:
        print('Usage: newrelic-admin command [options]')
        print()
        print("Type 'newrelic-admin help <command>'", end='')
        print("for help on a specific command.")
        print()
        print("Available commands are:")

        commands = sorted(_commands.keys())
        for name in commands:
            details = _commands[name]
            if not details.hidden:
                print(' ', name)

    else:
        name = args[0]

        if name not in _commands:
            print("Unknown command '%s'." % name, end=' ')
            print("Type 'newrelic-admin help' for usage.")

        else:
            details = _commands[name]

            print('Usage: newrelic-admin %s %s' % (name, details.options))
            if details.description:
                print()
                print(details.description)

def load_internal_plugins():
    for name in _builtin_plugins:
        module_name = '%s.%s' % (__name__, name)
        __import__(module_name)

def load_external_plugins():
    try:
        import pkg_resources
    except ImportError:
        return

    group = 'newrelic.admin'

    for entrypoint in pkg_resources.iter_entry_points(group=group):
        __import__(entrypoint.module_name)

def main():
    try:
        if len(sys.argv) > 1:
            command = sys.argv[1]
        else:
            command = 'help'

        callback = _commands[command]

    except Exception:
        print("Unknown command '%s'." % command, end='')
        print("Type 'newrelic-admin help' for usage.")
        sys.exit(1)

    callback(sys.argv[2:])

load_internal_plugins()
load_external_plugins()

if __name__ == '__main__':
    main()
