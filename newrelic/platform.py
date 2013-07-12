import os
import logging
import functools
import time
import zlib
import sys
import signal
import threading
import socket
import atexit

import newrelic.packages.requests as requests
import newrelic.packages.simplejson as json

from newrelic import version as agent_version

from ConfigParser import RawConfigParser, NoOptionError

_logger = logging.getLogger(__name__)

_LOG_LEVEL = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
}

_LOG_FORMAT = '%(asctime)s (%(process)d/%(threadName)s) ' \
              '%(name)s %(levelname)s - %(message)s'

_log_file = None
_log_level = None

class RequestsConnectionFilter(logging.Filter):
    def filter(self, record):
        return False

_requests_logger = logging.getLogger(
    'newrelic.packages.requests.packages.urllib3.connectionpool')
_requests_logger.addFilter(RequestsConnectionFilter())

_config_object = RawConfigParser()

def _config_read(config_file):
    _config_object.read([config_file])

def _config_option(name, section='newrelic', type=None, **kwargs):
    try:
        getter = 'get%s' % (type or '')
        return getattr(_config_object, getter)(section, name)
    except NoOptionError:
        if 'default' in kwargs:
            return kwargs['default']
        else:
            raise

def _config_options(section):
    return _config_object.items(section)

def _config_sections():
    return _config_object.sections()

_license_key = None

_collector_host = 'platform-api.newrelic.com'
_collector_port = None
_collector_ssl = True

_proxy_host = None
_proxy_port = None
_proxy_user = None
_proxy_pass = None

_collector_timeout = 30.0

_data_sources = []

def read_data_source(section):
    enabled = _config_option('enabled', section, 'boolean', default=True)

    if not enabled:
        return

    function = _config_option('function', section)
    (module_name, object_path) = function.split(':', 1)

    settings = {}
    properties = {}

    name = _config_option('name', section=section, default=None)
    config = _config_option('settings', section=section, default=None)

    if config:
        settings.update(_config_options(section=config))

    properties.update(_config_options(section=section))

    properties.pop('enabled', None)
    properties.pop('function', None)
    properties.pop('name', None)
    properties.pop('settings', None)

    _logger.debug("register data-source %s" % (
            (module_name, object_path, name),))

    try:
        module = __import__(module_name)
        for part in module_name.split('.')[1:]:
            module = getattr(module, part)
        parts = object_path.split('.')
        source = getattr(module, parts[0])
        for part in parts[1:]:
            source = getattr(source, part)

    except Exception:
        _logger.exception('Attempt to load data source %s:%s with '
                'name %r from section %r of agent configuration file '
                'has failed. Data source will be skipped.', module_name,
                object_path, name, section)

    else:
        _data_sources.append((section, module, object_path, name,
                settings, properties, source))

def read_configuration(config_file):
    _config_read(config_file)

    global _license_key

    global _collector_host
    global _collector_port
    global _collector_ssl

    global _proxy_host
    global _proxy_port
    global _proxy_user
    global _proxy_pass

    global _collector_timeout

    global _log_file
    global _log_level

    _license_key = os.environ.get('NEW_RELIC_LICENSE_KEY')
    _license_key = _config_option('license_key', default=_license_key)

    _collector_host = _config_option('host', default=_collector_host)
    _collector_port = _config_option('port', type='int', default=None)
    _collector_ssl = _config_option('ssl', type='boolean', default=True)

    _proxy_host = _config_option('proxy_host', default=None)
    _proxy_port = _config_option('proxy_port', type='int', default=None)
    _proxy_user = _config_option('proxy_user', default=None)
    _proxy_pass = _config_option('proxy_pass', default=None)

    _collector_timeout = _config_option('agent_limits.data_collector_timeout',
            type='float', default=30.0)

    _log_file = os.environ.get('NEW_RELIC_LOG_FILE')
    _log_file = _config_option('log_file', default=_log_file)

    if _log_file in ('stdout', 'stderr'):
        _log_file = None

    _log_level = os.environ.get('NEW_RELIC_LOG_LEVEL', 'INFO').upper()
    _log_level = _config_option('log_level', default=_log_level).upper()

    if _log_level in _LOG_LEVEL:
        _log_level = _LOG_LEVEL[_log_level]
    else:
        _log_level = logging.INFO

def register_data_sources():
    for section in _config_sections():
        if not section.startswith('data-source:'):
            continue
        read_data_source(section)

# User agent string that must be used in all requests. The data collector
# does not rely on this, but is used to target specific agents if there
# is a problem with data collector handling requests.

USER_AGENT = 'NewRelic-PythonAgent/%s (Python %s %s)' % (
         agent_version, sys.version.split()[0], sys.platform)

# Internal exceptions that can be generated in network layer. These are
# use to control what the upper levels should do. Any actual details of
# errors would already be logged at the network level.

class NetworkInterfaceException(Exception): pass
class ForceAgentRestart(NetworkInterfaceException): pass
class ForceAgentDisconnect(NetworkInterfaceException): pass
class DiscardDataForRequest(NetworkInterfaceException): pass
class RetryDataForRequest(NetworkInterfaceException): pass
class ServerIsUnavailable(RetryDataForRequest): pass

# Data collector URL and proxy settings.

def collector_url(server=None):
    """Returns the URL for talking to the data collector. When no server
    'host:port' is specified then the main data collector host and port is
    taken from the agent configuration. When a server is explicitly passed
    it would be the secondary data collector which subsequents requests
    in an agent session should be sent to.

    """

    url = '%s://%s/platform/v1/metrics'

    scheme = _collector_ssl and 'https' or 'http'

    if not server:
        # When pulling port from agent configuration it should only be
        # set when testing against a local data collector. For staging
        # and production should not be set and would default to port 80
        # or 443 based on scheme name in URL and we don't explicitly
        # add the ports.

        if _collector_port:
            server = '%s:%d' % (_collector_host, _collector_port)
        else:
            server = '%s' % _collector_host

    return url % (scheme, server)

def proxy_server():
    """Returns the dictionary of proxy server settings to be supplied to
    the 'requests' library when making requests.

    """

    # Require that both proxy host and proxy port are set to work.

    if not _proxy_host or not _proxy_port:
        return

    # The agent configuration only provides means to set one proxy so we
    # assume that it will be set correctly depending on whether SSL
    # connection requested or not.

    scheme = _collector_ssl and 'https' or 'http'
    proxy = '%s:%d' % (_proxy_host, _proxy_port)

    # Encode the proxy user name and password into the proxy server value
    # as requests library will strip it out of there and use that.

    if _proxy_user is not None and _proxy_pass is not None:
        proxy = 'http://%s:%s@%s' % (_proxy_user, _proxy_pass, proxy)

    return { scheme: proxy }

# This is a hack to work around a design flaw in the requests/urllib3
# modules we currently bundle. Together they do not close the socket
# connections in the connection pool when evicted, nor provide a way to
# explicitly close connections still in the pool when a session ends. We
# can get rid of this when we are able to drop Python 2.5 support and
# upgrade to a newer requests version. When we do upgrade to the newest
# requests library, we will be able to call close() on the session
# object to force close connections.

def close_requests_session(session, url=None):
    try:
        for connection_pool in session.poolmanager.pools.values():
            try:
                connection = connection_pool.pool.get_nowait()
            except Exception:
                connection = None

            while connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

                try:
                    connection = connection_pool.pool.get_nowait()
                except Exception:
                    connection = None
    except Exception:
        pass

# Low level network functions. Calls are always made via the main collector.

def send_request(url, license_key, payload=()):
    """Constructs and sends a request to the data collector."""

    headers = {}
    config = {}

    start = time.time()

    # Validate that the license key was actually set and if not replace
    # it with a string which makes it more obvious it was not set.

    if not license_key:
        license_key = 'NO LICENSE KEY WAS SET IN AGENT CONFIGURATION'

    headers['User-Agent'] = USER_AGENT
    headers['Content-Encoding'] = 'identity'
    headers['X-License-Key'] = license_key

    # Set up definitions for proxy server in case that has been set.

    proxies = proxy_server()

    # At this time we use JSON content encoding for the data being
    # sent. Ensure that normal byte strings are interpreted as Latin-1
    # and that the final result is ASCII so that don't need to worry
    # about converting back to bytes again. We set the default fallback
    # encoder to treat any iterable as a list. Unfortunately the JSON
    # library can't use it as an iterable and so means that generator
    # will be consumed up front and everything collected in memory as a
    # list before then converting to JSON.
    #
    # If an error does occur when encoding the JSON, then it isn't
    # likely going to work later on in a subsequent request with same
    # data, even if aggregated with other data, so we need to log the
    # details and then flag that data should be thrown away. Don't mind
    # being noisy in the the log in this situation as it would indicate
    # a problem with the implementation of the agent.

    try:
        data = json.dumps(payload, ensure_ascii=True, encoding='Latin-1')

    except Exception, exc:
        _logger.error('Error encoding data for JSON payload '
                'with payload of %r. Exception which occurred was %r. '
                'Please report this problem to New Relic support.',
                payload, exc)

        raise DiscardDataForRequest(str(exc))

    # Log details of call and/or payload for debugging. Use the JSON
    # encoded value so know that what is encoded is correct.

    _logger.debug('Calling data collector to report custom metrics '
            'with payload=%r.', data)

    # Compress the serialized JSON being sent as content if over 64KiB
    # in size. If less than 2MB in size compress for speed. If over
    # 2MB then compress for smallest size. This parallels what the Ruby
    # agent does.

    if len(data) > 64*1024:
        headers['Content-Encoding'] = 'deflate'
        level = (len(data) < 2000000) and 1 or 9
        data = zlib.compress(data, level)

    # The 'requests' library can raise a number of exception derived
    # from 'RequestException' before we even manage to get a connection
    # to the data collector. The data collector can the generate a
    # number of different types of HTTP errors for requests.

    try:
        session_config = {}
        session_config['keep_alive'] = True
        session_config['pool_connections'] = 1
        session_config['pool_maxsize'] = 1

        cert_loc = certifi.where()

        session = requests.session(config=session_config, verify=cert_loc)

        r = session.post(url, headers=headers, proxies=proxies,
                timeout=_collector_timeout, data=data)

        # Read the content now so we can force close the socket
        # connection if this is a transient session as quickly
        # as possible.

        content = r.content

    except requests.RequestException, exc:
        if not _proxy_host or not _proxy_port:
            _logger.warning('Data collector is not contactable. This can be '
                    'because of a network issue or because of the data '
                    'collector being restarted. In the event that contact '
                    'cannot be made after a period of time then please '
                    'report this problem to New Relic support for further '
                    'investigation. The error raised was %r.', exc)
        else:
            _logger.warning('Data collector is not contactable via the proxy '
                    'host %r on port %r with proxy user of %r. This can be '
                    'because of a network issue or because of the data '
                    'collector being restarted. In the event that contact '
                    'cannot be made after a period of time then please '
                    'report this problem to New Relic support for further '
                    'investigation. The error raised was %r.',
                    _proxy_host, _proxy_port, _proxy_user, exc)

        raise RetryDataForRequest(str(exc))

    finally:
        try:
            session.close()
        except AttributeError:
            close_requests_session(session)

    if r.status_code != 200:
        _logger.debug('Received a non 200 HTTP response from the data '
                'collector where url=%r, license_key=%r, headers=%r, '
                'status_code=%r and content=%r.', url, license_key,
                headers, r.status_code, r.content)

    if r.status_code == 400:
        if headers['Content-Encoding'] == 'deflate':
            data = zlib.uncompress(data)

        _logger.error('Data collector is indicating that a bad '
                'request has been submitted for url %r, headers of %r '
                'and payload of %r with response of %r. Please report '
                'this problem to New Relic support.', url, headers, data,
                r.content)

        raise DiscardDataForRequest()

    elif r.status_code == 403:
        _logger.error('Data collector is indicating that the license '
                'key %r is not valid.', license_key)

        raise DiscardDataForRequest()

    elif r.status_code == 413:
        _logger.warning('Data collector is indicating that a request '
                'was received where the request content size '
                'was over the maximum allowed size limit. The length of '
                'the request content was %d. If this keeps occurring on a '
                'regular basis, please report this problem to New Relic '
                'support for further investigation.', len(data))

        raise DiscardDataForRequest()

    elif r.status_code in  (503, 504):
        _logger.warning('Data collector is unavailable. This can be a '
                'transient issue because of the data collector or our '
                'core application being restarted. If the issue persists '
                'it can also be indicative of a problem with our servers. '
                'In the event that availability of our servers is not '
                'restored after a period of time then please report this '
                'problem to New Relic support for further investigation.')

        raise ServerIsUnavailable()

    elif r.status_code != 200:
        if not _proxy_host or not _proxy_port:
            _logger.warning('An unexpected HTTP response was received from '
                    'the data collector of %r. The payload for '
                    'the request was %r. If this issue persists then please '
                    'report this problem to New Relic support for further '
                    'investigation.', r.status_code, payload)
        else:
            _logger.warning('An unexpected HTTP response was received from '
                    'the data collector of %r while connecting '
                    'via proxy host %r on port %r with proxy user of %r. '
                    'The payload for the request was %r. If this issue '
                    'persists then please report this problem to New Relic '
                    'support for further investigation.', r.status_code,
                    _proxy_host, _proxy_port, _proxy_user, payload)

        raise DiscardDataForRequest()

    # Log details of response payload for debugging. Use the JSON
    # encoded value so know that what original encoded value was.

    duration = time.time() - start

    _logger.debug('Valid response from data collector after %.2f '
            'seconds with content=%r.', duration, r.content)

    # If we got this far we should have a legitimate response from the
    # data collector. The response is JSON so need to decode it.
    # Everything will come back as Unicode. Make sure all strings are
    # decoded as 'UTF-8'.

    try:
        result = json.loads(r.content, encoding='UTF-8')

    except Exception, exc:
        _logger.error('Error decoding data for JSON payload '
                'with payload of %r. Exception which occurred was %r. '
                'Please report this problem to New Relic support.',
                r.content, exc)

        raise DiscardDataForRequest(str(exc))

    # The decoded JSON can be either for a successful response or an
    # error. A successful response has a 'return_value' element and an
    # error an 'exception' element.

    if 'status' in result:
        return result['status']

    error_message = result['error']

    # Now need to check for server side exceptions. The following
    # exceptions can occur for abnormal events.

    _logger.debug('Received an exception from the data collector where '
            'url=%r, license_key=%r, headers=%r and error_message=%r. ',
            url, license_key, headers, error_message)

    raise DiscardDataForRequest(error_message)

class DataStats(dict):

    """Bucket for accumulating custom metrics in format required for
    platform agent API.

    """

    # Is based on a dict all metrics are sent to the core
    # application as that and list as base class means it
    # encodes direct to JSON as we need it.

    def __init__(self, count=0, total=0.0, min=0.0, max=0.0,
            sum_of_squares=0.0):
        self.count = count
        self.total = total
        self.min = min
        self.max = max
        self.sum_of_squares = sum_of_squares

    def __setattr__(self, name, value):
        self[name] = value

    def __getattr__(self, name):
        return self[name]

    def merge_stats(self, other):
        """Merge data from another instance of this object."""

        self.total += other.total
        self.min = self.count and min(self.min, other.min) or other.min
        self.max = max(self.max, other.max)
        self.sum_of_squares += other.sum_of_squares

        # Must update the call count last as update of the
        # minimum call time is dependent on initial value.

        self.count += other.count

    def merge_value(self, value):
        """Merge data from a value."""

        self.total += value
        self.min = self.count and min(self.min, value) or value
        self.max = max(self.max, value)
        self.sum_of_squares += value ** 2

        # Must update the call count last as update of the
        # minimum call time is dependent on initial value.

        self.count += 1

class DataSampler(object):

    def __init__(self, consumer, source, name, settings, **properties):
        self.consumer = consumer

        self.properties = source(settings)

        self.factory = self.properties['factory']
        self.instance =  None

        self.properties.update(properties)

        self.name = (name or self.properties.get('name') or source.__name__)

        self.group = self.properties.get('group')

        if self.group:
            self.group = self.group.rstrip('/')

        self.guid = self.properties.get('guid')

        if self.guid is None and hasattr(source, 'guid'):
            self.guid = source.guid

        self.version = self.properties.get('version')

        if self.version is None and hasattr(source, 'version'):
            self.version = source.version

        environ = {}

        environ['consumer.name'] = consumer
        environ['consumer.vendor'] = 'New Relic'
        environ['producer.name'] = self.name
        environ['producer.group'] = self.group
        environ['producer.guid'] = self.guid
        environ['producer.version'] = self.version

        self.environ = environ

        _logger.debug('Initialising data sampler for %r.', self.environ)

        # Need this when reporting data using platform agent API.

        self.period_start = 0.0
        self.metrics_table = None

    def start(self):
        if self.instance is None:
            self.instance = self.factory(self.environ)
        if hasattr(self.instance, 'start'):
            self.instance.start()

        self.period_start = time.time()
        self.metrics_table = None

    def stop(self):
        if hasattr(self.instance, 'stop'):
            self.instance.stop()
        else:
            self.instance = None

        self.period_start = 0.0
        self.metrics_table = None

    def metrics(self):
        assert self.instance is not None

        if self.group:
            return (('%s/%s' % (self.group, key), value)
                    for key, value in self.instance())
        else:
            return self.instance()

    def upload(self):
        assert self.instance is not None

        if not self.period_start:
            return

        session = None
        url = collector_url()
        license_key = _license_key

        now = time.time()

        duration = now - self.period_start

        agent = {}
        agent['host'] = socket.gethostname()
        agent['pid'] = os.getpid()

        if self.version:
            agent['version'] = self.version
        else:
            agent['version'] = '?.?.?'

        component = {}
        component['name'] = self.name
        component['guid'] = self.guid
        component['duration'] = duration

        metrics = self.metrics_table or {}
        self.metrics_table = None

        component['metrics'] = metrics

        payload = {}
        payload['agent'] = agent
        payload['components'] = [component]

        try:
            for name, value in self.metrics():
                stats = metrics.get(name)
                if stats is None:
                    stats = DataStats()
                    metrics[name] = stats

                try:
                    try:
                        stats.merge_stats(DataStats(*value))
                    except Exception:
                        stats.merge_value(value)

                except Exception:
                    _logger.exception('The merging of custom metric '
                            'sample %r from data sampler %r has failed. '
                            'Validate the format of the sample. If this '
                            'issue persists then please report this '
                            'problem to the data source provider or New '
                            'Relic support for further investigation.',
                            value, self.name)
                    break

        except Exception:
            _logger.exception('The processing of custom metrics from '
                    'data sampler %r has failed.  If this issue persists '
                    'then please report this problem to the data source '
                    'provider or New Relic support for further '
                    'investigation.', self.name)

            return []

        try:
            send_request(url, license_key, payload)

        except RetryDataForRequest:
            # Throw away data if cannot report data after 5
            # minutes if trying.

            if duration < 300:
                self.metrics_table = metrics

            else:
                _logger.exception('Unable to report data custom metrics '
                        'from data sampler %r for a period of 5 minutes. '
                        'Data being discarded. If this issue persists '
                        'then please report this problem to the data source '
                        'provider or New Relic support for further '
                        'investigation.', self.name)

                self.metrics_table = None
                self.period_start = now

        except DiscardDataForRequest:
            _logger.exception('Unable to report data custom metrics '
                    'from data sampler %r. Data being discarded. If this '
                    'issue persists then please report this problem to '
                    'the data source provider or New Relic support for '
                    'further investigation.', self.name)

            self.metrics_table = None
            self.period_start = now

        except Exception:
            # An unexpected error, likely some sort of internal
            # agent implementation issue.

            _logger.exception('Unexpected exception when attempting '
                    'to harvest custom metrics and send it to the '
                    'data collector. Please report this problem to '
                    'New Relic support for further investigation.')

            self.metrics_table = None
            self.period_start = now

        else:
            self.period_start = now

_harvest_shutdown = threading.Event()

def run_standalone():
    """Means of running standalone process to consume data sources and
    post custom metrics collected.

    """

    _logger.info('New Relic Python Agent - Data Source (%s)', agent_version)

    data_samplers = []

    for (section, module, object_path, name, settings, properties,
            source) in _data_sources:

        try:
            data_sampler = DataSampler('New Relic (Platform)', source, name,
                    settings, **properties)

            if data_sampler.guid is None:
                _logger.warning('Skipping data source %s:%s as does not '
                        'have an associated data source guid.', module,
                        object_path)

                continue

            data_samplers.append(data_sampler)

        except Exception:
            _logger.exception('Attempt to register data source %s:%s with '
                    'name %r from section %r of agent configuration file '
                    'has failed. Data source will be skipped.', module,
                    object_path, name, section)

    if not data_samplers:
        _logger.warning('No valid data sources defined.')
        return

    _logger.debug('Starting data samplers.')

    for data_sampler in data_samplers:
        data_sampler.start()

    next_harvest = time.time()

    def _do_harvest():
        _logger.debug('Commencing data harvest.')

        for data_sampler in data_samplers:
            _logger.debug('Harvest data source %r with guid %r. Reporting '
                    'data to %r.', data_sampler.name, data_sampler.guid,
                    data_sampler.consumer)

            data_sampler.upload()

    try:
        _logger.debug('Starting main harvest loop.')

        while True:
            now = time.time()
            while next_harvest <= now:
                next_harvest += 60.0

            delay = next_harvest - now

            _harvest_shutdown.wait(delay)

            if _harvest_shutdown.isSet():
                _logger.info('New Relic Python Agent Shutdown')
                _do_harvest()
                return

            _do_harvest()

    except Exception:
        _logger.exception('Unexpected exception when attempting '
                'to harvest custom metrics and send it to the '
                'data collector. Please report this problem to '
                'New Relic support for further investigation.')

def run(config_file, background=False):
    read_configuration(config_file)

    if not background:
        if _log_file:
            try:
                os.unlink(_settings.log_file)
            except Exception:
                pass

        logging.basicConfig(filename=_log_file,
                level=_log_level, format=_LOG_FORMAT)

    register_data_sources()

    def shutdown_agent(*args):
        _harvest_shutdown.set()

    atexit.register(shutdown_agent)

    if background:
        thread = threading.Thread(target=run_standalone)
        thread.setDaemon()
        thread.start()

    else:
        signal.signal(signal.SIGINT, shutdown_agent)
        signal.signal(signal.SIGTERM, shutdown_agent)
        signal.signal(signal.SIGHUP, shutdown_agent)

        run_standalone()

def data_source_generator(name=None, **properties):
    def _decorator(func):
        @functools.wraps(func)
        def _properties(settings):
            def _factory(environ):
                return func
            d = dict(properties)
            d['name'] = name
            d['factory'] = _factory
            return d
        return _properties
    return _decorator

def data_source_factory(name=None, **properties):
    def _decorator(func):
        @functools.wraps(func)
        def _properties(settings):
            def _factory(environ):
                return func(settings, environ)
            d = dict(properties)
            d['name'] = name
            d['factory'] = _factory
            return d
        return _properties
    return _decorator
