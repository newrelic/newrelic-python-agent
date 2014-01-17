import sys
import cgi
import time
import string
import re
import logging

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

import newrelic.api.application
import newrelic.api.transaction
import newrelic.api.object_wrapper
import newrelic.api.function_trace

from ..common.encoding_utils import (obfuscate, deobfuscate, json_encode,
    json_decode)

from ..packages import six

_logger = logging.getLogger(__name__)

_js_agent_header_fragment = '<script type="text/javascript">%s</script>'
_js_agent_footer_fragment = '<script type="text/javascript">'\
                            'window.NREUM||(NREUM={});NREUM.info=%s</script>'

# Seconds since epoch for Jan 1 2000

JAN_1_2000 = time.mktime((2000, 1, 1, 0, 0, 0, 0, 0, 0))

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

def _extract_token(cookie):
    try:
        t = re.search(r"\bNRAGENT=(tk=.{16})", cookie)
        token = re.search(r"^tk=([^\"<'>]+)$", t.group(1)) if t else None
        return token and token.group(1)
    except Exception:
        pass

class WebTransaction(newrelic.api.transaction.Transaction):

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

        newrelic.api.transaction.Transaction.__init__(self,
                application, enabled)

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

        # Extract from the WSGI environ dictionary
        # details of the URL path. This will be set as
        # default path for the web transaction. This can
        # be overridden by framework to be more specific
        # to avoid metrics explosion problem resulting
        # from too many distinct URLs for same resource
        # due to use of REST style URL concepts or
        # otherwise.

        request_uri = environ.get('REQUEST_URI', None)
        script_name = environ.get('SCRIPT_NAME', None)
        path_info = environ.get('PATH_INFO', None)
        http_cookie = environ.get('HTTP_COOKIE', None)

        if http_cookie and ("NRAGENT" in http_cookie):
            self.rum_token = _extract_token(http_cookie)
            self.rum_trace = True if self.rum_token else False

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
        # Which ever header is used, we accomodate the value
        # being in seconds, milliseconds or microseconds. Also
        # handle it being prefixed with 't='.

        now = time.time()

        def _parse_time_stamp(time_stamp):
            """
            Converts time_stamp to seconds. Input can be microseconds,
            milliseconds or seconds

            Divide the timestamp by the highest resolution divisor. If
            the result is older than Jan 1 2000, then pick a lower
            resolution divisor and repeat.  It is safe to assume no
            requests were queued for more than 10 years.

            """
            for divisor in (1000000.0, 1000.0, 1.0):
                converted_time = time_stamp/divisor

                # If queue_start is in the future, return 0.0.

                if converted_time > now:
                    return 0.0

                if converted_time > JAN_1_2000:
                    return converted_time

            return 0.0

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

        # Capture query request string parameters.

        value = environ.get('QUERY_STRING', None)

        if value:
            try:
                params = urlparse.parse_qs(value, keep_blank_values=True)
            except Exception:
                params = cgi.parse_qs(value, keep_blank_values=True)

            for name in settings.ignored_params:
                if name in params:
                    del params[name]

            self._request_params.update(params)

        # Check for the New Relic cross process ID header and extract
        # the relevant details.


        if settings.cross_application_tracer.enabled and \
                settings.cross_process_id and settings.trusted_account_ids and \
                settings.encoding_key:

            client_cross_process_id = environ.get('HTTP_X_NEWRELIC_ID')

            if client_cross_process_id:
                try:
                    client_cross_process_id = deobfuscate(
                            client_cross_process_id, settings.encoding_key)


                    # The cross process ID consists of the client
                    # account ID and the ID of the specific application
                    # the client is recording requests against. We need
                    # to validate that the client account ID is in the
                    # list of trusted account IDs and ignore it if it
                    # isn't. The trusted account IDs list has the
                    # account IDs as integers, so save the client ones
                    # away as integers here so easier to compare later.

                    client_account_id, client_application_id = \
                            map(int, client_cross_process_id.split('#'))

                    if client_account_id in settings.trusted_account_ids:
                        self.client_cross_process_id = client_cross_process_id
                        self.client_account_id = client_account_id
                        self.client_application_id = client_application_id

                        txn_header = self.process_txn_header(environ)
                        if txn_header:
                            self.referring_transaction_guid = txn_header[0]

                            # Incoming record_tt is OR'd with existing
                            # record_tt. In the sceanrio where we make multiple
                            # ext request, this will ensure we don't set the
                            # record_tt to False by a later request if it was
                            # set to True by an earlier request.

                            self.record_tt = self.record_tt or txn_header[1]

                except Exception:
                    pass

        # Capture WSGI request environ dictionary values. We capture
        # content length explicitly as will need it for cross process
        # metrics.

        self._read_length = int(environ.get('CONTENT_LENGTH') or -1)

        if settings.capture_environ:
            for name in settings.include_environ:
                if name in environ:
                    self._request_environment[name] = environ[name]

        # Flags for tracking whether RUM header inserted.

        self._rum_header = False

    def process_txn_header(self, environ):
        encoded_txn_header = environ.get('HTTP_X_NEWRELIC_TRANSACTION')

        if encoded_txn_header:
            try:
                decoded_txn_header = json_decode(deobfuscate(
                        encoded_txn_header, self._settings.encoding_key))
            except Exception:
                decoded_txn_header = None

        return decoded_txn_header

    def process_response(self, status, response_headers, *args):
        """Processes response status and headers, extracting any
        details required and returning a set of additional headers
        to merge into that being returned for the web transaction.

        """

        additional_headers = []

        # Extract the HTTP status response code.

        try:
            self.response_code = int(status.split(' ')[0])
        except Exception:
            pass

        # Extract response content length for inclusion in custom
        # parameters returned for slow transactions and errors.

        try:
            header = [x for x in response_headers
                    if x[0].lower() == 'content-length'][-1:]

            if header:
                self._response_properties['CONTENT_LENGTH'] = header[0][1]
        except Exception:
            pass

        # Generate metrics and response headers for inbound cross
        # process web external calls.

        if self.client_cross_process_id is not None:
            # Need to work out queueing time and duration up to this
            # point for inclusion in metrics and response header. If the
            # recording of the transaction had been prematurely stopped
            # via an API call, only return time up until that call was
            # made so it will match what is reported as duration for the
            # transaction.

            if self.queue_start:
                queue_time = self.start_time - self.queue_start
            else:
                queue_time = 0

            if self.end_time:
                duration = self.end_time = self.start_time
            else:
                duration = time.time() - self.start_time

            # Generate the metric identifying the caller.

            metric_name = 'ClientApplication/%s/all' % (
                    self.client_cross_process_id)
            self.record_custom_metric(metric_name, duration)

            # Generate the additional response headers which provide
            # information back to the caller. We need to freeze the
            # transaction name before adding to the header.

            self._freeze_path()

            payload = (self._settings.cross_process_id, self.path, queue_time,
                    duration, self._read_length, self.guid, self.record_tt)
            app_data = json_encode(payload)

            additional_headers.append(('X-NewRelic-App-Data', obfuscate(
                    app_data, self._settings.encoding_key)))

        # The additional headers returned need to be merged into the
        # original response headers passed back by the application.

        return additional_headers

    def browser_timing_header(self):
        """This function returns the header as a native python string.
           In Python 2 native strings are stored as bytes.
           In Python 3 native strings are stored as unicode.

         """
        if not self.enabled:
            return ''

        if self._state != newrelic.api.transaction.STATE_RUNNING:
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

        # Requirement is that the first 13 characters of the account
        # license key is used as the key when obfuscating values for
        # the RUM footer. Will not be able to perform the obfuscation
        # if license key isn't that long for some reason.

        if len(self._settings.license_key) < 13:
            return ''

        # Return header only if the agent received a valid js_agent_loader from
        # collector. Collector won't send any js_agent_loader if
        # browser_monitoring.loader is set to 'none'.
        #
        # JS Agent Loader is supposed to be ascii. Verify that by encoding it
        # as ascii. If encoding fails return an empty string.
        #
        # Set self._rum_header to true only if a valid header was returned.
        # This flag will be checked by the footer generation.

        if self._settings.js_agent_loader:
            header = _js_agent_header_fragment % self._settings.js_agent_loader
            try:
                header.encode('ascii')
            except UnicodeError:
                if not WebTransaction.unicode_error_reported:
                    _logger.error('ASCII encoding of js-agent-header failed.',
                            header)
                    WebTransaction.unicode_error_reported = True
                header = ''
            else:  # Successfully encoded.
                self._rum_header = True
        else:
            header = ''

        # Since encoding it as ascii was successful, return the string version
        # of header.

        return str(header)

    def browser_timing_footer(self):
        """This function returns the footer script as a native python string.
           In Python 2 native strings are stored as bytes.
           In Python 3 native strings are stored as unicode.

         """

        if not self.enabled:
            return ''

        if self._state != newrelic.api.transaction.STATE_RUNNING:
            return ''

        if self.ignore_transaction:
            return ''

        if not self._rum_header:
            return ''

        # Make sure we freeze the path.

        self._freeze_path()

        # When obfuscating values for the footer, we only use the
        # first 13 characters of the account license key.

        obfuscation_key = self._settings.license_key[:13]

        txn_name = obfuscate(self.path, obfuscation_key)

        queue_start = self.queue_start or self.start_time
        start_time = self.start_time
        end_time = time.time()

        queue_duration = int((start_time - queue_start) * 1000)
        request_duration = int((end_time - start_time) * 1000)

        config_dict = {
            "beacon": self._settings.beacon,
            "errorBeacon": self._settings.error_beacon,
            "licenseKey": self._settings.browser_key,
            "applicationID": self._settings.application_id,
            "transactionName": txn_name,
            "queueTime": queue_duration,
            "applicationTime": request_duration,
            "agent": self._settings.js_agent_file,
        }

        additional_params = []

        threshold = self._settings.transaction_tracer.transaction_threshold
        if threshold is None:
            threshold = self.apdex * 4

        if request_duration >= threshold:
            if self.rum_token:
                additional_params.append(('agentToken', self.rum_token))
                additional_params.append(('ttGuid', self.guid))

        if self._settings.browser_monitoring.capture_attributes:
            def _filter(params):
                for key, value in params.items():
                    if not isinstance(key, six.string_types):
                        continue
                    if (not isinstance(value, six.string_types) and
                            not isinstance(value, float) and
                            not isinstance(value, six.integer_types)):
                        continue
                    yield key, value

            user_attributes = dict(_filter(self._custom_params))

            if user_attributes:
                user_attributes = obfuscate(json_encode(user_attributes),
                        obfuscation_key)

                additional_params.append(('userAttributes', user_attributes))

        if self._settings.browser_monitoring.ssl_for_http is not None:
            additional_params.append(('sslForHttp',
                self._settings.browser_monitoring.ssl_for_http))

        # Add in the additional params to the footer config dictionary.

        config_dict.update(additional_params)
        footer = _js_agent_footer_fragment % json_encode(config_dict)

        # Footer dictionary is only supposed to have ascii chars. Verify that
        # by encoding it as ascii. If encoding fails return an empty string.

        try:
            footer.encode('ascii')
        except UnicodeError:
            if not WebTransaction.unicode_error_reported:
                _logger.error('ASCII encoding of js-agent-footer failed.',
                        footer)
                WebTransaction.unicode_error_reported = True
            return ''

        # Since encoding it as ascii was successful, return the string version
        # of footer.

        return str(footer)

class _WSGIApplicationIterable(object):

    def __init__(self, transaction, generator):
        self.transaction = transaction
        self.generator = generator

    def __iter__(self):
        if not self.transaction._sent_start:
            self.transaction._sent_start = time.time()
        try:
            with newrelic.api.function_trace.FunctionTrace(
                    self.transaction, name='Response', group='Python/WSGI'):
                for item in self.generator:
                    yield item
                    try:
                        self.transaction._calls_yield += 1
                        self.transaction._bytes_sent += len(item)
                    except Exception:
                        pass
        except GeneratorExit:
            raise
        except:  # Catch all
            self.transaction.record_exception(*sys.exc_info())
            raise

    def close(self):
        try:
            with newrelic.api.function_trace.FunctionTrace(
                    self.transaction, name='Finalize', group='Python/WSGI'):
                if hasattr(self.generator, 'close'):
                    name = newrelic.api.object_wrapper.callable_name(
                            self.generator.close)
                    with newrelic.api.function_trace.FunctionTrace(
                            self.transaction, name):
                        self.generator.close()

        except:  # Catch all
            self.transaction.__exit__(*sys.exc_info())
            raise
        else:
            self.transaction.__exit__(None, None, None)
            self.transaction._sent_end = time.time()

class WSGIInputWrapper(object):

    def __init__(self, transaction, input):
        self.__transaction = transaction
        self.__input = input

    def __getattr__(self, name):
        return getattr(self.__input, name)

    def close(self):
        if hasattr(self.__input, 'close'):
            self.__input.close()

    def read(self, *args, **kwargs):
        if not self.__transaction._read_start:
            self.__transaction._read_start = time.time()
        try:
            data = self.__input.read(*args, **kwargs)
            try:
                self.__transaction._calls_read += 1
                self.__transaction._bytes_read += len(data)
            except Exception:
                pass
        finally:
            self.__transaction._read_end = time.time()
        return data

    def readline(self, *args, **kwargs):
        if not self.__transaction._read_start:
            self.__transaction._read_start = time.time()
        try:
            line = self.__input.readline(*args, **kwargs)
            try:
                self.__transaction._calls_readline += 1
                self.__transaction._bytes_read += len(line)
            except Exception:
                pass
        finally:
            self.__transaction._read_end = time.time()
        return line

    def readlines(self, *args, **kwargs):
        if not self.__transaction._read_start:
            self.__transaction._read_start = time.time()
        try:
            lines = self.__input.readlines(*args, **kwargs)
            try:
                self.__transaction._calls_readlines += 1
                self.__transaction._bytes_read += sum(map(len, lines))
            except Exception:
                pass
        finally:
            self.__transaction._read_end = time.time()
        return lines

class WSGIApplicationWrapper(object):

    def __init__(self, wrapped, application=None, name=None, group=None,
               framework=None):
        if isinstance(wrapped, tuple):
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        self._nr_name = name
        self._nr_group = group

        if framework is None:
            self._nr_framework = None
        elif isinstance(framework, tuple):
            self._nr_framework = framework
        else:
            self._nr_framework = (framework, None)

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_application = application

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_application,
                self._nr_name, self._nr_group, self._nr_framework)

    def __call__(self, environ, start_response):
        transaction = newrelic.api.transaction.current_transaction()

        # Check to see if we are being called within the
        # context of any sort of transaction. If we are,
        # then we don't bother doing anything and just
        # call the wrapped function.

        if transaction:
            # Record details of framework against the transaction
            # for later reporting as supportability metrics.

            if self._nr_framework:
                transaction._frameworks.add(self._nr_framework)

            # Override the web transaction name to be the name of the
            # wrapped callable if not explicitly named, and we want the
            # default name to be that of the WSGI component for the
            # framework. This will override the use of a raw URL which
            # can result in metric grouping issues where a framework is
            # not instrumented or is leaking URLs.

            settings = transaction._settings

            if self._nr_name is None and settings:
                if self._nr_framework is not None:
                    naming_scheme = settings.transaction_name.naming_scheme
                    if naming_scheme in (None, 'framework'):
                        name = newrelic.api.object_wrapper.callable_name(
                                self._nr_next_object)
                        transaction.set_transaction_name(name, priority=1)

            elif self._nr_name:
                transaction.set_transaction_name(self._nr_name,
                        self._nr_group, priority=1)

            return self._nr_next_object(environ, start_response)

        # Otherwise treat it as top level transaction.
        # We have to though look first to see whether the
        # application name has been overridden through
        # the WSGI environ dictionary.

        app_name = environ.get('newrelic.app_name')

        if app_name:
            if app_name.find(';') != -1:
                app_names = [string.strip(n) for n in app_name.split(';')]
                app_name = app_names[0]
                application = newrelic.api.application.application_instance(
                        app_name)
                for altname in app_names[1:]:
                    application.link_to_application(altname)
            else:
                application = newrelic.api.application.application_instance(
                        app_name)
        else:
            application = self._nr_application

            # If application has an activate() method we assume it is an
            # actual application. Do this rather than check type so that
            # can easily mock it for testing.

            # FIXME Should this allow for multiple apps if a string.

            if not hasattr(application, 'activate'):
                application = newrelic.api.application.application_instance(
                        application)

        # Now start recording the actual web transaction.

        transaction = WebTransaction(application, environ)
        transaction.__enter__()

        # Record details of framework against the transaction
        # for later reporting as supportability metrics.

        if self._nr_framework:
            transaction._frameworks.add(self._nr_framework)

        # Override the initial web transaction name to be the supplied
        # name, or the name of the wrapped callable if wanting to use
        # the callable as the default. This will override the use of a
        # raw URL which can result in metric grouping issues where a
        # framework is not instrumented or is leaking URLs.
        #
        # Note that at present if default for naming scheme is still
        # None and we aren't specifically wrapping a designated
        # framework, then we still allow old URL based naming to
        # override. When we switch to always forcing a name we need to
        # check for naming scheme being None here.

        settings = transaction._settings

        if self._nr_name is None and settings:
            naming_scheme = settings.transaction_name.naming_scheme

            if self._nr_framework is not None:
                if naming_scheme in (None, 'framework'):
                    name = newrelic.api.object_wrapper.callable_name(
                            self._nr_next_object)
                    transaction.set_transaction_name(name, priority=1)

            elif naming_scheme in ('component', 'framework'):
                name = newrelic.api.object_wrapper.callable_name(
                        self._nr_next_object)
                transaction.set_transaction_name(name, priority=1)

        elif self._nr_name:
            transaction.set_transaction_name(self._nr_name, self._nr_group,
                  priority=1)

        def _start_response(status, response_headers, *args):

            additional_headers = transaction.process_response(
                    status, response_headers, *args)

            _write = start_response(status,
                    response_headers+additional_headers, *args)

            def write(data):
                if not transaction._sent_start:
                    transaction._sent_start = time.time()
                result = _write(data)
                transaction._calls_write += 1
                try:
                    transaction._bytes_sent += len(data)
                except Exception:
                    pass
                transaction._sent_end = time.time()
                return result

            return write

        try:
            # Should always exist, but check as test harnesses may not
            # have it.

            if 'wsgi.input' in environ:
                environ['wsgi.input'] = WSGIInputWrapper(transaction,
                        environ['wsgi.input'])

            application = newrelic.api.function_trace.FunctionTraceWrapper(
                    self._nr_next_object)

            with newrelic.api.function_trace.FunctionTrace(
                    transaction, name='Application', group='Python/WSGI'):
                result = application(environ, _start_response)
        except:  # Catch all
            transaction.__exit__(*sys.exc_info())
            raise

        return _WSGIApplicationIterable(transaction, result)

def wsgi_application(application=None, name=None, group=None, framework=None):
    def decorator(wrapped):
        return WSGIApplicationWrapper(wrapped, application, name, group,
            framework)
    return decorator

def wrap_wsgi_application(module, object_path, application=None,
            name=None, group=None, framework=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            WSGIApplicationWrapper, (application, name, group, framework))
