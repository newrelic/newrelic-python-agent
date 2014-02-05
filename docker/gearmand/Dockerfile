FROM ubuntu:12.04

RUN apt-get update

RUN apt-get install -y python-software-properties
RUN add-apt-repository ppa:gearman-developers/ppa

RUN apt-get update

RUN apt-get install -y gearman-job-server gearman-tools

EXPOSE 4730 
ENTRYPOINT ["gearmand"]
CMD ["-p", "4730"]
