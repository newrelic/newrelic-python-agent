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
from newrelic.core.samplers.adaptive_sampler import AdaptiveSampler


class SamplerProxy:
    def __init__(self, settings):
        if settings.serverless_mode.enabled:
            sampling_target_period = 60.0
        else:
            sampling_target_period = settings.sampling_target_period_in_seconds
        adaptive_sampler = AdaptiveSampler(settings.sampling_target, sampling_target_period)
        self._samplers = {"global": adaptive_sampler}
        # Add adaptive sampler instances for each config section if configured.
        self.add_adaptive_sampler(
            (True, 1),
            settings.distributed_tracing.sampler.full_granularity.remote_parent_sampled.adaptive.sampling_target,
            sampling_target_period,
        )
        self.add_adaptive_sampler(
            (True, 2),
            settings.distributed_tracing.sampler.full_granularity.remote_parent_not_sampled.adaptive.sampling_target,
            sampling_target_period,
        )
        self.add_adaptive_sampler(
            (False, 1),
            settings.distributed_tracing.sampler.partial_granularity.remote_parent_sampled.adaptive.sampling_target,
            sampling_target_period,
        )
        self.add_adaptive_sampler(
            (False, 2),
            settings.distributed_tracing.sampler.partial_granularity.remote_parent_not_sampled.adaptive.sampling_target,
            sampling_target_period,
        )

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
        return self.get_sampler(full_granularity, section).compute_sampled(*args, **kwargs)
