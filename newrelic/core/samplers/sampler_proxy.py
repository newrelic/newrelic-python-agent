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
        self._samplers = [adaptive_sampler]

    def get_sampler(self, full_granularity, section):
        return self._samplers[0]

    def compute_sampled(self, full_granularity, section, *args, **kwargs):
        """
        full_granularity: True is full granularity, False is partial granularity
        section: 0-root, 1-remote_parent_sampled, 2-remote_parent_not_sampled
        """
        return self.get_sampler(full_granularity, section).compute_sampled(*args, **kwargs)
