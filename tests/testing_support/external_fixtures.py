# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import http.client as httplib
except ImportError:
    import httplib


from newrelic.api.external_trace import ExternalTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import transient_function_wrapper
from newrelic.common.encoding_utils import json_encode, obfuscate


def create_incoming_headers(transaction):
    settings = transaction.settings
    encoding_key = settings.encoding_key

    headers = []

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

    assert isinstance(value, type(''))

    headers.append(('X-NewRelic-App-Data', value))

    return headers


def validate_synthetics_external_trace_header(required_header=(),
        should_exist=True):
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_synthetics_external_trace_header(wrapped, instance,
            args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)

        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            if should_exist:
                # XXX This validation routine is technically
                # broken as the argument to record_transaction()
                # is not actually an instance of the Transaction
                # object. Instead it is a TransactionNode object.
                # The static method generate_request_headers() is
                # expecting a Transaction object and not
                # TransactionNode. The latter provides attributes
                # which are not updatable by the static method
                # generate_request_headers(), which it wants to
                # update, so would fail. For now what we do is use
                # a little proxy wrapper so that updates do not
                # fail. The use of this wrapper needs to be
                # reviewed and a better way of achieving what is
                # required found.

                class _Transaction(object):
                    def __init__(self, wrapped):
                        self.__wrapped__ = wrapped

                    def __getattr__(self, name):
                        return getattr(self.__wrapped__, name)

                external_headers = ExternalTrace.generate_request_headers(
                        _Transaction(transaction))
                assert required_header in external_headers, (
                        'required_header=%r, ''external_headers=%r' % (
                        required_header, external_headers))

        return result

    return _validate_synthetics_external_trace_header


@transient_function_wrapper(httplib.__name__, 'HTTPConnection.putheader')
def cache_outgoing_headers(wrapped, instance, args, kwargs):
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
        cache[header].extend(values)
    except KeyError:
        cache[header] = list(values)

    return wrapped(*args, **kwargs)


@transient_function_wrapper(httplib.__name__, 'HTTPResponse.getheaders')
def insert_incoming_headers(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    headers = list(wrapped(*args, **kwargs))

    headers.extend(create_incoming_headers(transaction))

    return headers