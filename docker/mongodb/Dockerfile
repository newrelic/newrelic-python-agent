FROM ubuntu:12.04

RUN apt-get update

RUN apt-get install -y mongodb

# Create data directory.
RUN mkdir -p /data/db
RUN chown -R mongodb:mongodb /data/db

EXPOSE 27017

USER mongodb

CMD ["/usr/bin/mongod", "--port", "27017", "--bind_ip", "0.0.0.0"]
