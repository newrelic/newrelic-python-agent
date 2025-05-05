#!/bin/bash

REPO_ROOT=$(git rev-parse --show-toplevel)
cd $REPO_ROOT

# Generated from:
# opentelemetry-python==1.32.1
# Which uses:
# grpcio-tools==1.63.2
# https://github.com/open-telemetry/opentelemetry-proto/tree/v1.2.0

protos=(
    ./newrelic/packages/opentelemetry_proto/metrics.proto
    ./newrelic/packages/opentelemetry_proto/logs.proto
    ./newrelic/packages/opentelemetry_proto/resource.proto
    ./newrelic/packages/opentelemetry_proto/common.proto
)
python -m grpc_tools.protoc \
    -I ./ \
    --python_out=. \
    ${protos[@]}
