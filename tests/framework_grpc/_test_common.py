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

import functools
import threading

from newrelic.api.application import application_instance


def create_request(streaming_request, count=1, timesout=False):
    from sample_application import Message

    def _message_stream():
        for i in range(count):
            yield Message(text="Hello World", count=count, timesout=timesout)

    if streaming_request:
        request = _message_stream()
    else:
        request = Message(text="Hello World", count=count, timesout=timesout)

    return request


def get_result(method, request, *args, **kwargs):
    try:
        from grpc._channel import _InactiveRpcError as Error
    except ImportError:
        from grpc._channel import _Rendezvous as Error
    result = None
    try:
        result = method(request, *args, **kwargs)
        list(result)
    except Error as e:
        result = e
    except Exception:
        pass
    return result


def wait_for_transaction_completion(fn):
    CALLED = threading.Event()
    application = application_instance()
    record_transaction = application.record_transaction

    def record_transaction_wrapper(*args, **kwargs):
        record_transaction(*args, **kwargs)
        CALLED.set()

    @functools.wraps(fn)
    def _waiter(*args, **kwargs):
        application.record_transaction = record_transaction_wrapper
        try:
            result = fn(*args, **kwargs)
            CALLED.wait(timeout=1)
            return result
        finally:
            application.record_transaction = record_transaction

    return _waiter
