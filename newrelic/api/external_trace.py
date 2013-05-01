import functools
import inspect

import newrelic.packages.simplejson as simplejson
from newrelic.api.time_trace import TimeTrace
from newrelic.api.transaction import current_transaction
from newrelic.api.object_wrapper import (ObjectWrapper, wrap_object)
from newrelic.api.web_transaction import obfuscate, deobfuscate
from newrelic.core.external_node import ExternalNode

class ExternalTrace(TimeTrace):

    def __init__(self, transaction, library, url, method=None):
        super(ExternalTrace, self).__init__(transaction)

        self.library = library
        self.url = url
        self.method = method
        self.params = {}
        self.settings = self.transaction.settings

    def dump(self, file):
        print >> file, self.__class__.__name__, dict(library=self.library,
                url=self.url, method=self.method)

    def create_node(self):
        return ExternalNode(library=self.library, url=self.url,
                method=self.method, children=self.children,
                start_time=self.start_time, end_time=self.end_time,
                duration=self.duration, exclusive=self.exclusive,
                params=self.params)

    def terminal_node(self):
        return True

    def process_response_headers(self, response_headers):
        """
        Decode the response headers and create appropriate metics based on the
        header values. The response_headers are passed in as a list of tuples.
        [(HEADER_NAME0, HEADER_VALUE0), (HEADER_NAME1, HEADER_VALUE1)]

        """

        if not self.settings.cross_application_tracer.enabled:
            return

        appdata = None

        try:
            for k, v in response_headers:
                if k.upper() == 'X-NEWRELIC-APP-DATA':
                    appdata = simplejson.loads(
                            deobfuscate(v, self.settings.encoding_key),
                            encoding='UTF-8')
                    break

            if appdata:
                self.params['cross_process_id'] = appdata[0]
                self.params['external_txn_name'] = appdata[1]
                self.params['transaction_guid'] = appdata[5]

        except Exception:
            pass

    @staticmethod
    def generate_request_headers(transaction):
        """
        Return a list of NewRelic specific headers as tuples
        [(HEADER_NAME0, HEADER_VALUE0), (HEADER_NAME1, HEADER_VALUE1)]

        """

        if transaction is None:
            return []

        settings = transaction.settings

        if not settings.cross_application_tracer.enabled:
            return []

        encoded_cross_process_id = obfuscate(settings.cross_process_id,
                settings.encoding_key)

        transaction_data = [transaction.guid, transaction.record_tt]
        encoded_transaction = obfuscate(simplejson.dumps(transaction_data,
                    ensure_ascii=True, encoding='Latin-1'),
                settings.encoding_key)

        nr_headers = [('X-NewRelic-ID', encoded_cross_process_id),
                      ('X-NewRelic-Transaction', encoded_transaction)]

        return nr_headers

def ExternalTraceWrapper(wrapped, library, url, method=None):

    def dynamic_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if callable(url):
            if instance and inspect.ismethod(wrapped):
                _url = url(instance, *args, **kwargs)
            else:
                _url = url(*args, **kwargs)

        else:
            _url = url

        if callable(method):
            if instance and inspect.ismethod(wrapped):
                _method = method(instance, *args, **kwargs)
            else:
                _method = method(*args, **kwargs)

        else:
            _method = method

        with ExternalTrace(transaction, library, _url, _method):
            return wrapped(*args, **kwargs)

    def literal_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        with ExternalTrace(transaction, library, url, method):
            return wrapped(*args, **kwargs)

    if callable(url) or callable(method):
        return ObjectWrapper(wrapped, None, dynamic_wrapper)

    return ObjectWrapper(wrapped, None, literal_wrapper)

def external_trace(library, url, method=None):
    return functools.partial(ExternalTraceWrapper, library=library,
            url=url, method=method)

def wrap_external_trace(module, object_path, library, url, method=None):
    wrap_object(module, object_path, ExternalTraceWrapper,
            (library, url, method))
