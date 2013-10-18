from __future__ import print_function

import sys
import logging

from collections import namedtuple

_commands = {}

_Command = namedtuple('_Command', 'callback name options description hidden')

def command(name, options='', description='', hidden=False):
    def wrapper(callback):
        details = _Command(callback, name, options, description, hidden)
        _commands[name] = details
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
            print("Unknown command '%s'." % name, end='')
            print("Type 'newrelic-admin help' for usage.")

        else:
            details = _commands[name]

            print('Usage: newrelic-admin %s %s' % (name, details.options))
            if details.description:
                print()
                print(details.description)

def load_internal_plugins():
    from . import data_source
    from . import debug_console
    from . import generate_config
    from . import license_key
    from . import local_config
    from . import network_config
    from . import rum_footer
    from . import rum_header
    from . import run_program
    from . import run_python
    from . import server_config
    from . import validate_config

def load_external_plugins():
    pass

def main():
    try:
        if len(sys.argv) > 1:
            command = sys.argv[1]
        else:
            command = 'help'

        callback = _commands[command].callback

    except Exception:
        print("Unknown command '%s'." % command, end='')
        print("Type 'newrelic-admin help' for usage.")
        sys.exit(1)

    callback(sys.argv[2:])

load_internal_plugins()
load_external_plugins()

if __name__ == '__main__':
    main()
