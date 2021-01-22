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

import gc

from newrelic.samplers.decorators import data_source_factory

@data_source_factory(name='Garbage Collector Metrics')
class _GCDataSource(object):
    def __init__(self, settings, environ):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def __call__(self):
        counts = gc.get_count()

        yield ('GC/objects/all', {'count': sum(counts)})
        for gen, count in enumerate(counts):
            yield ('GC/objects/generation/%d' % (gen, ), {'count': count})


garbage_collector_data_source = _GCDataSource
