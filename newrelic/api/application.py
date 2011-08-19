import threading

import newrelic.core.config
import newrelic.core.agent

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
        self._linked = {}
        self.enabled = True

        self._agent = newrelic.core.agent.agent()

    @property
    def name(self):
        return self._name

    @property
    def settings(self):
        global_settings = self._agent.global_settings()
        if global_settings.debug.ignore_all_server_settings:
            return global_settings
        return self._agent.application_settings(self._name)

    @property
    def active(self):
        return self.settings is not None

    def activate(self):
        self._agent.activate_application(self._name, self._linked)

    def shutdown(self):
        pass

    @property
    def linked_applications(self):
        return self._linked.keys()

    def link_to_application(self, name):
        self._linked[name] = True

    def record_metric(self, name, value):
        if self.active:
            self._agent.record_metric(self._name, name, value)

    def record_transaction(self, data):
        if self.active:
            self._agent.record_transaction(self._name, data)

def application(name):
    return Application._instance(name)
