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
    from google.protobuf import __version__

    PROTOBUF_VERSION = tuple(int(v) for v in __version__.split("."))
except Exception:
    PROTOBUF_VERSION = (0, 0, 0)

# Import appropriate generated pb2 file for protobuf version
if PROTOBUF_VERSION >= (6,):
    from newrelic.core.infinite_tracing_v6_pb2 import AttributeValue, RecordStatus, Span, SpanBatch  # noqa: F401
elif PROTOBUF_VERSION >= (5,):
    from newrelic.core.infinite_tracing_v5_pb2 import AttributeValue, RecordStatus, Span, SpanBatch  # noqa: F401
elif PROTOBUF_VERSION >= (4,):
    from newrelic.core.infinite_tracing_v4_pb2 import AttributeValue, RecordStatus, Span, SpanBatch  # noqa: F401
else:
    from newrelic.core.infinite_tracing_v3_pb2 import AttributeValue, RecordStatus, Span, SpanBatch  # noqa: F401

# To generate the pb2 file:
#
# 1. Install grpcio-tools
#   * The exact version needed is hard to determine, trial and error is normally used.
#   * The newly generated pb2 file will specify the minimum protobuf version needed, we want that to be the first version from this major version series.
# 2. Run the command below to overwrite this file with the newly generated pb2 file.
# 3. Rename the pb2 file to infinite_tracing_vX_pb2 where X is the protobuf major version.
# 4. Restore this file from git.
# 5. Update the if statements above to import the new pb2 file when using the correct protobuf version.
# 6. Validate the generated pb2 file works with the oldest protobuf version in this major version series by importing this file.
#
# python -m grpc_tools.protoc --proto_path=newrelic/core --python_out=newrelic/core newrelic/core/infinite_tracing.proto
