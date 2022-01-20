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

def get_result(call):
    import asyncio

    loop = asyncio.get_event_loop()

    async def _get_response():
        try:
            # Await all responses in async iterator and return
            l = []
            async for x in call:
                l.append(x)
            return l
        except TypeError:
            # Return single awaited response
            return [await call]

    return loop.run_until_complete(_get_response())


def create_request(streaming_request, count=1, timesout=False, is_async=False):
    from sample_application.sample_application_pb2 import Message

    def _message_stream():
        for i in range(count):
            yield Message(text='Hello World', count=count, timesout=timesout)

    async def _message_stream_async():
        for i in range(count):
            yield Message(text='Hello World', count=count, timesout=timesout)

    if streaming_request:
        if is_async:
            return _message_stream_async()
        else:
            return _message_stream()
    else:
        return Message(text='Hello World', count=count, timesout=timesout)
