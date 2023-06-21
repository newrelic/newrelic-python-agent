
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

FROM ubuntu:20.04

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
        gcc \
        git \
        libbz2-dev \
        libffi-dev \
        libgmp-dev \
        liblzma-dev \
        libmpfr-dev \
        libncurses-dev \
        libpq-dev \
        libreadline-dev \
        libsqlite3-dev \
        libssl-dev \
        locales \
        make \
        openssl \
        python2-dev \
        python3-dev \
        python3-pip \
        sudo \
        unzip \
        vim \
        wget \
        zip \
        zlib1g \
        zlib1g-dev \
        zsh && \
    rm -rf /var/lib/apt/lists/*

# Set the locale
RUN locale-gen --no-purge en_US.UTF-8
ENV LANG=en_US.UTF-8 \ LANGUAGE=en_US:en \ LC_ALL=en_US.UTF-8

# Set user to non-root
ENV HOME /home/github
RUN useradd -rm -d "${HOME}" -s /bin/bash -u 1000 github
USER 1000:1000
WORKDIR "${HOME}"

# Install pyenv
ENV PYENV_ROOT="${HOME}/.pyenv"
RUN curl https://pyenv.run/ | /bin/bash
ENV PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:${PATH}"
RUN echo 'eval "$(pyenv init -)"' >>$HOME/.bashrc && \
    pyenv update

# Install Python
ARG PYTHON_VERSIONS="3.10 3.9 3.8 3.7 3.11 2.7 pypy2.7 pypy3.7"
ARG PYTHON_VERSIONS="3.10 2.7"
COPY --chown=1000:1000 --chmod=+x ./install-python.sh /tmp/install-python.sh
COPY ./requirements.txt /requirements.txt
RUN /tmp/install-python.sh && \
    rm /tmp/install-python.sh
