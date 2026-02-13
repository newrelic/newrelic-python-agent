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
import logging

from newrelic.core.samplers.adaptive_sampler import AdaptiveSampler
from newrelic.core.samplers.trace_id_ratio_based_sampler import TraceIdRatioBasedSampler

_logger = logging.getLogger(__name__)


class SamplerProxy:
    def __init__(self, settings):
        if settings.serverless_mode.enabled:
            sampling_target_period = 60.0
        else:
            sampling_target_period = settings.sampling_target_period_in_seconds
        adaptive_sampler = AdaptiveSampler(settings.sampling_target, sampling_target_period)
        self._samplers = {"global": adaptive_sampler}

        # full_gran_root_ratio = None
        # full_gran_parent_sampled_ratio = None
        # full_gran_parent_not_sampled_ratio = None
        ## Add sampler instances for each config section if configured.
        # if settings.distributed_tracing.sampler.full_granularity.enabled:
        #    # If the ratio is not defined fallback to adaptive sampler.
        #    if (
        #        settings.distributed_tracing.sampler._root == "trace_id_ratio_based"
        #        and settings.distributed_tracing.sampler.root.trace_id_ratio_based.ratio
        #    ):
        #        full_gran_root_ratio = settings.distributed_tracing.sampler.root.trace_id_ratio_based.ratio
        #        self.add_trace_id_ratio_based_sampler((True, 0), full_gran_root_ratio)
        #    else:
        #        self.add_adaptive_sampler(
        #            (True, 0),
        #            settings.distributed_tracing.sampler.root.adaptive.sampling_target,
        #            sampling_target_period,
        #        )
        #    # If the ratio is not defined fallback to adaptive sampler.
        #    if (
        #        settings.distributed_tracing.sampler._remote_parent_sampled == "trace_id_ratio_based"
        #        and settings.distributed_tracing.sampler.remote_parent_sampled.trace_id_ratio_based.ratio
        #    ):
        #        full_gran_parent_sampled_ratio = (
        #            settings.distributed_tracing.sampler.remote_parent_sampled.trace_id_ratio_based.ratio
        #        )
        #        self.add_trace_id_ratio_based_sampler((True, 1), full_gran_parent_sampled_ratio)
        #    else:
        #        self.add_adaptive_sampler(
        #            (True, 1),
        #            settings.distributed_tracing.sampler.remote_parent_sampled.adaptive.sampling_target,
        #            sampling_target_period,
        #        )
        #    # If the ratio is not defined fallback to adaptive sampler.
        #    if (
        #        settings.distributed_tracing.sampler._remote_parent_not_sampled == "trace_id_ratio_based"
        #        and settings.distributed_tracing.sampler.remote_parent_not_sampled.trace_id_ratio_based.ratio
        #    ):
        #        full_gran_parent_not_sampled_ratio = (
        #            settings.distributed_tracing.sampler.remote_parent_not_sampled.trace_id_ratio_based.ratio
        #        )
        #        self.add_trace_id_ratio_based_sampler((True, 2), full_gran_parent_not_sampled_ratio)
        #    else:
        #        self.add_adaptive_sampler(
        #            (True, 2),
        #            settings.distributed_tracing.sampler.remote_parent_not_sampled.adaptive.sampling_target,
        #            sampling_target_period,
        #        )
        # if settings.distributed_tracing.sampler.partial_granularity.enabled:
        #    # If the ratio is not defined fallback to adaptive sampler.
        #    if (
        #        settings.distributed_tracing.sampler.partial_granularity._root == "trace_id_ratio_based"
        #        and settings.distributed_tracing.sampler.partial_granularity.root.trace_id_ratio_based.ratio
        #    ):
        #        # If both full and partial are set to use the trace id ratio based sampler,
        #        # set partial granularity ratio = full ratio + partial ratio.
        #        ratio = settings.distributed_tracing.sampler.partial_granularity.root.trace_id_ratio_based.ratio
        #        if full_gran_root_ratio:
        #            ratio = min(ratio + full_gran_root_ratio, 1)
        #        self.add_trace_id_ratio_based_sampler((False, 0), ratio)
        #    else:
        #        self.add_adaptive_sampler(
        #            (False, 0),
        #            settings.distributed_tracing.sampler.partial_granularity.root.adaptive.sampling_target,
        #            sampling_target_period,
        #        )
        #    # If the ratio is not defined fallback to adaptive sampler.
        #    if (
        #        settings.distributed_tracing.sampler.partial_granularity._remote_parent_sampled
        #        == "trace_id_ratio_based"
        #        and settings.distributed_tracing.sampler.partial_granularity.remote_parent_sampled.trace_id_ratio_based.ratio
        #    ):
        #        # If both full and partial are set to use the trace id ratio based sampler,
        #        # set partial granularity ratio = full ratio + partial ratio.
        #        ratio = settings.distributed_tracing.sampler.partial_granularity.remote_parent_sampled.trace_id_ratio_based.ratio
        #        if full_gran_parent_sampled_ratio:
        #            ratio = min(ratio + full_gran_parent_sampled_ratio, 1)
        #        self.add_trace_id_ratio_based_sampler((False, 1), ratio)
        #    else:
        #        self.add_adaptive_sampler(
        #            (False, 1),
        #            settings.distributed_tracing.sampler.partial_granularity.remote_parent_sampled.adaptive.sampling_target,
        #            sampling_target_period,
        #        )
        #    # If the ratio is not defined fallback to adaptive sampler.
        #    if (
        #        settings.distributed_tracing.sampler.partial_granularity._remote_parent_not_sampled
        #        == "trace_id_ratio_based"
        #        and settings.distributed_tracing.sampler.partial_granularity.remote_parent_not_sampled.trace_id_ratio_based.ratio
        #    ):
        #        # If both full and partial are set to use the trace id ratio based sampler,
        #        # set partial granularity ratio = full ratio + partial ratio.
        #        ratio = settings.distributed_tracing.sampler.partial_granularity.remote_parent_not_sampled.trace_id_ratio_based.ratio
        #        if full_gran_parent_not_sampled_ratio:
        #            ratio = min(ratio + full_gran_parent_not_sampled_ratio, 1)
        #        self.add_trace_id_ratio_based_sampler((False, 2), ratio)
        #    else:
        #        self.add_adaptive_sampler(
        #            (False, 2),
        #            settings.distributed_tracing.sampler.partial_granularity.remote_parent_not_sampled.adaptive.sampling_target,
        #            sampling_target_period,
        #        )

    def add_trace_id_ratio_based_sampler(self, key, ratio):
        """
        Add a trace id ratio based sampler instance to self._samplers.
        """
        ratio_sampler = TraceIdRatioBasedSampler(ratio)
        self._samplers[key] = ratio_sampler

    def add_adaptive_sampler(self, key, sampling_target, sampling_target_period):
        """
        Add an adaptive sampler instance to self._samplers if the sampling_target is specified.
        """
        if sampling_target:
            adaptive_sampler = AdaptiveSampler(sampling_target, sampling_target_period)
            self._samplers[key] = adaptive_sampler

    def get_sampler(self, full_granularity, section):
        # Return the sampler instance for the given config section.
        # If no instance is present, return the global adaptive sampler instance instead.
        return self._samplers.get((full_granularity, section)) or self._samplers["global"]

    def compute_sampled(self, full_granularity, section, *args, **kwargs):
        """
        full_granularity: True is full granularity, False is partial granularity
        section: 0-root, 1-remote_parent_sampled, 2-remote_parent_not_sampled
        """
        try:
            return self.get_sampler(full_granularity, section).compute_sampled(*args, **kwargs)
        except Exception:
            # This happens when there is a mismatch in the settings used to create the
            # samplers vs request a sampler inside a transaction. While this shouldn't
            # ever happen this is a safety guard.
            _logger.warning(
                "Attempted to access sampler (%s, %s) but encountered an error. Falling back on global adaptive sampler.",
                full_granularity,
                section,
            )
            return self._samplers["global"].compute_sampled()
