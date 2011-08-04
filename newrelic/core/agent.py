'''
Created on Jul 27, 2011

@author: sdaubin
'''

import threading

import newrelic.core.config

from newrelic.core.remote import JSONRemote
from newrelic.core.harvest import Harvester
from newrelic.core.application import Application

class Agent(object):

    _lock = threading.Lock()
    _instance = None

    @staticmethod
    def _singleton():
        Agent._lock.acquire()
        try:
            if not Agent._instance:
                settings = newrelic.core.config.global_settings()
                Agent._instance = Agent(settings)
            return Agent._instance
        finally:
            Agent._lock.release()

    def __init__(self, config):
        print "Starting the New Relic agent"
        self._remote = JSONRemote(config.license_key, config.host, config.port)

        self._applications = {}
        self._harvester = Harvester(self._remote,60)

    def settings(self, name=None):
        if name is None:
            return newrelic.core.config.global_settings()
        return newrelic.core.config.application_settings(name)

    def activate(self, name, clusters=[]):

	# FIXME What is the appropriate term for these
	# secondary application names to report as other
	# than clusters. Want to maintain them as a
	# distinct item from primary name.

        clusters = sorted(set(clusters))

        application = self._applications.get(name, None)
        if application:
            if application.clusters() != clusters:
                # FIXME What should we do here. The set of additional
                # agents has changed since we first activated agent.
                pass
        else:
            application = Application(self._remote, name, clusters)
            self._applications[name] = application
            self._harvester.register_harvest_listener(application)

    def application(self, name):
        return self._application.get(name, None)

    @property
    def applications(self):
        """
        Returns a dictionary of applications keyed off the application name.
        """
        return self._applications

    def stop(self):
        for app in self._applications.itervalues():
            app.stop()
        self._harvester.stop()
        self._applications.clear()

    def shutdown(self):
        self._harvester.stop_harvest_thread()

    @property
    def remote(self):
        return self._remote

    def send(self, name, data):
        print 'DATA', name, data

def agent():
    return Agent._singleton()
