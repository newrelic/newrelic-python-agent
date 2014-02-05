FROM ubuntu:12.04
MAINTAINER Graham Dumpleton <grahamd@newrelic.com>

RUN adduser --system --shell `which bash` guest

RUN apt-get install -y bzip2
RUN apt-get install -y vim
RUN apt-get install -y wget

RUN apt-get update

RUN apt-get install -y python-software-properties
RUN add-apt-repository ppa:fkrull/deadsnakes

RUN apt-get update

RUN apt-get install -y python2.6 python2.6-dev
RUN apt-get install -y python2.7 python2.7-dev
RUN apt-get install -y python3.3 python3.3-dev

RUN wget https://bitbucket.org/pypy/pypy/downloads/pypy-2.2.1-linux64.tar.bz2
RUN tar -C /usr/local -xf pypy-2.2.1-linux64.tar.bz2

RUN ln -s /usr/local/pypy-2.2.1-linux64/bin/pypy /usr/local/bin/pypy

RUN wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
RUN python ez_setup.py

RUN wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py
RUN python get-pip.py

RUN pip install 'pip<1.5' 'virtualenv<1.11' 'tox<1.7.0'
