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

FROM nginx:latest

COPY <<"EOF" /etc/nginx/nginx.conf
user  nginx;
worker_processes  1;

error_log  /var/log/nginx/error.log notice;
pid        /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  text/plain;

    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    keepalive_timeout  65;
    # HTTP/1.1-3.0 server
    server {
        listen 8080 quic reuseport;
        listen 8080 ssl;
        http2 on;

        add_header Alt-Svc 'h3=":8080"; ma=86400';

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/cert.pem;

        location / {
            return 200 '{"http3": "$http3","http2": "$http2"}';
        }
    }
}
EOF

COPY --chmod=0755 <<"EOF" /docker-entrypoint.d/50-generate-cert.sh
#!/bin/bash
set -euo pipefail

echo "Generating self signed cert..."

CERTFILE=/etc/nginx/ssl/cert.pem
mkdir -p $(dirname $CERTFILE)
openssl req -nodes -newkey rsa:2048 -x509 -keyout $CERTFILE -out $CERTFILE -subj '/CN=localhost' -days 3650

echo "Self signed cert generated at $CERTFILE."
EOF
