FROM ubuntu:12.04

RUN apt-get update

RUN apt-get install -y memcached

EXPOSE 11211
ENTRYPOINT ["memcached"]
CMD ["-p", "11211"]
USER daemon
