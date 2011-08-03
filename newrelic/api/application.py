import os
import threading

import newrelic.core.config

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

class Application(object):

    _lock = threading.Lock()
    _instances = {}

    @staticmethod
    def _instance(name):
        Application._lock.acquire()
        try:
            instance = Application._instances.get(name, None)
            if not instance:
                instance = Application(name)
                Application._instances[name] = instance
            return instance
        finally:
            Application._lock.release()

    def __init__(self, name):
        self._name = name
        self._clusters = {}
        self.enabled = True

    @property
    def name(self):
        return self._name

    @property
    def clusters(self):
        return self._clusters.keys()

    @property
    def settings(self):
        # XXX For now return global settings.
        #return newrelic.core.config.application_settings(self._name)
        return newrelic.core.config.global_settings()

    @property
    def active(self):
        return self.settings is not None

    def add_to_cluster(self, name):
        self._clusters[name] = True

    def activate(self):
        pass

    def shutdown(self):
        pass

    def record_metric(self, name, value):
        pass

def application(name):
    return Application._instance(name)

if _agent_mode not in ('julunggul',):
    import _newrelic
    application = _newrelic.application
    Application = _newrelic.Application
