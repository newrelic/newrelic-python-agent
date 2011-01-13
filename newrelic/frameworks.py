# vi: set sw=4 expandtab :

import threading

# Interface for capturing information about framework being used
# and the gateway into code which performs any framework
# specific fixups to allow for monitoring of the framework. At
# present the captured information is not returned to the RPM
# GUI as not possible to return global information after the
# first connection to the local daemon. If that changes then we
# can pass back this information then.

_lock = threading.RLock()

_frameworks = {}

def _instrument(application, framework):
    _lock.acquire()

    try:
        settings = _frameworks.get(framework, {})

        if settings:
            return settings

        if framework == 'Django':
            import fixups_django
            settings = fixups_django._instrument(application)
            _frameworks[framework] = settings

    finally:
        _lock.release()

    return settings
