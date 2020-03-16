import grpc
from newrelic.core.mtb_pb2 import RecordStatus, Span


def record_span(request, context):
    count = 0

    for span in request:
        count += 1

    yield RecordStatus(messages_seen=count)


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
