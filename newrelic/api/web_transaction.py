from __future__ import with_statement

import sys
import types
import urlparse
import cgi
import base64
import time
import string
import random
import re

import newrelic.api.application
import newrelic.api.transaction
import newrelic.api.object_wrapper
import newrelic.api.function_trace

_rum_header_fragment = '<script type="text/javascript">' \
        'var NREUMQ=NREUMQ||[];NREUMQ.push(["mark","firstbyte",' \
        'new Date().getTime()]);</script>'

_rum_footer_short_fragment = '<script type="text/javascript">' \
        'if(!NREUMQ.f){NREUMQ.f=function(){NREUMQ.push(["load",' \
        'new Date().getTime()]);if(NREUMQ.a)NREUMQ.a();};' \
        'NREUMQ.a=window.onload;window.onload=NREUMQ.f;};' \
        'NREUMQ.push(["nrf2","%s","%s","%s","%s",%d,%d,' \
        'new Date().getTime()]);</script>'

_rum2_footer_short_fragment = '<script type="text/javascript">' \
        'if(!NREUMQ.f){NREUMQ.f=function(){NREUMQ.push(["load",' \
        'new Date().getTime()]);if(NREUMQ.a)NREUMQ.a();};' \
        'NREUMQ.a=window.onload;window.onload=NREUMQ.f;};' \
        'NREUMQ.push(["nrfj","%s","%s","%s","%s",%d,%d,' \
        'new Date().getTime(),"%s","%s","%s","%s","%s"]);</script>'

_rum_footer_long_fragment = '<script type="text/javascript">' \
        'if(!NREUMQ.f){NREUMQ.f=function(){NREUMQ.push(["load",' \
        'new Date().getTime()]);var e=document.createElement("script");' \
        'e.type="text/javascript";' \
        'e.src=(("http:"===document.location.protocol)?"http:":"https:")' \
        '+"//"+"%s";document.body.appendChild(e);if(NREUMQ.a)NREUMQ.a();};' \
        'NREUMQ.a=window.onload;window.onload=NREUMQ.f;};' \
        'NREUMQ.push(["nrf2","%s","%s","%s","%s",%d,%d,' \
        'new Date().getTime()]);</script>'

_rum2_footer_long_fragment = '<script type="text/javascript">' \
        'if(!NREUMQ.f){NREUMQ.f=function(){NREUMQ.push(["load",' \
        'new Date().getTime()]);var e=document.createElement("script");' \
        'e.type="text/javascript";' \
        'e.src=(("http:"===document.location.protocol)?"http:":"https:")' \
        '+"//"+"%s";document.body.appendChild(e);if(NREUMQ.a)NREUMQ.a();};' \
        'NREUMQ.a=window.onload;window.onload=NREUMQ.f;};' \
        'NREUMQ.push(["nrfj","%s","%s","%s","%s",%d,%d,' \
        'new Date().getTime(),"%s","%s","%s","%s","%s"]);</script>'

def _obfuscate(name, key):
    if name is None:
        return ''
    s = []
    for i in range(len(name)):
        s.append(chr(ord(name[i]) ^ ord(key[i % 13])))
    return base64.b64encode(''.join(s))

def _lookup_environ_setting(environ, name, default=False):
    flag = environ.get(name, default)
    if default is None or default:
        if isinstance(flag, basestring):
            flag = not flag.lower() in ['off', 'false', '0']
    else:
        if isinstance(flag, basestring):
            flag = flag.lower() in ['on', 'true', '1']
    return flag

def _extract_token(cookie):
    try:
        t = re.search(r"\bNRAGENT=(tk=.{16})", cookie)
        token = re.search(r"^tk=([^\"<'>]+)$", t.group(1)) if t else None
        return token and token.group(1)
    except:
        pass


class WebTransaction(newrelic.api.transaction.Transaction):

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
                self._settings.capture_params)
        self.autorum_disabled = _lookup_environ_setting(environ,
                'newrelic.disable_browser_autorum',
                not self._settings.browser_monitoring.auto_instrument)

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
            self.rum_guid = self.rum_token and str(random.getrandbits(64))

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

            self.name_transaction(path, 'Uri', priority=1)

            if self._request_uri is None:
                self._request_uri = path
        else:
            if self._request_uri is not None:
                self.name_transaction(self._request_uri, 'Uri', priority=1)

        # See if the WSGI environ dictionary includes
        # the special 'X-Queue-Start' HTTP header. This
        # header is an optional header that can be set
        # within the underlying web server or WSGI
        # server to indicate when the current request
        # was first received and ready to be processed.
        # The difference between this time and when
        # application starts processing the request is
        # the queue time and represents how long spent
        # in any explicit request queuing system, or how
        # long waiting in connecting state against
        # listener sockets where request needs to be
        # proxied between any processes within the
        # application server.
        #
        # Note that Heroku they set their own header
        # called HTTP_X_HEROKU_QUEUE_WAIT_TIME but it is
        # defined in milliseconds rather that
        # microseconds.
        #
        # Note that mod_wsgi 4.0 sets its own distinct
        # variable called mod_wsgi.queue_start so that
        # not necessary to enable and use mod_headers to
        # add X-Queue-Start. So also check for that, but
        # give priority to the explicitly added header
        # in case that header was added in front end
        # server to Apache instead although for that
        # case they should be using X-Request-Start
        # which do not support here yet as PHP agent
        # core doesn't have a way of tracking front end
        # web server time.

        value = environ.get('HTTP_X_QUEUE_START', None)

        if value and isinstance(value, basestring):
            if value.startswith('t='):
                try:
                    self.queue_start = int(value[2:]) / 1000000.0
                except:
                    pass

        if self.queue_start == 0.0:
            value = environ.get('HTTP_X_HEROKU_QUEUE_WAIT_TIME', None)

            if value and isinstance(value, basestring):
                try:
                    self.queue_start = time.time()
                    self.queue_start -= int(value) / 1000.0
                except:
                    pass

        if self.queue_start == 0.0:
            value = environ.get('mod_wsgi.queue_start', None)

            if value and isinstance(value, basestring):
                try:
                    self.queue_start = int(value) / 1000000.0
                except:
                    pass

        # Capture query request string parameters.

        value = environ.get('QUERY_STRING', None)

        if value:
            try:
                params = urlparse.parse_qs(value)
            except:
                params = cgi.parse_qs(value)

            for name in self._settings.ignored_params:
                if name in params:
                    del params[name]

            self._request_params.update(params)

        # Capture WSGI request environ dictionary values.

        if self._settings.capture_environ:
            for name in self._settings.include_environ:
                if name in environ:
                    self._request_environment[name] = environ[name]

        # Flags for tracking whether RUM header inserted.

        self._rum_header = False

    def browser_timing_header(self):
        if not self.enabled:
            return ''

        if self._state != newrelic.api.transaction.STATE_RUNNING:
            return ''

        if self.background_task:
            return ''

        if not self._settings.rum.enabled:
            return ''

        if self.ignore_transaction:
            return ''

        if not self._settings:
            return ''

        if not self._settings.episodes_url:
            return ''

        if not self._settings.license_key:
            return ''

        if len(self._settings.license_key) < 13:
            return ''

        self._rum_header = True

        return _rum_header_fragment

    def browser_timing_footer(self):
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

        name = _obfuscate(self.path, self._settings.license_key)

        queue_start = self.queue_start or self.start_time
        start_time = self.start_time
        end_time = time.time()

        queue_duration = int((start_time - queue_start) * 1000)
        request_duration = int((end_time - start_time) * 1000)

        rum_token = self.rum_token or ''
        rum_guid = self.rum_guid or ''

        threshold = self._settings.transaction_tracer.transaction_threshold
        if threshold is None:
            threshold = self.apdex *4

        rum_guid = rum_guid if request_duration >= threshold else ''

        user = _obfuscate(self._user_attrs.get('user'),
                self._settings.license_key)
        account = _obfuscate(self._user_attrs.get('account'),
                self._settings.license_key)
        product = _obfuscate(self._user_attrs.get('product'),
                self._settings.license_key)

        # Settings will have values as Unicode strings and the
        # result here will be Unicode so need to convert back to
        # normal string. Using str() and default encoding should
        # be fine as should all be ASCII anyway.

        if not self._settings.rum.load_episodes_file:
            if self._settings.rum.jsonp:
                return str(_rum2_footer_short_fragment % (
                    self._settings.beacon,
                    self._settings.browser_key,
                    self._settings.application_id,
                    name, queue_duration, request_duration, rum_guid,
                    rum_token, user, account, product))
            else:
                return str(_rum_footer_short_fragment % (
                    self._settings.beacon,
                    self._settings.browser_key,
                    self._settings.application_id,
                    name, queue_duration, request_duration))
        else:
            if self._settings.rum.jsonp:
                return str(_rum2_footer_long_fragment % (
                    self._settings.episodes_file,
                    self._settings.beacon,
                    self._settings.browser_key,
                    self._settings.application_id,
                    name, queue_duration, request_duration, rum_guid,
                    rum_token, user, account, product))
            else:
                return str(_rum_footer_long_fragment % (
                    self._settings.episodes_file,
                    self._settings.beacon,
                    self._settings.browser_key,
                    self._settings.application_id,
                    name, queue_duration, request_duration))

class _WSGIApplicationIterable(object):

    def __init__(self, transaction, generator):
        self.transaction = transaction
        self.generator = generator

    def __iter__(self):
        if not self.transaction._sent_start:
            self.transaction._sent_start = time.time()
        with newrelic.api.function_trace.FunctionTrace(
                self.transaction, name='Response', group='Python/WSGI'):
            for item in self.generator:
                yield item
                try:
                    self.transaction._calls_yield += 1
                    self.transaction._bytes_sent += len(item)
                except:
                    pass

    def close(self):
        try:
            if hasattr(self.generator, 'close'):
                self.generator.close()
        except:
            self.transaction.__exit__(*sys.exc_info())
            raise
        else:
            self.transaction.__exit__(None, None, None)
            self.transaction._sent_end = time.time()

class WSGIInputWrapper(object):

    def __init__(self, transaction, input):
        self.__transaction = transaction
        self.__input = input

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
            except:
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
            except:
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
            except:
                pass
        finally:
            self.__transaction._read_end = time.time()
        return lines

class WSGIApplicationWrapper(object):

    def __init__(self, wrapped, application=None):
        if type(wrapped) == types.TupleType:
            (instance, wrapped) = wrapped
        else:
            instance = None

        newrelic.api.object_wrapper.update_wrapper(self, wrapped)

        self._nr_instance = instance
        self._nr_next_object = wrapped

        if not hasattr(self, '_nr_last_object'):
            self._nr_last_object = wrapped

        self._nr_application = application

    def __get__(self, instance, klass):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, klass)
        return self.__class__((instance, descriptor), self._nr_application)

    def __call__(self, environ, start_response):
        transaction = newrelic.api.transaction.current_transaction()

        # Check to see if we are being called within the
        # context of any sort of transaction. If we are,
        # then we don't bother doing anything and just
        # call the wrapped function.

        if transaction:
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

            # FIXME Should this allow for multiple apps if a string.

            if type(application) != newrelic.api.application.Application:
                application = newrelic.api.application.application_instance(
                        application)

        # Now start recording the actual web transaction.

        transaction = WebTransaction(application, environ)
        transaction.__enter__()

        def _start_response(status, response_headers, *args):
            try:
                transaction.response_code = int(status.split(' ')[0])
            except:
                pass

            try:
                header = filter(lambda x: x[0].lower() == 'content-length',
                                response_headers)[-1:]
                if header:
                    transaction._response_properties['CONTENT_LENGTH'] = \
                            header[0][1]
            except:
                pass

            _write = start_response(status, response_headers, *args)

            def write(data):
                if not transaction._sent_start:
                    transaction._sent_start = time.time()
                result = _write(data)
                transaction._calls_write += 1
                try:
                    transaction._bytes_sent += len(data)
                except:
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
        except:
            transaction.__exit__(*sys.exc_info())
            raise

        return _WSGIApplicationIterable(transaction, result)

def wsgi_application(application=None):
    def decorator(wrapped):
        return WSGIApplicationWrapper(wrapped, application)
    return decorator

def wrap_wsgi_application(module, object_path, application=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            WSGIApplicationWrapper, (application, ))
