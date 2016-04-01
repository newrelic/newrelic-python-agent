FROM ubuntu:12.04

RUN apt-get update
RUN apt-get install -y couchdb

EXPOSE 5984

RUN echo '[httpd]' >> ./couch_config.ini
RUN echo 'bind_address = 0.0.0.0' >> ./couch_config.ini

CMD ["/usr/bin/couchdb", "-a", "./couch_config.ini"]
