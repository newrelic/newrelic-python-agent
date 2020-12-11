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

import re
import socket

def _to_int(version_str):
    m = re.match(r'\d+', version_str)
    return int(m.group(0)) if m else 0

def version2tuple(version_str):
    """Convert version, even if it contains non-numeric chars.

    >>> version2tuple('9.4rc1.1')
    (9, 4)

    """

    parts = version_str.split('.')[:2]
    return tuple(map(_to_int, parts))

def instance_hostname(hostname):
    if hostname == 'localhost' or hostname == "127.0.0.1":
        hostname = socket.gethostname()
    return hostname

def get_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port
