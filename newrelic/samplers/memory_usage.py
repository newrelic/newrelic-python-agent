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

"""This module implements a data source for generating metrics about
memory usage.

"""

from newrelic.common.system_info import physical_memory_used

from newrelic.samplers.decorators import data_source_generator


@data_source_generator(name='Memory Usage')
def memory_usage_data_source():
    yield ('Memory/Physical', physical_memory_used())
