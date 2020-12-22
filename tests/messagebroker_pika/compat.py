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

from minversion import pika_version_info


def basic_consume(channel, queue, callback, auto_ack=None):
    kwargs = {'queue': queue}
    if pika_version_info[0] < 1:
        kwargs['consumer_callback'] = callback
        if auto_ack is not None:
            kwargs['no_ack'] = not auto_ack
    else:
        kwargs['on_message_callback'] = callback
        if auto_ack is not None:
            kwargs['auto_ack'] = auto_ack

    return channel.basic_consume(**kwargs)
