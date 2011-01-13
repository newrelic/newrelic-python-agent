# vi: set sw=4 expandtab :

import threading
import atexit

import _newrelic

from frameworks import _instrument

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

_lock = threading.RLock()

_applications = {}
_frameworks = {}

_Application = _newrelic.Application

"""
class _Application(object):

    def __init__(self, instance):
        self.__instance = instance

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        else:
            return getattr(self.__instance, name)

    #def __setattr__(self, name, value):
    #    if name in self.__instance.__dict__:
    #        setattr(self.__instance, name, value)
    #    else:
    #        self.__dict__[name] = value
"""

def initialize(application, framework=None):
    _lock.acquire()

    try:
        instance = _applications.get(application, None)

        if instance and instance.framework != framework:
            raise RuntimeError('framework name has changed')

        if not instance and _frameworks.has_key(framework):
            raise RuntimeError('framework already initialized')

        if instance is None:
            print 'XXX 1'
            settings = _instrument(application, framework)

            instance = _newrelic.Application(application)
            print 'XXX 2'
            # TODO Make application object take settings and push it
            # so it appear in agent configuration.
            #instance = _Application(instance, settings)
            #instance = _Application(instance)

            _frameworks[framework] = settings

            #instance.framework = framework
            #instance.settings = settings

            _applications[framework] = instance

            print 'XXX 3'
            _newrelic.harvest()
            print 'XXX 4'

    finally:
        _lock.release()

    return instance 

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
