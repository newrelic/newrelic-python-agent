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

from concurrent import futures

import grpc
from newrelic.core.infinite_tracing_pb2 import RecordStatus, Span


def record_span(request, context):
    metadata = dict(context.invocation_metadata())
    assert 'agent_run_token' in metadata
    assert 'license_key' in metadata

    for span in request:
        status_code = span.intrinsics.get('status_code', None)
        status_code = status_code and getattr(
            grpc.StatusCode, status_code.string_value)
        if status_code is grpc.StatusCode.OK:
            break
        elif status_code:
            context.abort(status_code, "Abort triggered by client")

        yield RecordStatus(messages_seen=1)


HANDLERS = (
    grpc.method_handlers_generic_handler(
        "com.newrelic.trace.v1.IngestService",
        {
            "RecordSpan": grpc.stream_stream_rpc_method_handler(
                record_span, Span.FromString, RecordStatus.SerializeToString
            )
        },
    ),
)


def main():
    server = grpc.server(futures.ThreadPoolExecutor())
    server.add_generic_rpc_handlers(HANDLERS)
    server.add_insecure_port("127.0.0.1:8000")

    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    main()
