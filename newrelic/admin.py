import sys

if __name__ == '__main__':
    if len(sys.argv) == 1 :
        print "Usage: python -m newrelic.admin command"
        raise SystemExit(1)

    try:
        command = sys.argv[1]
        name = 'newrelic.scripts.%s' % command
        __import__(name)
        module = sys.modules[name]
        function = getattr(module, 'run')
    except:
        print "Error: unrecognised command '%s'" % command
        raise SystemExit(1)

    function(sys.argv[1:])
