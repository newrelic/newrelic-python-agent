import sys

if __name__ == '__main__':
    if len(sys.argv) == 1 :
        print "Usage: python -m newrelic.admin command"
        raise SystemExit(1)

    try:
        command = sys.argv[1]
        module = __import__('newrelic.commands.%s' % command)
        module = getattr(module, 'commands')
        module = getattr(module, command)
        function = getattr(module, 'run')
    except:
        print "Error: unrecognised command '%s'" % command
        raise SystemExit(1)

    function(sys.argv[1:])
