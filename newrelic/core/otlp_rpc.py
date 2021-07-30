from newrelic import version

try:
    import grpc
    from newrelic.core.otlp_common_pb2 import AnyValue, InstrumentationLibrary, KeyValue
    from newrelic.core.otlp_resource_pb2 import Resource
    from newrelic.core.otlp_service_pb2 import (
        ExportTraceServiceRequest,
        ExportTraceServiceResponse,
    )
    from newrelic.core.otlp_trace_pb2 import (
        InstrumentationLibrarySpans,
        ResourceSpans,
        Span,
    )

except ImportError:
    grpc = None


class OtlpRpc(object):
    PATH = "/opentelemetry.proto.collector.trace.v1.TraceService/Export"

    def __init__(self, endpoint, entity_guid, agent_run_id, ssl=True):
        if ssl:
            credentials = grpc.ssl_channel_credentials()
            channel = grpc.secure_channel(endpoint, credentials)
        else:
            channel = grpc.insecure_channel(endpoint)
        self.resource_attributes = (
            KeyValue(
                key="entity.guid",
                value=AnyValue(string_value=entity_guid),
            ),
            KeyValue(
                key="agent_run_id",
                value=AnyValue(string_value=agent_run_id),
            ),
        )
        self.channel = channel
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
                        attributes=self.resource_attributes,
                        dropped_attributes_count=0,
                    ),
                    instrumentation_library_spans=(
                        InstrumentationLibrarySpans(
                            instrumentation_library=InstrumentationLibrary(
                                name="newrelic-python-agent",
                                version=version,
                            ),
                            spans=spans,
                        ),
                    ),
                ),
            )
        )
        return self.rpc(request)


if __name__ == "__main__":
    rpc = OtlpRpc("localhost:4317", "looks_guid", ssl=False)
    rpc.send_spans(
        [
            Span(
                trace_id=None,
                span_id=None,
                trace_state=None,
                parent_span_id=None,
                name=None,
                kind=None,
                start_time_unix_nano=None,
                end_time_unix_nano=None,
                attributes=None,
                dropped_attributes_count=None,
                events=None,
                dropped_events_count=None,
                links=None,
                dropped_links_count=None,
                status=None,
            )
        ]
    )
