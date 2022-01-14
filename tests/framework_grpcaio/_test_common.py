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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either exess or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

def get_response(method, request):
    import asyncio

    loop = asyncio.get_event_loop()

    async def _get_response():
        response = method(request)
        try:
            # Await all responses in async iterator and return
            l = []
            async for x in response:
                l.append(x)
            return l
        except:
            # Return single awaited response
            return [await response]

    return loop.run_until_complete(_get_response())
