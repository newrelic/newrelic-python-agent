
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
        rustc \
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

# Setup custom paths for uv
ENV UV_PYTHON_INSTALL_DIR=/opt/uv/python
ENV UV_PYTHON_BIN_DIR=/opt/uv/bin
ENV UV_TOOL_DIR=/opt/uv/tools
ENV UV_CACHE_DIR=/opt/uv/cache
ENV UV_PYTHON_CACHE_DIR="${UV_CACHE_DIR}"
ENV UV_TOOL_BIN_DIR="${UV_PYTHON_BIN_DIR}"
ENV PATH="/opt/uv/bin:${PATH}"
RUN mkdir -m 0755 -p \
    "${UV_PYTHON_INSTALL_DIR}" \
    "${UV_PYTHON_BIN_DIR}" \
    "${UV_TOOL_DIR}" \
    "${UV_CACHE_DIR}"

# Install and configure uv
COPY --chmod=0755 --from=ghcr.io/astral-sh/uv:latest /uv /uvx /opt/uv/bin/
ENV UV_PYTHON_PREFERENCE="only-managed"
ENV UV_PYTHON_DOWNLOADS="manual"
ENV UV_LINK_MODE="copy"

# Install CPython and PyPy versions
RUN uv python install -f \
        cp3.14 cp3.13 cp3.12 cp3.11 cp3.10 cp3.9 \
        pp3.11 pp3.10 \
        cp3.14t && \
    uv clean

# Set default Python version to CPython 3.13
RUN uv python install -f --default cp3.13

# Add shim for pip to use 'uv pip'
COPY --chmod=0775 <<EOF "${UV_PYTHON_BIN_DIR}/pip"
#!/bin/bash
exec uv pip \$@
EOF

# Prevent any runtime downloads
ENV UV_PYTHON_DOWNLOADS=never

# Install tools with uv in isolated environments
RUN uv tool install tox --with tox-uv-bare && \
    uv tool install ruff && \
    uv tool install pre-commit --with pre-commit-uv && \
    uv tool install asv --with virtualenv && \
    uv clean
