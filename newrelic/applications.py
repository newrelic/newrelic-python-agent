# vi: set sw=4 expandtab :

import threading

import _newrelic

from frameworks import _instrument

_lock = threading.RLock()

_applications = {}
_frameworks = {}

def initialize(application, framework=None):
    _lock.acquire()

    try:
        instance = _applications.get(application, None)

        if instance and instance.framework != framework:
            raise RuntimeError('framework name has changed')

        if not instance and _frameworks.has_key(framework):
            raise RuntimeError('framework already initialized')

        if instance is None:
            settings = _instrument(application, framework)
            instance = _newrelic.application(application)
            _frameworks[framework] = settings
            _applications[framework] = instance

    finally:
        _lock.release()

    return instance 
