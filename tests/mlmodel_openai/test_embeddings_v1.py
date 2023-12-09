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
from testing_support.fixtures import (  # noqa: F401; pylint: disable=W0611
    override_application_settings,
    reset_core_stats_engine,
)

from newrelic.api.background_task import background_task


@reset_core_stats_engine()
@background_task()
def test_openai_embedding_sync(set_trace_info, sync_openai_client):
    set_trace_info()
    sync_openai_client.embeddings.create(input="This is an embedding test.", model="text-embedding-ada-002")
