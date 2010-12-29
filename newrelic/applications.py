# vi: set sw=4 expandtab :

import threading
import atexit

import _newrelic

# We ensure only single application object for a specific name
# is created as it is the Python object and not the internal
# agent client application instance that holds the 'enabled'
# flag indicating whether monitoring for this agent is being
# performed. If allow multiple instances of the application
# object then disabling it in one will not disable any of the
# transactions triggered via another instance of the application
# for the same named application. We also force a harvest when
# first creating an instance of an application because the local
# daemon will not accept metrics the first time if it does not
# know about the application. This forced harvest primes it and
# ensures that it talks to RPM to get configuration so that when
# next harvest occurs it doesn't reject metrics data. This is
# especially important where process generating metrics is short
# lived.

_applications_lock = threading.RLock()
_applications = {}

def Application(name):

    _applications_lock.acquire()

    application = _applications.get(name, None)

    if application is None:
        application = _newrelic.Application(name)
        _applications[name] = application
        _newrelic.harvest()

    _applications_lock.release()

    return application 

# A harvest will only normally be forced when all the
# application objects are destroyed. Because application objects
# are cached by above code then would only occur when Python is
# destroying all the loaded modules. Force a harvest of data
# when registered exit handlers are run. This should be before
# when modules are being destroyed and everything still in place
# in memory. Note that some hosting mechanisms, such as
# mod_python, make use of Python sub interpreters but exit
# callbacks are not triggered within sub interpreters, only the
# main interpreter. Thus this will still not be called. If using
# mod_wsgi there is no problem as it explicitly triggers exit
# callbacks for sub interpreters even though Python itself does
# not do it.

atexit.register(_newrelic.harvest)
