"""This module holds the Agent class which is the primary interface for
interacting with the agent core.

"""

import time
import logging
import threading
import atexit

import newrelic
import newrelic.core.log_file
import newrelic.core.config
import newrelic.core.remote
import newrelic.core.application
import newrelic.core.database_utils

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
                Agent._instance.activate_agent()
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
        self._config = config

        self._harvest_thread = threading.Thread(target=self._harvest_loop,
                name='NR-Harvest-Thread')
        self._harvest_thread.setDaemon(True)
        self._harvest_shutdown = threading.Event()

        if self._config.monitor_mode:
            atexit.register(self.shutdown_agent)

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

    def activate_application(self, app_name, linked_applications=[],
                             timeout=0.0):
        """Initiates activation for the named application if this has
        not been done previously. If an attempt to trigger the
        activation of the application has already been performed,
        whether or not that has completed, calling this again will
        have no affect.

        The list of linked applications is the additional applications
        to which data should also be reported in addition to the primary
        application.

        The timeout is how long to wait for the initial connection. The
        timeout only applies the first time a specific named application
        is being activated. The timeout would be used by test harnesses
        and can't really be used by activation of application for first
        request because it can take up to a second for initial handshake
        to get back configuration settings for application.

        """

        if not self._config.monitor_mode:
            return

        Agent._lock.acquire()
        try:
            application = self._applications.get(app_name, None)
            if not application:
                linked_applications = sorted(set(linked_applications))
                application = newrelic.core.application.Application(
                        self._remote, app_name, linked_applications)
                application.activate_session()
                if timeout:
                    application.wait_for_session_activation(timeout)
                self._applications[app_name] = application
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
            return name, False

        return application.normalize_name(name)

    def _harvest_loop(self):
        now = time.time()

        self._next_harvest = ((now-(now+30.0)%60.0)+60.0)

        while True:
            if self._harvest_shutdown.isSet():
                # We would have just finished a harvest or only
                # just started the agent, so don't bother doing
                # a forced harvest if shutting down anyway.

                return

            now = time.time()
            delay = self._next_harvest - now
            self._next_harvest += 60.0

            if delay > 0.0:
                self._harvest_shutdown.wait(delay) 
                if self._harvest_shutdown.isSet(): 
                    # Force a final harvest on agent shutdown.

                    self._run_harvest()
                    return

            self._run_harvest()

            # Something really went wrong here and we are overdue
            # already for next harvest. Skip it and wait until the
            # next harvest time instead.

            # FIXME Should harvest period be configuration setting.

            now = time.time()
            while self._next_harvest < now:
                self._next_harvest += 60.0

            # Expire entries from any caches which are being kept.

            # FIXME Make number of harvest periods that cache entries
            # are kept for configurable.

            newrelic.core.database_utils.sql_properties_cache.expire(3)

    def _run_harvest(self):
        # If we can't even get a connection at the start of this
        # harvest then pass on doing all the applications.

        connection = None

        try:
            connection = self._remote.create_connection()

        except:
            _logger.exception('Failed to create connection, aborting '
                              'harvest for all applications.')

        else:
            # This isn't going to maintain order of applications
            # such that oldest is always done first. A new one
            # could come in earlier once added and upset the
            # overall timing. The data collector should cope
            # with this though.

            for application in self._applications.values():
                    # Last application to be harvested this time
                    # around failed and we must have closed the
                    # connection. Attempt to create a new
                    # connection so can we can try remaining
                    # applications. If we can't get a new connection
                    # though then we skip remainder of applications.

                    try:
                        if not connection:
                            connection = self._remote.create_connection()
                    except:
                        _logger.exception('Failed to create connection, '
                                          'aborting harvest.')

                        break

                    else:
                        # Connection okay. Harvest single application.

                        try:
                            application.harvest(connection)

                        except:
                            _logger.exception('Failed to harvest data '
                                              'for %s.' % application.name)

                            # For any sort of failure, close and null out
                            # the connection. If more applications still to
                            # go then will create a connection again for it
                            # when enter loop again above.

                            try:
                                connection.close()
                            except:
                                _logger.exception('Failed to '
                                                  'close connection.')

                            connection = None

            else:
                if connection:
                    try:
                        connection.close()
                    except:
                        _logger.exception('Failed to close connection.')

    def activate_agent(self):
        if not self._config.monitor_mode:
            return
        if self._harvest_thread.isAlive():
            return
        self._harvest_thread.start()

    def shutdown_agent(self, timeout=None):
        if self._harvest_shutdown.isSet():
            return

        if timeout is None:
            timeout = self._config.shutdown_timeout

        _logger.info('New Relic Python Agent Shutdown')

        self._harvest_shutdown.set()
        self._harvest_thread.join(timeout)

def agent():
    """Returns the agent object. This function should always be used and
    instances of the agent object should never be created directly to
    ensure there is only ever one instance.

    Network connection details and the licence key needed to initialise the
    agent must have been set in the global default configuration settings
    prior to the first call of this function.

    """

    return Agent._singleton()
