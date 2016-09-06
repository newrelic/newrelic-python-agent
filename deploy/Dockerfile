FROM ubuntu:14.04
MAINTAINER Tom Offermann <toffermann@newrelic.com>

RUN apt-get update

RUN apt-get install -y language-pack-en-base \
                       software-properties-common \
                       curl \
                       wget \
                       git \
                       python3 python3-dev

ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

RUN add-apt-repository ppa:fkrull/deadsnakes-python2.7
RUN apt-get update

RUN apt-get install -y python2.7 python2.7-dev
RUN ln -s /usr/bin/python2.7 /usr/bin/python

RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3 get-pip.py

RUN pip install twine awscli
