# syntax=docker/dockerfile:1.4
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

FROM redis:7.0.12

COPY <<"EOF" /etc/redis.conf
bind 0.0.0.0
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 5000
cluster-preferred-endpoint-type hostname
appendonly yes
EOF

ENV REDIS_PORT=6379 \
    REDIS_ANNOUNCE_HOSTNAME=localhost

CMD ["sh", "-c", "exec redis-server /etc/redis.conf --port \"$REDIS_PORT\" --cluster-announce-hostname \"$REDIS_ANNOUNCE_HOSTNAME\" --cluster-announce-port \"$REDIS_PORT\""]
