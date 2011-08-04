import os
import threading

import newrelic.core.config
import newrelic.core.agent

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

class Application(object):

    _lock = threading.Lock()
    _instances = {}

    @staticmethod
    def _instance(name):
        Application._lock.acquire()
        try:
            if name is None:
                name = newrelic.core.config.global_settings().app_name
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

        self._agent = newrelic.core.agent.agent()

    @property
    def name(self):
        return self._name

    @property
    def clusters(self):
        return self._clusters.keys()

    @property
    def settings(self):
        if self._agent.settings().debug.ignore_server_settings:
            return self._agent.settings()
        return self._agent.settings(self._name)

    @property
    def active(self):
        return self.settings is not None

    def add_to_cluster(self, name):
        self._clusters[name] = True

    def activate(self):
        self._agent.activate(self._name, self._clusters)

    def shutdown(self):
        pass

    def record_metric(self, name, value):
        pass

    def record_transaction(self, data):
        self._agent.send(self._name, data)

def application(name):
    return Application._instance(name)

if _agent_mode not in ('julunggul',):
    import _newrelic
    application = _newrelic.application
    Application = _newrelic.Application
