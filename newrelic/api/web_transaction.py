import cgi
import time
import logging
import warnings

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

from newrelic.api.transaction import Transaction

from newrelic.common.encoding_utils import (obfuscate, deobfuscate,
        json_encode, json_decode, decode_newrelic_header, ensure_utf8)

from newrelic.core.attribute import (create_agent_attributes,
        create_attributes, process_user_attribute)
from newrelic.core.attribute_filter import DST_BROWSER_MONITORING, DST_NONE

from newrelic.packages import six

_logger = logging.getLogger(__name__)

_js_agent_header_fragment = '<script type="text/javascript">%s</script>'
_js_agent_footer_fragment = '<script type="text/javascript">'\
                            'window.NREUM||(NREUM={});NREUM.info=%s</script>'

# Seconds since epoch for Jan 1 2000
JAN_1_2000 = time.mktime((2000, 1, 1, 0, 0, 0, 0, 0, 0))


def _parse_time_stamp(time_stamp):
    """
    Converts time_stamp to seconds. Input can be microseconds,
    milliseconds or seconds

    Divide the timestamp by the highest resolution divisor. If
    the result is older than Jan 1 2000, then pick a lower
    resolution divisor and repeat.  It is safe to assume no
    requests were queued for more than 10 years.

    """

    now = time.time()

    for divisor in (1000000.0, 1000.0, 1.0):
        converted_time = time_stamp / divisor

        # If queue_start is in the future, return 0.0.

        if converted_time > now:
            return 0.0

        if converted_time > JAN_1_2000:
            return converted_time

    return 0.0


def _lookup_environ_setting(environ, name, default=False):
    flag = environ.get(name, default)
    if default is None or default:
        try:
            flag = not flag.lower() in ['off', 'false', '0']
        except AttributeError:
            pass
    else:
        try:
            flag = flag.lower() in ['on', 'true', '1']
        except AttributeError:
            pass
    return flag


def _parse_synthetics_header(header):
    # Return a dictionary of values from Synthetics header
    # Returns empty dict, if version is not supported.

    synthetics = {}
    version = None

    try:
        if len(header) > 0:
            version = int(header[0])

        if version == 1:
            synthetics['version'] = version
            synthetics['account_id'] = int(header[1])
            synthetics['resource_id'] = header[2]
            synthetics['job_id'] = header[3]
            synthetics['monitor_id'] = header[4]
    except Exception:
        return

    return synthetics


def _remove_query_string(url):
    out = urlparse.urlsplit(url)
    return urlparse.urlunsplit((out.scheme, out.netloc, out.path, '', ''))


def _is_websocket(environ):
    return environ.get('HTTP_UPGRADE', '').lower() == 'websocket'


class WSGIHeaderProxy(Mapping):
    def __init__(self, environ):
        self.environ = environ
        self.length = None

    @staticmethod
    def _to_wsgi(key):
        key = key.upper()
        if key == 'CONTENT-LENGTH':
            return 'CONTENT_LENGTH'
        elif key == 'CONTENT-TYPE':
            return 'CONTENT_TYPE'
        return 'HTTP_' + key.replace('-', '_')

    @staticmethod
    def _from_wsgi(key):
        return key[5:].replace('_', '-')

    def __getitem__(self, key):
        wsgi_key = self._to_wsgi(key)
        return self.environ[wsgi_key]

    def __iter__(self):
        for key in self.environ:
            if key == 'CONTENT_LENGTH':
                yield 'CONTENT-LENGTH'
            elif key == 'CONTENT_TYPE':
                yield 'CONTENT-TYPE'
            elif key == 'HTTP_CONTENT_LENGTH' or key == 'HTTP_CONTENT_TYPE':
                # These keys are illegal and should be ignored
                continue
            elif key.startswith('HTTP_'):
                yield self._from_wsgi(key)

    def __len__(self):
        if self.length is None:
            self.length = sum(1 for _ in iter(self))
        return self.length


class WSGIWebTransaction(Transaction):

    report_unicode_error = True

    def __init__(self, application, environ):

        # The web transaction can be enabled/disabled by
        # the value of the variable "newrelic.enabled"
        # in the WSGI environ dictionary. We need to check
        # this before initialising the transaction as needs
        # to be passed in base class constructor. The
        # default is None, which would then result in the
        # base class making the decision based on whether
        # application or agent as a whole are enabled.

        enabled = _lookup_environ_setting(environ,
                'newrelic.enabled', None)

        # Initialise the common transaction base class.

        super(WSGIWebTransaction, self).__init__(application, enabled)

        # Disable transactions for websocket connections.
        # Also disable autorum if this is a websocket. This is a good idea for
        # two reasons. First, RUM is unnecessary for websocket transactions
        # anyway. Secondly, due to a bug in the gevent-websocket (0.9.5)
        # package, if our _WSGIApplicationMiddleware is applied a websocket
        # connection cannot be made.

        if _is_websocket(environ):
            self.autorum_disabled = True
            self.enabled = False

        # Bail out if the transaction is running in a
        # disabled state.

        if not self.enabled:
            return

        # Will need to check the settings a number of times.

        settings = self._settings

        # Check for override settings from WSGI environ.

        self.background_task = _lookup_environ_setting(environ,
                'newrelic.set_background_task', False)

        self.ignore_transaction = _lookup_environ_setting(environ,
                'newrelic.ignore_transaction', False)
        self.suppress_apdex = _lookup_environ_setting(environ,
                'newrelic.suppress_apdex_metric', False)
        self.suppress_transaction_trace = _lookup_environ_setting(environ,
                'newrelic.suppress_transaction_trace', False)
        self.capture_params = _lookup_environ_setting(environ,
                'newrelic.capture_request_params',
                settings.capture_params)
        self.autorum_disabled = _lookup_environ_setting(environ,
                'newrelic.disable_browser_autorum',
                not settings.browser_monitoring.auto_instrument)

        # Make sure that if high security mode is enabled that
        # capture of request params is still being disabled.
        # No warning is issued for this in the logs because it
        # is a per request configuration and would create a lot
        # of noise.

        if settings.high_security:
            self.capture_params = False

        # WSGI spec says SERVER_PORT "can never be empty string",
        # but I'm going to set a default value anyway...

        port = environ.get('SERVER_PORT', None)
        if port:
            try:
                self._port = int(port)
            except Exception:
                pass

        # Extract from the WSGI environ dictionary
        # details of the URL path. This will be set as
        # default path for the web transaction. This can
        # be overridden by framework to be more specific
        # to avoid metrics explosion problem resulting
        # from too many distinct URLs for same resource
        # due to use of REST style URL concepts or
        # otherwise.

        request_uri = environ.get('REQUEST_URI', None)

        if request_uri is None:
            # The gunicorn WSGI server uses RAW_URI instead
            # of the more typical REQUEST_URI used by Apache
            # and other web servers.

            request_uri = environ.get('RAW_URI', None)

        script_name = environ.get('SCRIPT_NAME', None)
        path_info = environ.get('PATH_INFO', None)

        self._request_uri = request_uri

        if self._request_uri is not None:
            # Need to make sure we drop off any query string
            # arguments on the path if we have to fallback
            # to using the original REQUEST_URI. Can't use
            # attribute access on result as only support for
            # Python 2.5+.

            self._request_uri = urlparse.urlparse(self._request_uri)[2]

        if script_name is not None or path_info is not None:
            if path_info is None:
                path = script_name
            elif script_name is None:
                path = path_info
            else:
                path = script_name + path_info

            self.set_transaction_name(path, 'Uri', priority=1)

            if self._request_uri is None:
                self._request_uri = path
        else:
            if self._request_uri is not None:
                self.set_transaction_name(self._request_uri, 'Uri', priority=1)

        # See if the WSGI environ dictionary includes the
        # special 'X-Request-Start' or 'X-Queue-Start' HTTP
        # headers. These header are optional headers that can be
        # set within the underlying web server or WSGI server to
        # indicate when the current request was first received
        # and ready to be processed. The difference between this
        # time and when application starts processing the
        # request is the queue time and represents how long
        # spent in any explicit request queuing system, or how
        # long waiting in connecting state against listener
        # sockets where request needs to be proxied between any
        # processes within the application server.
        #
        # Note that mod_wsgi sets its own distinct variables
        # automatically. Initially it set mod_wsgi.queue_start,
        # which equated to when Apache first accepted the
        # request. This got changed to mod_wsgi.request_start
        # however, and mod_wsgi.queue_start was instead used
        # just for when requests are to be queued up for the
        # daemon process and corresponded to the point at which
        # they are being proxied, after Apache does any
        # authentication etc. We check for both so older
        # versions of mod_wsgi will still work, although we
        # don't try and use the fact that it is possible to
        # distinguish the two points and just pick up the
        # earlier of the two.
        #
        # Checking for the mod_wsgi values means it is not
        # necessary to enable and use mod_headers to add X
        # -Request-Start or X-Queue-Start. But we still check
        # for the headers and give priority to the explicitly
        # added header in case that header was added in front
        # end server to Apache instead.
        #
        # Which ever header is used, we accommodate the value
        # being in seconds, milliseconds or microseconds. Also
        # handle it being prefixed with 't='.

        queue_time_headers = ('HTTP_X_REQUEST_START', 'HTTP_X_QUEUE_START',
                'mod_wsgi.request_start', 'mod_wsgi.queue_start')

        for queue_time_header in queue_time_headers:
            value = environ.get(queue_time_header, None)

            try:
                if value.startswith('t='):
                    try:
                        self.queue_start = _parse_time_stamp(float(value[2:]))
                    except Exception:
                        pass
                else:
                    try:
                        self.queue_start = _parse_time_stamp(float(value))
                    except Exception:
                        pass

            except Exception:
                pass

            if self.queue_start > 0.0:
                break

        # Capture query request string parameters, unless we're in
        # High Security Mode.

        if not settings.high_security:

            value = environ.get('QUERY_STRING', None)

            if value:
                try:
                    params = urlparse.parse_qs(value, keep_blank_values=True)
                except Exception:
                    params = cgi.parse_qs(value, keep_blank_values=True)

                self._request_params.update(params)

        # Check for Synthetics header

        if settings.synthetics.enabled and \
                settings.trusted_account_ids and settings.encoding_key:

            try:
                header_name = 'HTTP_X_NEWRELIC_SYNTHETICS'
                header = self.decode_newrelic_header(environ, header_name)
                synthetics = _parse_synthetics_header(header)

                if synthetics['account_id'] in settings.trusted_account_ids:

                    # Save obfuscated header, because we will pass it along
                    # unchanged in all external requests.

                    self.synthetics_header = environ.get(header_name)

                    if synthetics['version'] == 1:
                        self.synthetics_resource_id = synthetics['resource_id']
                        self.synthetics_job_id = synthetics['job_id']
                        self.synthetics_monitor_id = synthetics['monitor_id']

            except Exception:
                pass

        # Process the New Relic cross process ID header and extract
        # the relevant details.

        if settings.distributed_tracing.enabled:
            distributed_header = environ.get('HTTP_NEWRELIC', None)
            if distributed_header is not None:
                self.accept_distributed_trace_payload(distributed_header)
        else:
            client_cross_process_id = environ.get('HTTP_X_NEWRELIC_ID')
            txn_header = environ.get('HTTP_X_NEWRELIC_TRANSACTION')
            self._process_incoming_cat_headers(client_cross_process_id,
                    txn_header)

        # Capture WSGI request environ dictionary values. We capture
        # content length explicitly as will need it for cross process
        # metrics.

        self._read_length = int(environ.get('CONTENT_LENGTH') or -1)

        if settings.capture_environ:
            for name in settings.include_environ:
                if name in environ:
                    self._request_environment[name] = environ[name]

        # Strip query params from referer URL.
        if 'HTTP_REFERER' in self._request_environment:
            self._request_environment['HTTP_REFERER'] = _remove_query_string(
                    self._request_environment['HTTP_REFERER'])

        try:
            if 'CONTENT_LENGTH' in self._request_environment:
                self._request_environment['CONTENT_LENGTH'] = int(
                        self._request_environment['CONTENT_LENGTH'])
        except Exception:
            del self._request_environment['CONTENT_LENGTH']

        # Flags for tracking whether RUM header and footer have been
        # generated.

        self.rum_header_generated = False
        self.rum_footer_generated = False

    def decode_newrelic_header(self, environ, header_name):
        encoded_header = environ.get(header_name)
        if encoded_header:
            try:
                decoded_header = json_decode(deobfuscate(
                        encoded_header, self._settings.encoding_key))
            except Exception:
                decoded_header = None

        return decoded_header

    def process_response(self, status, response_headers, *args):
        """Processes response status and headers, extracting any
        details required and returning a set of additional headers
        to merge into that being returned for the web transaction.

        """

        # Set our internal response code based on WSGI status.
        # Per spec, it is expected that this is a string. If this is not
        # the case, skip setting the internal response code as we cannot
        # make the determination. (An integer 200 for example when passed
        # would raise as a 500 for WSGI applications).

        try:
            self.response_code = int(status.split(' ')[0])
        except Exception:
            pass

        # Extract response content length and type for inclusion in agent
        # attributes

        try:

            for header, value in response_headers:
                lower_header = header.lower()
                if 'content-length' == lower_header:
                    self._response_properties['CONTENT_LENGTH'] = int(value)
                elif 'content-type' == lower_header:
                    self._response_properties['CONTENT_TYPE'] = value

        except Exception:
            pass

        # If response code is 304 do not insert CAT headers.
        # See https://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.3.5
        if self.response_code == 304:
            return []

        # Generate CAT response headers
        return self._generate_response_headers()

    def browser_timing_header(self):
        """Returns the JavaScript header to be included in any HTML
        response to perform real user monitoring. This function returns
        the header as a native Python string. In Python 2 native strings
        are stored as bytes. In Python 3 native strings are stored as
        unicode.

        """

        if not self.enabled:
            return ''

        if self._state != self.STATE_RUNNING:
            return ''

        if self.background_task:
            return ''

        if self.ignore_transaction:
            return ''

        if not self._settings:
            return ''

        if not self._settings.browser_monitoring.enabled:
            return ''

        if not self._settings.license_key:
            return ''

        # Don't return the header a second time if it has already
        # been generated.

        if self.rum_header_generated:
            return ''

        # Requirement is that the first 13 characters of the account
        # license key is used as the key when obfuscating values for
        # the RUM footer. Will not be able to perform the obfuscation
        # if license key isn't that long for some reason.

        if len(self._settings.license_key) < 13:
            return ''

        # Return the RUM header only if the agent received a valid value
        # for js_agent_loader from the data collector. The data
        # collector is not meant to send a non empty value for the
        # js_agent_loader value if browser_monitoring.loader is set to
        # 'none'.

        if self._settings.js_agent_loader:
            header = _js_agent_header_fragment % self._settings.js_agent_loader

            # To avoid any issues with browser encodings, we will make sure
            # that the javascript we inject for the browser agent is ASCII
            # encodable. Since we obfuscate all agent and user attributes, and
            # the transaction name with base 64 encoding, this will preserve
            # those strings, if they have values outside of the ASCII character
            # set. In the case of Python 2, we actually then use the encoded
            # value as we need a native string, which for Python 2 is a byte
            # string. If encoding as ASCII fails we will return an empty
            # string.

            try:
                if six.PY2:
                    header = header.encode('ascii')
                else:
                    header.encode('ascii')

            except UnicodeError:
                if not WSGIWebTransaction.unicode_error_reported:
                    _logger.error('ASCII encoding of js-agent-header failed.',
                            header)
                    WSGIWebTransaction.unicode_error_reported = True

                header = ''

        else:
            header = ''

        # We remember if we have returned a non empty string value and
        # if called a second time we will not return it again. The flag
        # will also be used to check whether the footer should be
        # generated.

        if header:
            self.rum_header_generated = True

        return header

    def browser_timing_footer(self):
        """Returns the JavaScript footer to be included in any HTML
        response to perform real user monitoring. This function returns
        the footer as a native Python string. In Python 2 native strings
        are stored as bytes. In Python 3 native strings are stored as
        unicode.

        """

        if not self.enabled:
            return ''

        if self._state != self.STATE_RUNNING:
            return ''

        if self.ignore_transaction:
            return ''

        # Only generate a footer if the header had already been
        # generated and we haven't already generated the footer.

        if not self.rum_header_generated:
            return ''

        if self.rum_footer_generated:
            return ''

        # Make sure we freeze the path.

        self._freeze_path()

        # When obfuscating values for the footer, we only use the
        # first 13 characters of the account license key.

        obfuscation_key = self._settings.license_key[:13]

        intrinsics = self.browser_monitoring_intrinsics(obfuscation_key)

        attributes = {}

        user_attributes = {}
        for attr in self.user_attributes:
            if attr.destinations & DST_BROWSER_MONITORING:
                user_attributes[attr.name] = attr.value

        if user_attributes:
            attributes['u'] = user_attributes

        agent_attributes = {}
        for attr in self.request_parameters_attributes:
            if attr.destinations & DST_BROWSER_MONITORING:
                agent_attributes[attr.name] = attr.value

        if agent_attributes:
            attributes['a'] = agent_attributes

        # create the data structure that pull all our data in

        footer_data = intrinsics

        if attributes:
            attributes = obfuscate(json_encode(attributes), obfuscation_key)
            footer_data['atts'] = attributes

        footer = _js_agent_footer_fragment % json_encode(footer_data)

        # To avoid any issues with browser encodings, we will make sure that
        # the javascript we inject for the browser agent is ASCII encodable.
        # Since we obfuscate all agent and user attributes, and the transaction
        # name with base 64 encoding, this will preserve those strings, if
        # they have values outside of the ASCII character set.
        # In the case of Python 2, we actually then use the encoded value
        # as we need a native string, which for Python 2 is a byte string.
        # If encoding as ASCII fails we will return an empty string.

        try:
            if six.PY2:
                footer = footer.encode('ascii')
            else:
                footer.encode('ascii')

        except UnicodeError:
            if not WSGIWebTransaction.unicode_error_reported:
                _logger.error('ASCII encoding of js-agent-footer failed.',
                        footer)
                WSGIWebTransaction.unicode_error_reported = True

            footer = ''

        # We remember if we have returned a non empty string value and
        # if called a second time we will not return it again.

        if footer:
            self.rum_footer_generated = True

        return footer

    def browser_monitoring_intrinsics(self, obfuscation_key):
        txn_name = obfuscate(self.path, obfuscation_key)

        queue_start = self.queue_start or self.start_time
        start_time = self.start_time
        end_time = time.time()

        queue_duration = int((start_time - queue_start) * 1000)
        request_duration = int((end_time - start_time) * 1000)

        intrinsics = {
            "beacon": self._settings.beacon,
            "errorBeacon": self._settings.error_beacon,
            "licenseKey": self._settings.browser_key,
            "applicationID": self._settings.application_id,
            "transactionName": txn_name,
            "queueTime": queue_duration,
            "applicationTime": request_duration,
            "agent": self._settings.js_agent_file,
        }

        if self._settings.browser_monitoring.ssl_for_http is not None:
            ssl_for_http = self._settings.browser_monitoring.ssl_for_http
            intrinsics['sslForHttp'] = ssl_for_http

        return intrinsics


class WebTransaction(WSGIWebTransaction):
    def __init__(self, application, environ):
        super(WebTransaction, self).__init__(application, environ)
        warnings.warn((
            'The WebTransaction API call has been deprecated.'
        ), DeprecationWarning)


class BaseWebTransaction(Transaction):
    QUEUE_TIME_HEADERS = ('x-request-start', 'x-queue-start')

    def __init__(self, application, name, group=None,
            scheme=None, host=None, port=None, request_method=None,
            request_path=None, query_string=None, headers=None,
            enabled=None):

        super(BaseWebTransaction, self).__init__(application, enabled)

        if not self.enabled:
            return

        # Inputs
        self._request_uri = request_path
        self._request_method = request_method
        self._request_scheme = scheme
        self._request_host = host
        self._request_params = {}
        self._request_headers = {}

        try:
            self._port = int(port)
        except Exception:
            self._port = None

        # Queue Time
        self.queue_start = 0.0

        # Synthetics
        self.synthetics_header = None
        self.synthetics_resource_id = None
        self.synthetics_job_id = None
        self.synthetics_monitor_id = None

        # Response
        self._response_headers = {}
        self._response_code = None

        if headers:
            if isinstance(headers, Mapping):
                headers = headers.items()

            for k, v in headers:
                k = ensure_utf8(k)
                if k is not None:
                    self._request_headers[k.lower()] = v

        # Capture query request string parameters, unless we're in
        # High Security Mode.
        if query_string and not self._settings.high_security:
            query_string = ensure_utf8(query_string)
            try:
                params = urlparse.parse_qs(
                        query_string,
                        keep_blank_values=True)
                self._request_params.update(params)
            except Exception:
                pass

        self._process_queue_time()
        self._process_synthetics_header()
        self._process_context_headers()

        if name is not None:
            self.set_transaction_name(name, group, priority=1)
        elif request_path is not None:
            self.set_transaction_name(request_path, 'Uri', priority=1)

    def _process_queue_time(self):
        for queue_time_header in self.QUEUE_TIME_HEADERS:
            value = self._request_headers.get(queue_time_header)
            value = ensure_utf8(value)

            try:
                if value.startswith('t='):
                    self.queue_start = _parse_time_stamp(float(value[2:]))
                else:
                    self.queue_start = _parse_time_stamp(float(value))
            except Exception:
                pass

            if self.queue_start > 0.0:
                break

    def _process_synthetics_header(self):
        # Check for Synthetics header

        if self._settings.synthetics.enabled and \
                self._settings.trusted_account_ids and \
                self._settings.encoding_key:

            encoded_header = self._request_headers.get('x-newrelic-synthetics')
            decoded_header = decode_newrelic_header(
                    encoded_header,
                    self._settings.encoding_key)
            synthetics = _parse_synthetics_header(decoded_header)

            if synthetics and \
                    synthetics['account_id'] in \
                    self._settings.trusted_account_ids:

                # Save obfuscated header, because we will pass it along
                # unchanged in all external requests.

                self.synthetics_header = encoded_header
                self.synthetics_resource_id = synthetics['resource_id']
                self.synthetics_job_id = synthetics['job_id']
                self.synthetics_monitor_id = synthetics['monitor_id']

    def _process_context_headers(self):
        # Process the New Relic cross process ID header and extract
        # the relevant details.
        if self._settings.distributed_tracing.enabled:
            distributed_header = self._request_headers.get('newrelic')
            if distributed_header is not None:
                self.accept_distributed_trace_payload(distributed_header)
        else:
            client_cross_process_id = \
                    self._request_headers.get('x-newrelic-id')
            txn_header = self._request_headers.get('x-newrelic-transaction')
            self._process_incoming_cat_headers(client_cross_process_id,
                    txn_header)

    def process_response(self, status_code, response_headers):
        """Processes response status and headers, extracting any
        details required and returning a set of additional headers
        to merge into that being returned for the web transaction.

        """

        # Extract response headers
        if response_headers:
            if isinstance(response_headers, Mapping):
                response_headers = response_headers.items()

            for header, value in response_headers:
                header = ensure_utf8(header)
                if header is not None:
                    self._response_headers[header.lower()] = value

        try:
            status_code = int(status_code)
            self._response_code = status_code
        except Exception:
            status_code = None

        # If response code is 304 do not insert CAT headers.
        # See https://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.3.5
        if status_code == 304:
            return []

        # Generate CAT response headers
        try:
            read_length = int(self._request_headers.get('content-length'))
        except Exception:
            read_length = -1

        return self._generate_response_headers(read_length)

    @property
    def agent_attributes(self):
        a_attrs = self._agent_attributes
        settings = self._settings

        if 'accept' in self._request_headers:
            a_attrs['request.headers.accept'] = self._request_headers['accept']
        if 'content-length' in self._request_headers:
            a_attrs['request.headers.contentLength'] = \
                    self._request_headers['content-length']
        if 'content-type' in self._request_headers:
            a_attrs['request.headers.contentType'] = \
                    self._request_headers['content-type']
        if 'host' in self._request_headers:
            a_attrs['request.headers.host'] = self._request_headers['host']
        if 'referer' in self._request_headers:
            a_attrs['request.headers.referer'] = _remove_query_string(
                    self._request_headers['referer'])
        if 'user-agent' in self._request_headers:
            a_attrs['request.headers.userAgent'] = \
                    self._request_headers['user-agent']
        if self._request_method:
            a_attrs['request.method'] = self._request_method
        if self._request_uri:
            a_attrs['request.uri'] = self._request_uri

        if 'content-length' in self._response_headers:
            a_attrs['response.headers.contentLength'] = \
                    self._response_headers['content-length']
        if 'content-type' in self._response_headers:
            a_attrs['response.headers.contentType'] = \
                    self._response_headers['content-type']
        if self._response_code:
            a_attrs['response.status'] = str(self._response_code)

        if self.queue_wait != 0:
            a_attrs['webfrontend.queue.seconds'] = self.queue_wait

        # TODO: move these to the Transaction base class
        if settings.process_host.display_name:
            a_attrs['host.displayName'] = settings.process_host.display_name
        if self._thread_utilization_value:
            a_attrs['thread.concurrency'] = self._thread_utilization_value

        agent_attributes = create_agent_attributes(a_attrs,
                settings.attribute_filter)

        # Include request parameters in agent attributes
        agent_attributes.extend(self.request_parameters_attributes)

        return agent_attributes

    @property
    def request_parameters_attributes(self):
        # Request parameters are a special case of agent attributes, so they
        # must be added on to agent_attributes separately
        #
        # Filter request parameters through the AttributeFilter, but set the
        # destinations to NONE.
        #
        # That means by default, request parameters won't get included in any
        # destination. But, it will allow user added include/exclude attribute
        # filtering rules to be applied to the request parameters.

        attributes_request = []

        if self._request_params:

            r_attrs = {}

            for k, v in self._request_params.items():
                new_key = 'request.parameters.%s' % k
                new_val = ",".join(v)

                final_key, final_val = process_user_attribute(new_key, new_val)

                if final_key:
                    r_attrs[final_key] = final_val

            attributes_request = create_attributes(r_attrs, DST_NONE,
                    self._settings.attribute_filter)

        return attributes_request
