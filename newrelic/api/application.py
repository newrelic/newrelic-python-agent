from __future__ import with_statement

import threading
import warnings

import newrelic.core.config
import newrelic.core.agent

class Application(object):

    _lock = threading.Lock()
    _instances = {}

    @staticmethod
    def _instance(name):
        if name is None:
            name = newrelic.core.config.global_settings().app_name

        # Try first without lock. If we find it we can return.

        instance = Application._instances.get(name, None)

        if not instance:
            with Application._lock:
                # Now try again with lock so that only one gets
                # to create and add it.

                instance = Application._instances.get(name, None)
                if not instance:
                    instance = Application(name)
                    Application._instances[name] = instance

        return instance

    def __init__(self, name):
        self._name = name
        self._linked = {}
        self.enabled = True

        self._agent = newrelic.core.agent.agent_instance()

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

    def activate(self, timeout=None):
        # If timeout not supplied then the default from the global
        # configuration will later be used. Note that the timeout only
        # applies on the first call to activate the application.

        self._agent.activate_application(self._name, self._linked, timeout)

    def shutdown(self):
        pass

    @property
    def linked_applications(self):
        return self._linked.keys()

    def link_to_application(self, name):
        self._linked[name] = True

    @property
    def thread_utilization(self):
        return self._agent.thread_utilization(self._name)

    def record_metric(self, name, value):
        if self.active:
            self._agent.record_metric(self._name, name, value)

    def record_metrics(self, metrics):
        if self.active and metrics:
            self._agent.record_metrics(self._name, metrics)

    def record_transaction(self, data):
        if self.active:
            self._agent.record_transaction(self._name, data)

    def normalize_name(self, name, rule_type='url'):
        if self.active:
            return self._agent.normalize_name(self._name, name, rule_type)
        return name, False

def application_instance(name=None):
    return Application._instance(name)

def application():
   warnings.warn('Internal API change. Use application_instance() '
           'instead of application().', DeprecationWarning, stacklevel=2)

   return application_instance()
