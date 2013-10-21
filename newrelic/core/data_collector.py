"""This module implements the communications layer with the data collector.

"""

import logging
import os
import socket
import sys
import time
import zlib
import json

import newrelic.packages.six as six

import newrelic.packages.requests as requests

from newrelic import version
from newrelic.core.config import global_settings, create_settings_snapshot
from newrelic.core.internal_metrics import (internal_trace, InternalTrace,
        internal_metric)

from newrelic.network.exceptions import (NetworkInterfaceException,
        ForceAgentRestart, ForceAgentDisconnect, DiscardDataForRequest,
        RetryDataForRequest, ServerIsUnavailable)

from ..network.addresses import proxy_details
from ..common.object_wrapper import patch_function_wrapper

_logger = logging.getLogger(__name__)

# User agent string that must be used in all requests. The data collector
# does not rely on this, but is used to target specific agents if there
# is a problem with data collector handling requests.

USER_AGENT = 'NewRelic-PythonAgent/%s (Python %s %s)' % (
         version, sys.version.split()[0], sys.platform)

# Data collector URL and proxy settings.

def collector_url(server=None):
    """Returns the URL for talking to the data collector. When no server
    'host:port' is specified then the main data collector host and port is
    taken from the agent configuration. When a server is explicitly passed
    it would be the secondary data collector which subsequents requests
    in an agent session should be sent to.

    """

    settings = global_settings()

    url = '%s://%s/agent_listener/invoke_raw_method'

    scheme = settings.ssl and 'https' or 'http'

    if not server:
        # When pulling port from agent configuration it should only be
        # set when testing against a local data collector. For staging
        # and production should not be set and would default to port 80
        # or 443 based on scheme name in URL and we don't explicitly
        # add the ports.

        if settings.port:
            server = '%s:%d' % (settings.host, settings.port)
        else:
            server = '%s' % settings.host

    return url % (scheme, server)

def proxy_server():
    """Returns the dictionary of proxy server settings to be supplied to
    the 'requests' library when making requests.

    """

    # For backward compatibility from when using requests prior to 2.0.0,
    # we take the proxy_scheme as not being set to mean that we should
    # derive it from whether SSL is being used. This will still be overridden
    # if the proxy scheme was defined as part of proxy URL in proxy_host.

    settings = global_settings()

    ssl = settings.ssl
    proxy_scheme = settings.proxy_scheme

    if proxy_scheme is None:
        proxy_scheme = ssl and 'https' or 'http'

    return proxy_details(proxy_scheme, settings.proxy_host,
            settings.proxy_port, settings.proxy_user, settings.proxy_pass)

# This is a monkey patch for urllib3 contained within our bundled requests
# library. This is to override the urllib3 behaviour for how the proxy
# is communicated with so as to allow us to restore the old broken
# behaviour from before requests 2.0.0 so that we can transition
# customers over without outright breaking their existing configurations.

@patch_function_wrapper(
        'newrelic.packages.requests.packages.urllib3.connectionpool',
        'HTTPSConnectionPool._prepare_conn')
def _requests_proxy_scheme_workaround(wrapped, instance, args, kwargs):
    def _params(connection, *args, **kwargs):
        return connection

    pool, connection = instance, _params(*args, **kwargs)

    settings = global_settings()

    if pool.proxy and pool.proxy.scheme == 'https':
        if settings.proxy_scheme in (None, 'https'):
            return connection

    return wrapped(*args, **kwargs)

# Low level network functions and session management. When connecting to
# the data collector it is initially done through the main data collector.
# It is though then necessary to ask the data collector for the per
# session data collector to use. Subsequent calls are then made to it.

def send_request(session, url, method, license_key, agent_run_id=None,
            payload=()):
    """Constructs and sends a request to the data collector."""

    params = {}
    headers = {}
    config = {}

    settings = global_settings()

    start = time.time()

    # Validate that the license key was actually set and if not replace
    # it with a string which makes it more obvious it was not set.

    if not license_key:
        license_key = 'NO LICENSE KEY WAS SET IN AGENT CONFIGURATION'

    # The agent formats requests and is able to handle responses for
    # protocol version 12.

    params['method'] = method
    params['license_key'] = license_key
    params['protocol_version'] = '12'
    params['marshal_format'] = 'json'

    if agent_run_id:
        params['run_id'] = str(agent_run_id)

    headers['User-Agent'] = USER_AGENT
    headers['Content-Encoding'] = 'identity'

    # Set up definitions for proxy server in case that has been set.

    proxies = proxy_server()

    # At this time we use JSON content encoding for the data being sent.
    # If an error does occur when encoding the JSON, then it isn't
    # likely going to work later on in a subsequent request with same
    # data, even if aggregated with other data, so we need to log the
    # details and then flag that data should be thrown away. Don't mind
    # being noisy in the the log in this situation as it would indicate
    # a problem with the implementation of the agent.

    try:
        with InternalTrace('Supportability/Collector/JSON/Encode/%s' % method):
            data = json.dumps(payload, default=lambda o: list(iter(o)))

    except Exception:
        _logger.exception('Error encoding data for JSON payload for '
                'method %r with payload of %r. Please report this problem '
                'to New Relic support.', method, payload)

        raise DiscardDataForRequest(str(sys.exc_info()[1]))

    # Log details of call and/or payload for debugging. Use the JSON
    # encoded value so know that what is encoded is correct.

    if settings.debug.log_data_collector_payloads:
        _logger.debug('Calling data collector with url=%r, method=%r and '
                'payload=%r.', url, method, data)
    elif settings.debug.log_data_collector_calls:
        _logger.debug('Calling data collector with url=%r and method=%r.',
                url, method)

    # Compress the serialized JSON being sent as content if over 64KiB
    # in size. If less than 2MB in size compress for speed. If over
    # 2MB then compress for smallest size. This parallels what the Ruby
    # agent does.

    if len(data) > 64*1024:
        headers['Content-Encoding'] = 'deflate'
        level = (len(data) < 2000000) and 1 or 9

        internal_metric('Supportability/Collector/ZLIB/Bytes/%s' % method,
                len(data))

        with InternalTrace('Supportability/Collector/ZLIB/Compress/'
                '%s' % method):
            data = zlib.compress(six.b(data), level)

    # If there is no requests session object provided for making
    # requests create one now. We want to close this as soon as we
    # are done with it.

    auto_close_session = False

    if not session:
        session = requests.session()
        auto_close_session = True

    # The 'requests' library can raise a number of exception derived
    # from 'RequestException' before we even manage to get a connection
    # to the data collector.
    #
    # The data collector can the generate a number of different types of
    # HTTP errors for requests. These are:
    #
    # 400 Bad Request - For incorrect method type or incorrectly
    # construct parameters. We should not get this and if we do it would
    # likely indicate a problem with the implementation of the agent.
    #
    # 413 Request Entity Too Large - Where the request content was too
    # large. The limits on number of nodes in slow transaction traces
    # should in general prevent this, but not everything has size limits
    # and so rogue data could still blow things out. Same data is not
    # going to work later on in a subsequent request, even if aggregated
    # with other data, so we need to log the details and then flag that
    # data should be thrown away.
    #
    # 415 Unsupported Media Type - This occurs when the JSON which was
    # sent can't be decoded by the data collector. If this is a true
    # problem with the JSON formatting, then sending again, even if
    # aggregated with other data, may not work, so we need to log the
    # details and then flag that data should be thrown away.
    #
    # 503 Service Unavailable - This occurs when data collector, or core
    # application is being restarted and not in state to be able to
    # accept requests. It should be a transient issue so should be able
    # to retain data and try again.

    internal_metric('Supportability/Collector/Output/Bytes/%s' % method,
            len(data))

    try:
        # The timeout value in the requests module is only on
        # the initial connection and doesn't apply to how long
        # it takes to get back a response.

        timeout = settings.agent_limits.data_collector_timeout

        r = session.post(url, params=params, headers=headers,
                proxies=proxies, timeout=timeout, data=data)

        # Read the content now so we can force close the socket
        # connection if this is a transient session as quickly
        # as possible.

        content = r.content

    except requests.RequestException:
        if not settings.proxy_host or not settings.proxy_port:
            _logger.warning('Data collector is not contactable. This can be '
                    'because of a network issue or because of the data '
                    'collector being restarted. In the event that contact '
                    'cannot be made after a period of time then please '
                    'report this problem to New Relic support for further '
                    'investigation. The error raised was %r.',
                    sys.exc_info()[1])
        else:
            _logger.warning('Data collector is not contactable via the proxy '
                    'host %r on port %r with proxy user of %r. This can be '
                    'because of a network issue or because of the data '
                    'collector being restarted. In the event that contact '
                    'cannot be made after a period of time then please '
                    'report this problem to New Relic support for further '
                    'investigation. The error raised was %r.',
                    settings.proxy_host, settings.proxy_port,
                    settings.proxy_user, sys.exc_info()[1])

        raise RetryDataForRequest(str(sys.exc_info()[1]))

    finally:
        if auto_close_session:
            session.close()
            session = None

    if r.status_code != 200:
        _logger.debug('Received a non 200 HTTP response from the data '
                'collector where url=%r, method=%r, license_key=%r, '
                'agent_run_id=%r, params=%r, headers=%r, status_code=%r '
                'and content=%r.', url, method, license_key, agent_run_id,
                params, headers, r.status_code, content)

    if r.status_code == 400:
        _logger.error('Data collector is indicating that a bad '
                'request has been submitted for url %r, headers of %r, '
                'params of %r and payload of %r. Please report this '
                'problem to New Relic support.', url, headers, params,
                payload)

        raise DiscardDataForRequest()

    elif r.status_code == 413:
        _logger.warning('Data collector is indicating that a request for '
                'method %r was received where the request content size '
                'was over the maximum allowed size limit. The length of '
                'the request content was %d. If this keeps occurring on a '
                'regular basis, please report this problem to New Relic '
                'support for further investigation.', method, len(data))

        raise DiscardDataForRequest()

    elif r.status_code == 415:
        _logger.warning('Data collector is indicating that it was sent '
                'malformed JSON data for method %r. If this keeps occurring '
                'on a regular basis, please report this problem to New '
                'Relic support for further investigation.', method)

        if settings.debug.log_malformed_json_data:
            if headers['Content-Encoding'] == 'deflate':
                data = zlib.decompress(data)

            _logger.info('JSON data which was rejected by the data '
                    'collector was %r.', data)

        raise DiscardDataForRequest(content)

    elif r.status_code == 503:
        _logger.warning('Data collector is unavailable. This can be a '
                'transient issue because of the data collector or our '
                'core application being restarted. If the issue persists '
                'it can also be indicative of a problem with our servers. '
                'In the event that availability of our servers is not '
                'restored after a period of time then please report this '
                'problem to New Relic support for further investigation.')

        raise ServerIsUnavailable()

    elif r.status_code != 200:
        if not settings.proxy_host or not settings.proxy_port:
            _logger.warning('An unexpected HTTP response was received from '
                    'the data collector of %r for method %r. The payload for '
                    'the request was %r. If this issue persists then please '
                    'report this problem to New Relic support for further '
                    'investigation.', r.status_code, method, payload)
        else:
            _logger.warning('An unexpected HTTP response was received from '
                    'the data collector of %r for method %r while connecting '
                    'via proxy host %r on port %r with proxy user of %r. '
                    'The payload for the request was %r. If this issue '
                    'persists then please report this problem to New Relic '
                    'support for further investigation.', r.status_code,
                    method, settings.proxy_host, settings.proxy_port,
                    settings.proxy_user, payload)

        raise DiscardDataForRequest()

    # Log details of response payload for debugging. Use the JSON
    # encoded value so know that what original encoded value was.

    duration = time.time() - start

    if settings.debug.log_data_collector_payloads:
        _logger.debug('Valid response from data collector after %.2f '
                'seconds with content=%r.', duration, content)
    elif settings.debug.log_data_collector_calls:
        _logger.debug('Valid response from data collector after %.2f '
                'seconds.', duration)

    # If we got this far we should have a legitimate response from the
    # data collector. The response is JSON so need to decode it.

    internal_metric('Supportability/Collector/Input/Bytes/%s' % method,
            len(content))

    try:
        with InternalTrace('Supportability/Collector/JSON/Decode/%s' % method):
            if six.PY3:
                content = content.decode('UTF-8')

            result = json.loads(content)

    except Exception:
        _logger.exception('Error decoding data for JSON payload for '
                'method %r with payload of %r. Please report this problem '
                'to New Relic support.', method, content)

        if settings.debug.log_malformed_json_data:
            _logger.info('JSON data received from data collector which '
                    'could not be decoded was %r.', content)

        raise DiscardDataForRequest(str(sys.exc_info()[1]))

    # The decoded JSON can be either for a successful response or an
    # error. A successful response has a 'return_value' element and an
    # error an 'exception' element.

    if 'return_value' in result:
        return result['return_value']

    error_type = result['exception']['error_type']
    message = result['exception']['message']

    # Now need to check for server side exceptions. The following
    # exceptions can occur for abnormal events.

    _logger.debug('Received an exception from the data collector where '
            'url=%r, method=%r, license_key=%r, agent_run_id=%r, params=%r, '
            'headers=%r, error_type=%r and message=%r', url, method,
            license_key, agent_run_id, params, headers, error_type,
            message)

    if error_type == 'NewRelic::Agent::LicenseException':
        _logger.error('Data collector is indicating that an incorrect '
                'license key has been supplied by the agent. The value '
                'which was used by the agent is %r. Please correct any '
                'problem with the license key or report this problem to '
                'New Relic support.', license_key)

        raise DiscardDataForRequest(message)

    elif error_type == 'NewRelic::Agent::PostTooBigException':
        _logger.warning('Core application is indicating that a request for '
                'method %r was received where the request content size '
                'was over the maximum allowed size limit. The length of '
                'the request content was %d. If this keeps occurring on a '
                'regular basis, please report this problem to New Relic '
                'support for further investigation.', method, len(data))

        raise DiscardDataForRequest(message)

    # Server side exceptions are also used to inform the agent to
    # perform certain actions such as restart when server side
    # configuration has changed for this application or when agent is
    # being disabled remotely for some reason.

    if error_type == 'NewRelic::Agent::ForceRestartException':
        _logger.info('An automatic internal agent restart has been '
                'requested by the data collector for the application '
                'where the agent run was %r. The reason given for the '
                'forced restart is %r.', agent_run_id, message)

        raise ForceAgentRestart(message)

    elif error_type == 'NewRelic::Agent::ForceDisconnectException':
        _logger.critical('Disconnection of the agent has been requested by '
                'the data collector for the application where the '
                'agent run was %r. The reason given for the forced '
                'disconnection is %r. Please contact New Relic support '
                'for further information.', agent_run_id, message)

        raise ForceAgentDisconnect(message)

    # We received an unexpected server side error we don't know what
    # to do with.

    _logger.warning('An unexpected server error was received from the '
            'data collector for method %r with payload of %r. The error '
            'was of type %r with message %r. If this issue persists '
            'then please report this problem to New Relic support for '
            'further investigation.', method, payload, error_type, message)

    raise DiscardDataForRequest(message)


class ApplicationSession(object):

    """ Class which encapsulates communication with the data collector
    once the initial registration has been done.

    """

    def __init__(self, collector_url, license_key, configuration):
        self.collector_url = collector_url
        self.license_key = license_key
        self.configuration = configuration
        self.agent_run_id = configuration.agent_run_id

        self._requests_session = None

    @property
    def requests_session(self):
        if self._requests_session is None:
            self._requests_session = requests.session()
        return self._requests_session

    def close_connection(self):
        if self._requests_session:
            self._requests_session.close()
        self._requests_session = None

    @internal_trace('Supportability/Collector/Calls/shutdown')
    def shutdown_session(self):
        """Called to perform orderly deregistration of agent run against
        data collector, rather than simply dropping the connection and
        relying on data collector to surmise that agent run is finished
        due to no more data being reported.

        """

        _logger.debug('Connecting to data collector to terminate session '
                'for agent run %r.', self.agent_run_id)

        result = send_request(self.requests_session, self.collector_url,
                'shutdown', self.license_key, self.agent_run_id)

        _logger.info('Successfully shutdown New Relic Python agent '
                'where app_name=%r, pid=%r, and agent_run_id=%r',
                self.configuration.app_name, os.getpid(),
                self.agent_run_id)

        return result

    @internal_trace('Supportability/Collector/Calls/metric_data')
    def send_metric_data(self, start_time, end_time, metric_data):
        """Called to submit metric data for specified period of time.
        Time values are seconds since UNIX epoch as returned by the
        time.time() function. The metric data should be iterable of
        specific metrics.

        """

        payload = (self.agent_run_id, start_time, end_time, metric_data)

        return send_request(self.requests_session, self.collector_url,
                'metric_data', self.license_key, self.agent_run_id, payload)

    @internal_trace('Supportability/Collector/Calls/error_data')
    def send_errors(self, errors):
        """Called to submit errors. The errors should be an iterable
        of individual errors details.

        NOTE Although the details for each error carries a timestamp,
        the data collector appears to ignore it and overrides it with
        the timestamp that the data is received by the data collector.

        """

        if not errors:
            return

        payload = (self.agent_run_id, errors)

        return send_request(self.requests_session, self.collector_url,
                'error_data',
                self.license_key, self.agent_run_id, payload)

    @internal_trace('Supportability/Collector/Calls/transaction_sample_data')
    def send_transaction_traces(self, transaction_traces):
        """Called to submit transaction traces. The transaction traces
        should be an iterable of individual traces.

        NOTE Although multiple traces could be supplied, the agent is
        currently only reporting on the slowest transaction in the most
        recent period being reported on.

        """

        if not transaction_traces:
            return

        payload = (self.agent_run_id, transaction_traces)

        return send_request(self.requests_session, self.collector_url,
                'transaction_sample_data', self.license_key,
                self.agent_run_id, payload)

    @internal_trace('Supportability/Collector/Calls/send_profile_data')
    def send_profile_data(self, profile_data):
        """Called to submit Profile Data.
        """

        if not profile_data:
            return

        payload = (self.agent_run_id, profile_data)

        return send_request(self.requests_session, self.collector_url,
                'profile_data', self.license_key,
                self.agent_run_id, payload)

    @internal_trace('Supportability/Collector/Calls/sql_trace_data')
    def send_sql_traces(self, sql_traces):
        """Called to sub SQL traces. The SQL traces should be an
        iterable of individual SQL details.

        NOTE The agent currently only reports on the 10 slowest SQL
        queries in the most recent period being reported on.

        """

        if not sql_traces:
            return

        payload = (sql_traces,)

        return send_request(self.requests_session, self.collector_url,
                'sql_trace_data', self.license_key, self.agent_run_id,
                payload)

    @internal_trace('Supportability/Collector/Calls/get_agent_commands')
    def get_agent_commands(self):
        """Receive agent commands from the data collector.

        """

        payload = (self.agent_run_id,)

        return send_request(self.requests_session, self.collector_url,
                'get_agent_commands', self.license_key, self.agent_run_id,
                payload)

    @internal_trace('Supportability/Collector/Calls/send_agent_command_results')
    def send_agent_command_results(self, cmd_results):
        """Acknowledge the receipt of an agent command.

        """

        payload = (self.agent_run_id, cmd_results)

        return send_request(self.requests_session, self.collector_url,
                'agent_command_results', self.license_key, self.agent_run_id,
                payload)

    @internal_trace('Supportability/Collector/Calls/get_xray_metadata')
    def get_xray_metadata(self, xray_id):
        """Receive xray metadata from the data collector.

        """

        payload = (self.agent_run_id, xray_id)

        return send_request(self.requests_session, self.collector_url,
                'get_xray_metadata', self.license_key, self.agent_run_id,
                payload)

    def analytic_event_data(self, sample_set):
        """Called to submit sample set for analytics.

        """

        payload = (self.agent_run_id, sample_set)

        return send_request(self.requests_session, self.collector_url,
                'analytic_event_data', self.license_key, self.agent_run_id,
                payload)

def create_session(license_key, app_name, linked_applications,
        environment, settings):

    """Registers the agent for the specified application with the data
    collector and retrieves the server side configuration. Returns a
    session object if successful through which subsequent calls to the
    data collector are made. If unsucessful then None is returned.

    """

    start = time.time()

    # If no license key provided in the call, fallback to using that
    # from the agent configuration file or environment variables. Flag
    # an error if the result still seems invalid.

    if not license_key:
        license_key = global_settings().license_key

    if not license_key:
        _logger.error('A valid account license key cannot be found. '
            'Has a license key been specified in the agent configuration '
            'file or via the NEW_RELIC_LICENSE_KEY environment variable?')

    try:
        # First need to ask the primary data collector which of the many
        # data collector instances we should use for this agent run.

        _logger.debug('Connecting to data collector to register agent with '
                'license_key=%r, app_name=%r, linked_applications=%r, '
                'environment=%r and settings=%r.', license_key, app_name,
                linked_applications, environment, settings)

        url = collector_url()
        redirect_host = send_request(None, url, 'get_redirect_host',
                license_key)

        # Then we perform a connect to the actual data collector host
        # we need to use. All communications after this point should go
        # to the secondary data collector.
        #
        # We use the global requests session object for now as harvest
        # for different applications are all done in turn. We will need
        # to change this if use multiple threads as currently force
        # session object to maintain only single connection to ensure
        # that keep alive is effective.

        app_names = [app_name] + linked_applications

        local_config = {}

        local_config['pid'] = os.getpid()
        local_config['language'] = 'python'
        local_config['host'] = socket.gethostname()
        local_config['app_name'] = app_names
        local_config['identifier'] = ','.join(app_names)
        local_config['agent_version'] = version
        local_config['environment'] = environment
        local_config['settings'] = settings

        payload = (local_config,)

        url = collector_url(redirect_host)
        server_config = send_request(None, url, 'connect',
                license_key, None, payload)

        # The agent configuration for the application in constructed
        # by taking a snapshot of the locally constructed configuration
        # and overlaying it with that from the server.

        application_config = create_settings_snapshot(server_config)

    except NetworkInterfaceException:
        # The reason for errors of this type have already been logged.
        # No matter what the error we just pass back None. The upper
        # layer needs to count how many success times this has failed
        # and escalate things with a more sever error.

        pass

    except Exception:
        # Any other errors are going to be unexpected and likely will
        # indicate an issue with the implementation of the agent.

        _logger.exception('Unexpected exception when attempting to '
                'register the agent with the data collector. Please '
                'report this problem to New Relic support for further '
                'investigation.')

        pass

    else:
        # Everything fine so we create the session object through which
        # subsequent communication with data collector will be done.

        session = ApplicationSession(url, license_key, application_config)

        duration = time.time() - start

        # Log successful agent registration and any server side messages.

        _logger.info('Successfully registered New Relic Python agent '
                'where app_name=%r, pid=%r, redirect_host=%r and '
                'agent_run_id=%r, in %.2f seconds.', app_name, os.getpid(),
                redirect_host, session.agent_run_id, duration)

        if hasattr(application_config, 'high_security'):
            _logger.info('High security mode is being applied to all '
                    'communications between the agent and the data '
                    'collector for this session.')

        logger_func_mapping = {
            'ERROR': _logger.error,
            'WARN': _logger.warning,
            'INFO': _logger.info,
            'VERBOSE': _logger.debug,
        }

        if 'messages' in server_config:
            for item in server_config['messages']:
                message = item['message']
                level = item['level']
                logger_func = logger_func_mapping.get(level, None)
                if logger_func:
                    logger_func('%s', message)

        return session
