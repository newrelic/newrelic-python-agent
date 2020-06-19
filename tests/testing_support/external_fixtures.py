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

from newrelic.api.external_trace import ExternalTrace
from newrelic.common.object_wrapper import transient_function_wrapper


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
