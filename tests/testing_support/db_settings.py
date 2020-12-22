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

import pwd
import os

USER = pwd.getpwuid(os.getuid()).pw_name


def postgresql_settings():
    """Return a list of dict of settings for connecting to postgresql.

    Will return the correct settings, depending on which of the environments it
    is running in. It attempts to set variables in the following order, where
    later environments override earlier ones.

        1. Local
        2. Github Actions
    """

    if "GITHUB_ACTIONS" in os.environ:
        instances = 2

        user = password = db = "postgres"
        base_port = 8080
    else:
        instances = 1

        user = db = USER
        password = ""
        base_port = 5432

    settings = [
        {
            "user": user,
            "password": password,
            "name": db,
            "host": "localhost",
            "port": base_port + instance_num,
            "table_name": "postgres_table_" + str(os.getpid()),
        }
        for instance_num in range(instances)
    ]
    return settings


def mysql_settings():
    """Return a list of dict of settings for connecting to postgresql.

    Will return the correct settings, depending on which of the environments it
    is running in. It attempts to set variables in the following order, where
    later environments override earlier ones.

        1. Local
        2. Github Actions
    """

    if "GITHUB_ACTIONS" in os.environ:
        instances = 2

        user = password = db = "python_agent"
        base_port = 8080
    else:
        instances = 1

        user = db = USER
        password = ""
        base_port = 3306

    settings = [
        {
            "user": user,
            "password": password,
            "name": db,
            "host": "127.0.0.1",
            "port": base_port + instance_num,
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

    if "GITHUB_ACTIONS" in os.environ:
        instances = 2
        base_port = 8080
    else:
        instances = 1
        base_port = 6379

    settings = [
        {
            "host": "localhost",
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

    if "GITHUB_ACTIONS" in os.environ:
        instances = 2
        base_port = 8080
    else:
        instances = 1
        base_port = 11211

    settings = [
        {
            "host": "127.0.0.1",
            "port": base_port + instance_num,
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

    if "GITHUB_ACTIONS" in os.environ:
        instances = 2
        base_port = 8080
    else:
        instances = 1
        base_port = 27017

    settings = [
        {
            "host": "127.0.0.1",
            "port": base_port + instance_num,
            "collection": "mongodb_collection_" + str(os.getpid())
        }
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

    if "GITHUB_ACTIONS" in os.environ:
        instances = 2
        base_port = 8080
    else:
        instances = 1
        base_port = 9200

    settings = [
        {
            "host": "localhost",
            "port": str(base_port + instance_num),
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

    if "GITHUB_ACTIONS" in os.environ:
        instances = 2
        base_port = 8080
    else:
        instances = 1
        base_port = 8983

    settings = [
        {
            "host": "127.0.0.1",
            "port": base_port + instance_num,
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

    instances = 1
    base_port = 5672

    settings = [
        {
            "host": "localhost",
            "port": base_port + instance_num,
        }
        for instance_num in range(instances)
    ]
    return settings
