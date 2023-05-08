from newrelic import version

try:
    import grpc

    from newrelic.core.otlp_common_pb2 import AnyValue, InstrumentationScope, KeyValue
    from newrelic.core.otlp_resource_pb2 import Resource
    from newrelic.core.otlp_trace_pb2 import ResourceSpans, ScopeSpans, Span
    from newrelic.core.otlp_trace_service_pb2 import (
        ExportTraceServiceRequest,
        ExportTraceServiceResponse,
    )

except ImportError:
    grpc = None
    AnyValue, InstrumentationScope, KeyValue = None, None, None
    Resource = None
    ResourceSpans, ScopeSpans, Span = None, None, None
    ExportTraceServiceRequest, ExportTraceServiceResponse = None, None


class OtlpRpc(object):
    PATH = "/opentelemetry.proto.collector.trace.v1.TraceService/Export"

    # def __init__(self, endpoint, entity_guid, agent_run_id, ssl=True, compression=None):
    def __init__(self, endpoint, metadata, record_metric, ssl=True, compression=None):
        self.endpoint = endpoint
        self.metadata = metadata
        self.record_metric = record_metric
        self.ssl = ssl
        self.compression_setting = grpc.Compression.Gzip if compression else grpc.Compression.NoCompression

        self.create_channel()

    def create_channel(self):
        if self.ssl:
            credentials = grpc.ssl_channel_credentials()
            channel = grpc.secure_channel(self.endpoint, credentials, compression=self.compression_setting)
        else:
            channel = grpc.insecure_channel(self.endpoint, compression=self.compression_setting)

        self.channel = channel

        # self.rpc = self.channel.stream_stream(
        self.rpc = self.channel.unary_unary(
            self.PATH,
            ExportTraceServiceRequest.SerializeToString,
            ExportTraceServiceResponse.FromString,
        )

    def send_spans(self, spans):
        request = ExportTraceServiceRequest(
            resource_spans=(
                ResourceSpans(
                    resource=Resource(
                        attributes=self.metadata,
                        dropped_attributes_count=0,
                    ),
                    scope_spans=ScopeSpans(
                        scope=InstrumentationScope(
                            name="newrelic-python-agent",
                            version=version,
                        ),
                        spans=spans,
                    ),
                ),
            ),
        )
        return self.rpc(request)


# if __name__ == "__main__":
#     rpc = OtlpRpc("localhost:4317", "looks_guid", ssl=False)
#     rpc.send_spans(
#         [
#             Span(
#                 trace_id=None,
#                 span_id=None,
#                 trace_state=None,
#                 parent_span_id=None,
#                 name=None,
#                 kind=None,
#                 start_time_unix_nano=None,
#                 end_time_unix_nano=None,
#                 attributes=None,
#                 dropped_attributes_count=None,
#                 events=None,
#                 dropped_events_count=None,
#                 links=None,
#                 dropped_links_count=None,
#                 status=None,
#             )
#         ]
#     )
