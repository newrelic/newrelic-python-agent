from concurrent import futures

import grpc
from newrelic.core.infinite_tracing_pb2 import RecordStatus, Span


def record_span(request, context):
    metadata = dict(context.invocation_metadata())
    assert 'agent_run_token' in metadata
    assert 'license_key' in metadata

    for span in request:
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