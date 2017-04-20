import functools

from .time_trace import TimeTrace
from .transaction import current_transaction
from ..core.external_node import ExternalNode
from ..common.object_wrapper import FunctionWrapper, wrap_object
from ..common.encoding_utils import (obfuscate, deobfuscate, json_encode,
    json_decode)


class ExternalTrace(TimeTrace):

    node = ExternalNode

    def __init__(self, transaction, library, url, method=None):
        super(ExternalTrace, self).__init__(transaction)

        self.library = library
        self.url = url
        self.method = method
        self.params = {}
        self.settings = transaction and self.transaction.settings or None

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(
                library=self.library, url=self.url, method=self.method))

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
                    appdata = json_decode(deobfuscate(v,
                            self.settings.encoding_key))
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

        nr_headers = []

        if settings.cross_application_tracer.enabled:

            transaction.is_part_of_cat = True
            encoded_cross_process_id = obfuscate(settings.cross_process_id,
                    settings.encoding_key)
            nr_headers.append(('X-NewRelic-ID', encoded_cross_process_id))

            transaction_data = [transaction.guid, transaction.record_tt,
                    transaction.trip_id, transaction.path_hash]
            encoded_transaction = obfuscate(json_encode(transaction_data),
                    settings.encoding_key)
            nr_headers.append(('X-NewRelic-Transaction', encoded_transaction))

        if transaction.synthetics_header:
            nr_headers.append(
                    ('X-NewRelic-Synthetics', transaction.synthetics_header))

        return nr_headers


def ExternalTraceWrapper(wrapped, library, url, method=None):

    def dynamic_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if callable(url):
            if instance is not None:
                _url = url(instance, *args, **kwargs)
            else:
                _url = url(*args, **kwargs)

        else:
            _url = url

        if callable(method):
            if instance is not None:
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
        return FunctionWrapper(wrapped, dynamic_wrapper)

    return FunctionWrapper(wrapped, literal_wrapper)


def external_trace(library, url, method=None):
    return functools.partial(ExternalTraceWrapper, library=library,
            url=url, method=method)


def wrap_external_trace(module, object_path, library, url, method=None):
    wrap_object(module, object_path, ExternalTraceWrapper,
            (library, url, method))
