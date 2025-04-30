
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
ARG TARGETPLATFORM

# Install OS packages
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install -y \
        bash \
        build-essential \
        curl \
        default-libmysqlclient-dev \
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
        pkg-config \
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

# Install addlicense binary
ARG ADDLICENSE_VERSION=1.1.1
RUN if [ "${TARGETPLATFORM}" = "linux/amd64" ]; then export ARCH="x86_64"; else export ARCH="arm64"; fi && \
    mkdir -p /tmp/addlicense && \
    wget https://github.com/google/addlicense/releases/download/v${ADDLICENSE_VERSION}/addlicense_${ADDLICENSE_VERSION}_Linux_${ARCH}.tar.gz \
        -O /tmp/addlicense/addlicense.tar.gz && \
        tar -xzvf /tmp/addlicense/addlicense.tar.gz -C /tmp/addlicense && \
    mv /tmp/addlicense/addlicense /usr/local/bin/addlicense && \
    rm -rf /tmp/addlicense && \
    chmod +x /usr/local/bin/addlicense

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
RUN if [ "${TARGETPLATFORM}" = "linux/amd64" ]; then export ARCH="x86_64"; else export ARCH="aarch64"; fi && \
    sed -i "s|Driver=psqlodbca.so|Driver=/usr/lib/${ARCH}-linux-gnu/odbc/psqlodbca.so|g" /etc/odbcinst.ini && \
    sed -i "s|Driver=psqlodbcw.so|Driver=/usr/lib/${ARCH}-linux-gnu/odbc/psqlodbcw.so|g" /etc/odbcinst.ini && \
    sed -i "s|Setup=libodbcpsqlS.so|Setup=/usr/lib/${ARCH}-linux-gnu/odbc/libodbcpsqlS.so|g" /etc/odbcinst.ini

# Set the locale
RUN locale-gen --no-purge en_US.UTF-8
ENV LANG=en_US.UTF-8 \ LANGUAGE=en_US:en \ LC_ALL=en_US.UTF-8
ENV TZ="Etc/UTC"
RUN ln -fs "/usr/share/zoneinfo/${TZ}" /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# Use root user
ENV HOME=/root
WORKDIR "${HOME}"

# Install pyenv
ENV PYENV_ROOT="/usr/local/pyenv"
RUN curl https://pyenv.run/ | /bin/bash
ENV PATH="${PYENV_ROOT}/bin:${PYENV_ROOT}/shims:${PATH}"
RUN echo 'eval "$(pyenv init -)"' >>${HOME}/.bashrc && \
    pyenv update

# Install Python
ARG PYTHON_VERSIONS="3.12 3.11 3.10 3.9 3.8 3.7 3.13 pypy3.10-7.3.17"
COPY --chown=0:0 --chmod=755 ./install-python.sh /tmp/install-python.sh
RUN /tmp/install-python.sh && \
    rm /tmp/install-python.sh

# Install dependencies for main python installation
COPY ./requirements.txt /tmp/requirements.txt
RUN pyenv exec pip install --upgrade -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Install tools with pipx in isolated environments
COPY ./requirements-tools.txt /tmp/requirements-tools.txt
ENV PIPX_HOME="/opt/pipx"
ENV PIPX_BIN_DIR="${PIPX_HOME}/bin"
ENV PATH="${PIPX_BIN_DIR}:${PATH}"
RUN mkdir -p "${PIPX_BIN_DIR}" && \
    while IFS="" read -r line || [ -n "$line" ]; do \
        pyenv exec pipx install --global "${line}"; \
    done </tmp/requirements-tools.txt && \
    rm /tmp/requirements-tools.txt

# Inject compatibile dependencies for tox
COPY ./requirements-tox.txt /tmp/requirements-tox.txt
RUN pipx inject --force tox -r /tmp/requirements-tox.txt && \
    rm /tmp/requirements-tox.txt

# # Install Azure Function Core Tools
# ENV DEBIAN_VERSION=12
# RUN apt-get update && apt-get install gpg wget  -y && \
#     wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | tee /usr/share/keyrings/microsoft-prod.gpg && \
#     wget -q https://packages.microsoft.com/config/debian/$DEBIAN_VERSION/prod.list && \
#     mv prod.list /etc/apt/sources.list.d/microsoft-prod.list && \
#     chown root:root /usr/share/keyrings/microsoft-prod.gpg && \
#     chown root:root /etc/apt/sources.list.d/microsoft-prod.list && \
#     apt-get update && apt-get install azure-functions-core-tools-4  -y && \
#     apt-get update && apt-get install libicu-dev  -y


# RUN wget -q https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb && \
#     sudo dpkg -i packages-microsoft-prod.deb && \
#     sudo apt-get update && \
#     sudo apt-get install azure-functions-core-tools-4 && \
#     sudo apt-get install libicu