FROM ubuntu:16.04

RUN apt-get update

RUN adduser --system --shell `which bash` guest

RUN apt-get install -y language-pack-en-base

ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

RUN apt-get install -y \
    bzip2 \
    vim \
    wget \
    git \
    software-properties-common \
    python-software-properties

# Install python versions.
RUN add-apt-repository ppa:fkrull/deadsnakes && \
    add-apt-repository ppa:jonathonf/python-3.6 && \
    apt-get update && \
    apt-get install -y \
    python2.6 python2.6-dev \
    python2.7 python2.7-dev \
    python3.3 python3.3-dev \
    python3.4 python3.4-dev \
    python3.5 python3.5-dev \
    python3.6 python3.6-dev

RUN wget https://bitbucket.org/pypy/pypy/downloads/pypy2-v5.9.0-linux64.tar.bz2 && \
    tar -C /usr/local -xf pypy2-v5.9.0-linux64.tar.bz2 && \
    rm pypy2-v5.9.0-linux64.tar.bz2 && \
    ln -s /usr/local/pypy2-v5.9.0-linux64/bin/pypy /usr/local/bin/pypy && \
    wget https://bitbucket.org/pypy/pypy/downloads/pypy3-v5.9.0-linux64.tar.bz2 && \
    tar -C /usr/local -xf pypy3-v5.9.0-linux64.tar.bz2 && \
    rm pypy3-v5.9.0-linux64.tar.bz2 && \
    ln -s /usr/local/pypy3-v5.9.0-linux64/bin/pypy3 /usr/local/bin/pypy3

# Pip.
RUN wget https://bootstrap.pypa.io/get-pip.py && \
    python get-pip.py && \
    pip install -U pip==9.0.1 virtualenv==15.1.0 tox==2.3.2

# Needed for tests.
# The DEBIAN_FRONTEND env var prevents mysql-server from prompting for a root
# password
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
    postgresql \
    postgresql-server-dev-9.5 \
    libffi-dev \
    freetds-dev \
    libmemcached-dev \
    build-essential \
    redis-server \
    mysql-server \
    libmysqlclient-dev \
    curl \
    libcurl4-openssl-dev
