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

import os
import pwd

USER = pwd.getpwuid(os.getuid()).pw_name


def postgresql_settings():
    """Return a list of dict of settings for connecting to postgresql.

    Will return the correct settings, depending on which of the environments it
    is running in. It attempts to set variables in the following order, where
    later environments override earlier ones.

        1. Local
        2. Github Actions
    """

    host = "host.docker.internal" if "GITHUB_ACTIONS" in os.environ else "localhost"
    instances = 2
    settings = [
        {
            "user": "postgres",
            "password": "postgres",
            "name": "postgres",
            "host": host,
            "port": 8080 + instance_num,
            "table_name": "postgres_table_" + str(os.getpid()),
        }
        for instance_num in range(instances)
    ]
    return settings


def mysql_settings():
    """Return a list of dict of settings for connecting to MySQL.

    Will return the correct settings, depending on which of the environments it
    is running in. It attempts to set variables in the following order, where
    later environments override earlier ones.

        1. Local
        2. Github Actions
    """

    host = "host.docker.internal" if "GITHUB_ACTIONS" in os.environ else "127.0.0.1"
    instances = 1
    settings = [
        {
            "user": "python_agent",
            "password": "python_agent",
            "name": "python_agent",
            "host": host,
            "port": 8080 + instance_num,
            "namespace": str(os.getpid()),
        }
        for instance_num in range(instances)
    ]
    return settings


def mssql_settings():
    """Return a list of dict of settings for connecting to MS SQL.

    Will return the correct settings, depending on which of the environments it
    is running in. It attempts to set variables in the following order, where
    later environments override earlier ones.

        1. Local
        2. Github Actions
    """

    host = "host.docker.internal" if "GITHUB_ACTIONS" in os.environ else "127.0.0.1"
    instances = 1
    settings = [
        {
            "user": "SA",
            "password": "python_agent#1234",
            "host": host,
            "port": 8080 + instance_num,
            "namespace": str(os.getpid()),
        }
        for instance_num in range(instances)
    ]
    return settings


def redis_settings():
    """Return a list of dict of settings for connecting to redis.

    Will return the correct settings, depending on which of the environments it
    is running in. It attempts to set variables in the following order, where
    later environments override earlier ones.

        1. Local
        2. Github Actions
    """

    host = "host.docker.internal" if "GITHUB_ACTIONS" in os.environ else "localhost"
    instances = 2
    settings = [
        {
            "host": host,
            "port": 8080 + instance_num,
        }
        for instance_num in range(instances)
    ]
    return settings


def redis_cluster_settings():
    """Return a list of dict of settings for connecting to redis cluster.

    Will return the correct settings, depending on which of the environments it
    is running in. It attempts to set variables in the following order, where
    later environments override earlier ones.

        1. Local
        2. Github Actions
    """

    host = "host.docker.internal" if "GITHUB_ACTIONS" in os.environ else "localhost"
    instances = 1
    base_port = 6379

    settings = [
        {
            "host": host,
            "port": base_port + instance_num,
        }
        for instance_num in range(instances)
    ]
    return settings


def memcached_settings():
    """Return a list of dict of settings for connecting to memcached.

    Will return the correct settings, depending on which of the environments it
    is running in. It attempts to set variables in the following order, where
    later environments override earlier ones.

        1. Local
        2. Github Actions
    """

    host = "host.docker.internal" if "GITHUB_ACTIONS" in os.environ else "127.0.0.1"
    instances = 2
    settings = [
        {
            "host": host,
            "port": 8080 + instance_num,
            "namespace": str(os.getpid()),
        }
        for instance_num in range(instances)
    ]
    return settings


def mongodb_settings():
    """Return a list of dict of settings for connecting to mongodb.

    Will return the correct settings, depending on which of the environments it
    is running in. It attempts to set variables in the following order, where
    later environments override earlier ones.

        1. Local
        2. Github Actions
    """

    host = "host.docker.internal" if "GITHUB_ACTIONS" in os.environ else "127.0.0.1"
    instances = 2
    settings = [
        {"host": host, "port": 8080 + instance_num, "collection": "mongodb_collection_" + str(os.getpid())}
        for instance_num in range(instances)
    ]
    return settings


def elasticsearch_settings():
    """Return a list of dict of settings for connecting to elasticsearch.

    Will return the correct settings, depending on which of the environments it
    is running in. It attempts to set variables in the following order, where
    later environments override earlier ones.

        1. Local
        2. Github Actions
    """

    host = "host.docker.internal" if "GITHUB_ACTIONS" in os.environ else "localhost"
    instances = 2
    settings = [
        {
            "host": host,
            "port": str(8080 + instance_num),
            "namespace": str(os.getpid()),
        }
        for instance_num in range(instances)
    ]
    return settings


def solr_settings():
    """Return a list of dict of settings for connecting to solr.

    Will return the correct settings, depending on which of the environments it
    is running in. It attempts to set variables in the following order, where
    later environments override earlier ones.

        1. Local
        2. Github Actions
    """

    host = "host.docker.internal" if "GITHUB_ACTIONS" in os.environ else "127.0.0.1"
    instances = 2
    settings = [
        {
            "host": host,
            "port": 8080 + instance_num,
            "namespace": str(os.getpid()),
        }
        for instance_num in range(instances)
    ]
    return settings


def rabbitmq_settings():
    """Return a list of dict of settings for connecting to rabbitmq.

    Will return the correct settings, depending on which of the environments it
    is running in. It attempts to set variables in the following order, where
    later environments override earlier ones.

        1. Local
        2. Github Actions
    """

    host = "host.docker.internal" if "GITHUB_ACTIONS" in os.environ else "localhost"
    instances = 1
    settings = [
        {
            "host": host,
            "port": 5672 + instance_num,
        }
        for instance_num in range(instances)
    ]
    return settings


def kafka_settings():
    """Return a list of dict of settings for connecting to kafka.

    Will return the correct settings, depending on which of the environments it
    is running in. It attempts to set variables in the following order, where
    later environments override earlier ones.

        1. Local
        2. Github Actions
    """

    host = "host.docker.internal" if "GITHUB_ACTIONS" in os.environ else "127.0.0.1"
    base_port = 8082 if "GITHUB_ACTIONS" in os.environ else 8080
    instances = 2
    settings = [
        {
            "host": host,
            "port": base_port + instance_num,
        }
        for instance_num in range(instances)
    ]
    return settings


def gearman_settings():
    """Return a list of dict of settings for connecting to kafka.

    Will return the correct settings, depending on which of the environments it
    is running in. It attempts to set variables in the following order, where
    later environments override earlier ones.

        1. Local
        2. Github Actions
    """

    host = "host.docker.internal" if "GITHUB_ACTIONS" in os.environ else "localhost"
    instances = 1
    settings = [
        {
            "host": host,
            "port": 8080 + instance_num,
        }
        for instance_num in range(instances)
    ]
    return settings
