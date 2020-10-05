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
    build-essential \
    software-properties-common \
    python-software-properties

# Install python versions.
RUN echo "deb-src http://archive.ubuntu.com/ubuntu/ xenial main restricted" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get build-dep -y python3.5 && \
    wget https://www.python.org/ftp/python/3.5.5/Python-3.5.5.tgz && \
    tar xfz Python-3.5.5.tgz && \
    cd Python-3.5.5 && \
    ./configure && \
    make -s -j4 && \
    make install && \
    cd .. && \
    rm -rf Python-3.5.5 && \
    rm Python-3.5.5.tgz

RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y \
    python2.7-dev \
    python3.6-dev \
    python3.7-dev \
    python3.8-dev \
    python3.9-dev \
    python3.8-distutils \
    python3.9-distutils

RUN wget https://downloads.python.org/pypy/pypy2.7-v7.3.2-linux64.tar.bz2 && \
    tar -C /usr/local -xf pypy2.7-v7.3.2-linux64.tar.bz2 && \
    rm pypy2.7-v7.3.2-linux64.tar.bz2 && \
    ln -s /usr/local/pypy2.7-v7.3.2-linux64/bin/pypy /usr/local/bin/pypy && \
    wget https://downloads.python.org/pypy/pypy3.6-v7.3.2-linux64.tar.bz2 && \
    tar -C /usr/local -xf pypy3.6-v7.3.2-linux64.tar.bz2 && \
    rm pypy3.6-v7.3.2-linux64.tar.bz2 && \
    ln -s /usr/local/pypy3.6-v7.3.2-linux64/bin/pypy3 /usr/local/bin/pypy3

# Pip.
RUN wget https://bootstrap.pypa.io/get-pip.py && \
    python3.8 get-pip.py && \
    python3.8 -m pip install -U pip==20.2.3 virtualenv==20.0.32 tox==3.20.0

# Needed for tests.
# The DEBIAN_FRONTEND env var prevents mysql-server from prompting for a root
# password
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
    postgresql \
    postgresql-server-dev-9.5 \
    libffi-dev \
    freetds-dev \
    libmemcached-dev \
    redis-server \
    mysql-server \
    libmysqlclient-dev \
    curl \
    libcurl4-openssl-dev
