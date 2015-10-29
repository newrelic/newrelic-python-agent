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

RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3 get-pip.py

RUN pip install twine
