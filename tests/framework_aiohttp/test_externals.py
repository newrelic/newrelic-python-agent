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

import pytest
import asyncio

from testing_support.fixtures import (validate_transaction_metrics,
        validate_tt_parenting)

expected_parenting = (
    'TransactionNode', [
        ('FunctionNode', [
            ('ExternalTrace', []),
            ('ExternalTrace', []),
        ]),
])


@validate_tt_parenting(expected_parenting)
@validate_transaction_metrics('_target_application:multi_fetch_handler',
        rollup_metrics=[('External/all', 2)])
def test_multiple_requests_within_transaction(local_server_info, aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request('GET', '/multi_fetch',
                params={'url': local_server_info.url})
        assert resp.status == 200

    aiohttp_app.loop.run_until_complete(fetch())
