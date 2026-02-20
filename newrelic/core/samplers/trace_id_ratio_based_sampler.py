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

# For compatibility with 64 bit trace IDs, the sampler checks the 64
# low-order bits of the trace ID to decide whether to sample a given trace.
TRACE_ID_LIMIT = (1 << 64) - 1


class TraceIdRatioBasedSampler:
    """
    This replicates behavior of TraceIdRatioBased sampler in
    https://github.com/open-telemetry/opentelemetry-python/blob/main/opentelemetry-sdk/src/opentelemetry/sdk/trace/sampling.py.
    """

    def __init__(self, ratio):
        self.ratio = ratio
        self.bound = round(ratio * (TRACE_ID_LIMIT + 1))

    def compute_sampled(self, trace_id):
        if trace_id & TRACE_ID_LIMIT < self.bound:
            return True
        return False
