FROM ubuntu:14.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update
RUN apt-get install -y redis-server

# Edit redis.conf: Don't daemonize.

RUN sed -i 's/daemonize yes/daemonize no/' /etc/redis/redis.conf

# Edit redis.conf: Listen on all interfaces.

RUN sed -i 's/bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf

EXPOSE 6379

USER redis

CMD ["/usr/bin/redis-server"]
