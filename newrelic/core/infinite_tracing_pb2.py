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

# Protobuf v5 Files
try:
    from newrelic.core.infinite_tracing_v5_pb2 import (  # noqa: F401; pylint: disable=W0611
        AttributeValue,
        RecordStatus,
        Span,
        SpanBatch,
    )
except Exception:
    # Protobuf v4 Files
    try:
        from newrelic.core.infinite_tracing_v4_pb2 import (  # noqa: F401; pylint: disable=W0611
            AttributeValue,
            RecordStatus,
            Span,
            SpanBatch,
        )
    except Exception:
        # Protobuf v3 Files
        try:
            from newrelic.core.infinite_tracing_v3_pb2 import (  # noqa: F401; pylint: disable=W0611
                AttributeValue,
                RecordStatus,
                Span,
                SpanBatch,
            )
        except Exception:
            pass

