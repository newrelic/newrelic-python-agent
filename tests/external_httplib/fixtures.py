try:
    import http.client as httplib
except ImportError:
    import httplib

import urllib3

from newrelic.agent import (transient_function_wrapper, current_transaction,
    function_wrapper)

from newrelic.common.encoding_utils import (json_encode, json_decode,
    obfuscate, deobfuscate)

def cache_outgoing_headers_fn(wrapped, instance, args, kwargs):
    def _bind_params(header, *values):
        return header, values

    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    header, values = _bind_params(*args, **kwargs)

    try:
        cache = transaction._test_request_headers
    except AttributeError:
        cache = transaction._test_request_headers = {}

    try:
        transaction._test_request_headers[header].extend(values)
    except KeyError:
        transaction._test_request_headers[header] = list(values)

    return wrapped(*args, **kwargs)

@transient_function_wrapper(httplib.__name__, 'HTTPConnection.putheader')
def cache_outgoing_headers(wrapped, instance, args, kwargs):
    return cache_outgoing_headers_fn(wrapped, instance, args, kwargs)

@transient_function_wrapper(urllib3.__name__, 'connection.HTTPConnection.putheader')
def cache_outgoing_headers_urllib3(wrapped, instance, args, kwargs):
    return cache_outgoing_headers_fn(wrapped, instance, args, kwargs)

@function_wrapper
def validate_cross_process_headers(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)

    transaction = current_transaction()
    settings = transaction.settings
    encoding_key = settings.encoding_key

    headers = transaction._test_request_headers

    assert 'X-NewRelic-ID' in headers

    values = headers['X-NewRelic-ID']
    assert len(values) == 1

    assert type(values[0]) == type('')

    cross_process_id = deobfuscate(values[0], encoding_key)
    assert cross_process_id == settings.cross_process_id

    assert 'X-NewRelic-Transaction' in headers

    values = headers['X-NewRelic-Transaction']
    assert len(values) == 1

    assert type(values[0]) == type('')

    guid, record_tt = json_decode(deobfuscate(values[0], encoding_key))

    assert guid == transaction.guid
    assert record_tt == transaction.record_tt

    return result

@transient_function_wrapper(httplib.__name__, 'HTTPResponse.getheaders')
def insert_incoming_headers(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    settings = transaction.settings
    encoding_key = settings.encoding_key

    headers = list(wrapped(*args, **kwargs))

    cross_process_id = '1#2'
    path = 'test'
    queue_time = 1.0
    duration = 2.0
    read_length = 1024
    guid = '0123456789012345'
    record_tt = False

    payload = (cross_process_id, path, queue_time, duration, read_length,
            guid, record_tt)
    app_data = json_encode(payload)

    value = obfuscate(app_data, encoding_key)

    assert type(value) == type('')

    headers.append(('X-NewRelic-App-Data', value))

    return headers

def validate_external_node_params(params=[]):
    @transient_function_wrapper('newrelic.api.external_trace',
            'ExternalTrace.process_response_headers')
    def _validate_external_node_params(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)

        # This is only validating that logic to extract cross process
        # header and update params in ExternalTrace is succeeding. This
        # is actually done after the ExternalTrace __exit__() is called
        # with the ExternalNode only being updated by virtue of the
        # original params dictionary being aliased rather than copied.
        # So isn't strictly validating that params ended up in the actual
        # ExternalNode in the transaction trace.

        for name, value in params:
            assert instance.params[name] == value

        return result

    return _validate_external_node_params
