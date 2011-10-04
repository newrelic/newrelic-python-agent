"""This module holds the Agent class which is the primary interface for
interacting with the agent core.

"""

import logging
import threading

import newrelic
import newrelic.core.log_file
import newrelic.core.config
import newrelic.core.remote
import newrelic.core.harvest
import newrelic.core.application

_logger = logging.getLogger('newrelic.core.agent')

class Agent(object):

    """Only one instance of the agent should ever exist and that can be
    obtained using the agent() function.

    The licence key information, network connection details for the
    collector, plus whether SSL should be used is obtained directly from
    the global configuration settings. If a proxy has to be used, details
    for that will similarly come from the global configuration settings.

    The global configuration settings would normally be setup from the
    agent configuration file or could also be set explicitly. Direct access
    to global configuration setings prior to the agent instance being
    created needs to be via the 'newrelic.core.config' module.

    After the network connection details have been set, and the agent
    object created and accessed using the agent() function, each individual
    reporting application can be activated using the activate_application()
    method of the agent. The name of the primary application and an
    optional list of linked applications to which metric data should also
    be reported needs to be supplied.

    Once an application has been activated and communications established
    with the core application, the application specific settings, which
    consists of the global default configuration settings overlaid with the
    server side configuration settings can be obtained using the
    application_settings() method. That a valid settings object rather than
    None is returned is the indicator that the application has been
    successfully activated. The application settings object can be
    associated with a transaction so that settings are available for the
    life of the transaction, but should not be cached and used across
    transactions. Instead the application settings object should be
    requested on each transaction to ensure that it is detected whether
    application is still active or not due to a server side triggered
    restart. When such a restart occurs, the application settings could
    change and thus why application settings cannot be cached beyond the
    lifetime of a single transaction.

    """

    _lock = threading.Lock()
    _instance = None

    @staticmethod
    def _singleton():
        """Used by the agent() function to access/create the single
        agent object instance.

        """

        if Agent._instance:
            return Agent._instance

	# Just in case that the main initialisation function
	# wasn't called to read in a configuration file and as
	# such the logging system was not initialised already,
	# we trigger initialisation again here.

        newrelic.core.log_file.initialize()

        _logger.info('New Relic Python Agent (%s)' % \
                     '.'.join(map(str, newrelic.version_info)))

        Agent._lock.acquire()
        try:
            if not Agent._instance:
                _logger.debug('Creating instance of Python agent.')

                settings = newrelic.core.config.global_settings()
                Agent._instance = Agent(settings)
            return Agent._instance
        finally:
            Agent._lock.release()

    def __init__(self, config):
	"""Initialises the agent and attempt to establish a connection
	to the core application. Will start the harvest loop running but
	will not activate any applications.

        """

        license_key = config.license_key

        collector_host = config.host
        collector_port = config.port

        require_ssl = config.ssl

        proxy_host = config.proxy_host
        proxy_port = config.proxy_port
        proxy_user = config.proxy_user
        proxy_pass = config.proxy_pass

        _logger.debug('Initializing Python agent.')

        if proxy_host:
            # FIXME Need to implement proxy support.
            raise NotImplemented('no support for proxy')
        else:
            if require_ssl:
                # FIXME Need to implement SSL support.
                raise NotImplemented('no support for ssl')
            else:
                self._remote = newrelic.core.remote.JSONRemote(
                        config.license_key, config.host, config.port)

        self._applications = {}

        # FIXME Should harvest period be a configuration
        # parameter.

        if config.monitor_mode:
            self._harvester = newrelic.core.harvest.Harvester(self._remote, 60)
        else:
            self._harvester = None

    def global_settings(self):
	"""Returns the global default settings object. If access is
	needed to this prior to initialising the agent, use the
	'newrelic.core.config' module directly.

        """

        return newrelic.core.config.global_settings()

    def application_settings(self, app_name):
	"""Returns the application specific settings object. This only
	returns a valid settings object once a connection has been
	established to the core application and the application server
	side settings have been obtained. If this returns None then
	activate_application() should be used to force activation for
	the agent in case that hasn't been done previously.

        """

        application = self._applications.get(app_name)

        if application:
            return application.configuration

    def activate_application(self, app_name, linked_applications=[]):
	"""Initiates activation for the named application if this has
	not been done previously. If an attempt to trigger the
	activation of the application has already been performed,
	whether or not that has completed, calling this again will
        have no affect.

	The list of linked applications is the additional applications
	to which data should also be reported in addition to the primary
	application.

        """

        if not self._harvester:
            return

	# FIXME To make testing easier, need to be able to supply an
	# argument indicating want to wait for application to be
	# activated. This could be indefinite wait, or be a time value.
        # Should be able to do this based on a thread condition variable.

        linked_applications = sorted(set(linked_applications))

        Agent._lock.acquire()
        try:
            application = self._applications.get(app_name, None)
            if not application:
                application = newrelic.core.application.Application(
                        self._remote, app_name, linked_applications)
                self._applications[app_name] = application
                self._harvester.register_harvest_listener(application)
        finally:
            Agent._lock.release()

    @property
    def applications(self):
	"""Returns a dictionary of the internal application objects
	cooresponding to the applications for which activation has already
	been requested. This does not reflect whether activation has been
	successful or not. To determine if application if currently in an
	activated state use application_settings() method to see if a valid
	application settings objects is available or query the application
        object directly.

        """
        return self._applications

    def application(self, app_name):
	"""Returns the internal application object for the named
	application or None if not activate. When an application object
        is returned, it does not relect whether activation has been
	successful or not. To determine if application if currently in an
	activated state use application_settings() method to see if a valid
	application settings objects is available or query the application
        object directly.

        """

        return self._applications.get(app_name, None)

    def record_metric(self, app_name, name, value):
	"""Records a basic metric for the named application. If there has
	been no prior request to activate the application, the metric is
	discarded.

        """

	# FIXME Are base metrics ignored if the application is not in
	# the activated state when received or are they accumulated?

        application = self._applications.get(app_name, None)
        if application is None:
            return

        application.record_metric(name, value)

    def record_metrics(self, app_name, metrics):
	"""Records the metrics for the named application. If there has
	been no prior request to activate the application, the metric is
	discarded. The metrics should be an iterable yielding tuples
        consisting of the name and value.

        """

	# FIXME Are base metrics ignored if the application is not in
	# the activated state when received or are they accumulated?

        application = self._applications.get(app_name, None)
        if application is None:
            return

        application.record_metrics(metrics)

    def record_transaction(self, app_name, data):
        """Processes the raw transaction data, generating and recording
	appropriate metrics against the named application. If there has
	been no prior request to activate the application, the metric is
	discarded.

        The actual processing of the raw transaction data is performed
        by the process_raw_transaction() function of the module
        'newrelic.core.transaction'.

        """

        application = self._applications.get(app_name, None)
        if application is None:
            return

        application.record_transaction(data)

    def normalize_name(self, app_name, name):
        application = self._applications.get(app_name, None)
        if application is None:
            return name

        return application.normalize_name(name)

    # FIXME The following for managing running state of harvester and
    # applications should probably support the concept of a manually
    # triggered restart. Have to think about the case where a fork of
    # process occurs after this is initialised and new requests handled
    # in the sub process. As is, the higher level instrumentation layer
    # will only activate this agent on the first request which would
    # normally be after the fork. But this doesn't rule out that someone
    # may come up with some odd system where both parent and child
    # handle requests. The parent for example may run background tasks
    # rather than handle specific web requests.

    def stop(self):
        if not self._harvester:
            return

        for app in self._applications.itervalues():
            app.stop()
        self._harvester.stop()
        self._applications.clear()

    def shutdown(self):
        if not self._harvester:
            return

        self._harvester.stop_harvest_thread()

def agent():
    """Returns the agent object. This function should always be used and
    instances of the agent object should never be created directly to
    ensure there is only ever one instance.

    Network connection details and the licence key needed to initialise the
    agent must have been set in the global default configuration settings
    prior to the first call of this function.

    """

    return Agent._singleton()
