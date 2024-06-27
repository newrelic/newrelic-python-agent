
# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM ubuntu:24.04

# Install OS packages
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install -y \
        bash \
        build-essential \
        curl \
        expat \
        fish \
        fontconfig \
        freetds-common \
        freetds-dev \
        gcc \
        git \
        libbz2-dev \
        libcurl4-openssl-dev \
        libffi-dev \
        libgmp-dev \
        libkrb5-dev \
        liblzma-dev \
        libmpfr-dev \
        libncurses-dev \
        libpq-dev \
        libreadline-dev \
        libsqlite3-dev \
        libssl-dev \
        locales \
        make \
        odbc-postgresql \
        openssl \
        python3-dev \
        python3-pip \
        sudo \
        tzdata \
        unixodbc-dev \
        unzip \
        vim \
        wget \
        zip \
        zlib1g \
        zlib1g-dev \
        zsh && \
    rm -rf /var/lib/apt/lists/*

# Build librdkafka from source
ARG LIBRDKAFKA_VERSION=2.1.1
RUN cd /tmp && \
    wget https://github.com/confluentinc/librdkafka/archive/refs/tags/v${LIBRDKAFKA_VERSION}.zip -O ./librdkafka.zip && \
    unzip ./librdkafka.zip && \
    rm ./librdkafka.zip && \
    cd ./librdkafka-${LIBRDKAFKA_VERSION} && \
    ./configure && \
    make all install && \
    cd /tmp && \
    rm -rf ./librdkafka-${LIBRDKAFKA_VERSION}

# Setup ODBC config
RUN sed -i 's|Driver=psqlodbca.so|Driver=/usr/lib/x86_64-linux-gnu/odbc/psqlodbca.so|g' /etc/odbcinst.ini && \
    sed -i 's|Driver=psqlodbcw.so|Driver=/usr/lib/x86_64-linux-gnu/odbc/psqlodbcw.so|g' /etc/odbcinst.ini && \
    sed -i 's|Setup=libodbcpsqlS.so|Setup=/usr/lib/x86_64-linux-gnu/odbc/libodbcpsqlS.so|g' /etc/odbcinst.ini

# Set the locale
RUN locale-gen --no-purge en_US.UTF-8
ENV LANG=en_US.UTF-8 \ LANGUAGE=en_US:en \ LC_ALL=en_US.UTF-8
ENV TZ="Etc/UTC"
RUN ln -fs "/usr/share/zoneinfo/${TZ}" /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# Use root user
ENV HOME /root
WORKDIR "${HOME}"

# Install pyenv
ENV PYENV_ROOT="/usr/local/pyenv"
RUN curl https://pyenv.run/ | /bin/bash
ENV PATH="${PYENV_ROOT}/bin:${PYENV_ROOT}/shims:${PATH}"
RUN echo 'eval "$(pyenv init -)"' >>${HOME}/.bashrc && \
    pyenv update

# Install Python
ARG PYTHON_VERSIONS="3.11 3.10 3.9 3.8 3.7 3.12 pypy3.10-7.3.15"
COPY --chown=1000:1000 --chmod=+x ./install-python.sh /tmp/install-python.sh
RUN /tmp/install-python.sh && \
    rm /tmp/install-python.sh

# Install dependencies for main python installation
COPY ./requirements.txt /tmp/requirements.txt
RUN pyenv exec pip install --upgrade -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt