import pwd
import os


def _e(key, default):
    return os.environ.get(key, default)

USER = pwd.getpwuid(os.getuid()).pw_name

def postgresql_settings():
    """Return a dict of settings for connecting to postgresql.

    Will return the correct settings, depending on which of the
    three environments it is running in. It attempts to set variables
    in the following order, where later environments override earlier
    ones.

        1. Local
        2. Tddium
        3. Test Docker container

    """

    settings = {}

    # Use local defaults, if TDDIUM vars aren't present.

    settings['name'] = _e('TDDIUM_DB_PG_NAME', USER)
    settings['user'] = _e('TDDIUM_DB_PG_USER', USER)
    settings['password'] = _e('TDDIUM_DB_PG_PASSWORD', '')
    settings['host'] = _e('TDDIUM_DB_PG_HOST', 'localhost')
    settings['port'] = int(_e('TDDIUM_DB_PG_PORT', '5432'))

    # Look for env vars in test docker container.

    settings['name'] = _e('PACKNSEND_DB_USER', settings['name'])
    settings['user'] = _e('PACKNSEND_DB_USER', settings['user'])
    settings['password'] = _e('PACKNSEND_DB_USER', settings['password'])
    settings['host'] = _e('POSTGRESQL_PORT_5432_TCP_ADDR',
            settings['host'])
    settings['port'] = int(_e('POSTGRESQL_PORT_5432_TCP_PORT',
            settings['port']))

    return settings

def postgresql_multiple_settings():
    """Return a list of dicts of settings for connecting to postgresql.

    Will return the correct settings, depending on which of the
    three environments it is running in. It attempts to set variables
    in the following order, where later environments override earlier
    ones.

        1. Local
        2. Tddium
        3. Test Docker container
        4. Test docker-compose container

    """

    db1 = postgresql_settings()

    # When not using docker-compose, return immediately

    if not _e('COMPOSE', False):
        return [db1]

    db2 = db1.copy()

    # Update hostnames based on docker-compose env vars

    db1['host'] = _e('COMPOSE_POSTGRESQL_HOST_1', db1['host'])
    db2['host'] = _e('COMPOSE_POSTGRESQL_HOST_2', db2['host'])

    return [db1, db2]

def mysql_settings():
    """Return a dict of settings for connecting to mysql.

    Will return the correct settings, depending on which of the
    three environments it is running in. It attempts to set variables
    in the following order, where later environments override earlier
    ones.

        1. Local
        2. Tddium
        3. Test Docker container

    """

    settings = {}

    # Use local defaults, if TDDIUM vars aren't present.

    settings['name'] = _e('TDDIUM_DB_MYSQL_NAME', USER)
    settings['user'] = _e('TDDIUM_DB_MYSQL_USER', USER)
    settings['password'] = _e('TDDIUM_DB_MYSQL_PASSWORD', '')
    settings['host'] = _e('TDDIUM_DB_MYSQL_HOST', 'localhost')
    settings['port'] = int(_e('TDDIUM_DB_MYSQL_PORT', '3306'))

    # Look for env vars in test docker container.

    settings['name'] = _e('PACKNSEND_DB_USER', settings['name'])
    settings['user'] = _e('PACKNSEND_DB_USER', settings['user'])
    settings['password'] = _e('PACKNSEND_DB_USER', settings['password'])
    settings['host'] = _e('MYSQL_PORT_3306_TCP_ADDR', settings['host'])
    settings['port'] = int(_e('MYSQL_PORT_3306_TCP_PORT',
            settings['port']))

    return settings

def mysql_multiple_settings():
    """Return a list of dicts of settings for connecting to mysql.

    Will return the correct settings, depending on which of the
    four environments it is running in. It attempts to set variables
    in the following order, where later environments override earlier
    ones.

        1. Local
        2. Tddium
        3. Test Docker container
        4. Test docker-compose container

    """

    db1 = mysql_settings()

    # When not using docker-compose, return immediately

    if not _e('COMPOSE', False):
        return [db1]

    db2 = db1.copy()

    # Update hostnames based on docker-compose env vars

    db1['host'] = _e('COMPOSE_MYSQL_HOST_1', db1['host'])
    db2['host'] = _e('COMPOSE_MYSQL_HOST_2', db2['host'])

    return [db1, db2]

def mongodb_settings():
    """Return (host, port) tuple to connect to mongodb."""

    # Use local defaults, if TDDIUM vars aren't present.

    host = 'localhost'  # TDDIUM sets up mongodb on each test worker.
    port = int(os.environ.get('TDDIUM_MONGOID_PORT', '27017'))

    # Look for env vars in test docker container.

    host = os.environ.get('MONGODB_PORT_27017_TCP_ADDR', host)
    port = int(os.environ.get('MONGODB_PORT_27017_TCP_PORT', port))

    return (host, port)

def elasticsearch_settings():
    """Return (host, port) tuple to connect to elasticsearch."""

    # Use local defaults, if TDDIUM vars aren't present.

    host = os.environ.get('TDDIUM_ES_HOST', 'localhost')
    port = int(os.environ.get('TDDIUM_ES_HTTP_PORT', '9200'))

    # Look for env vars in test docker container.

    host = os.environ.get('ELASTICSEARCH_PORT_9200_TCP_ADDR', host)
    port = int(os.environ.get('ELASTICSEARCH_PORT_9200_TCP_PORT', port))

    return (host, port)

def solr_settings():
    """Return (host, port) tuple to connect to solr."""

    # Use local defaults, if TDDIUM vars aren't present.

    host = os.environ.get('TDDIUM_SOLR_HOST', 'localhost')
    port = int(os.environ.get('TDDIUM_SOLR_PORT', '8983'))

    # Look for env vars in test docker container.

    host = os.environ.get('SOLR4_PORT_8983_TCP_ADDR', host)
    port = int(os.environ.get('SOLR4_PORT_8983_TCP_PORT', port))

    return (host, port)

def redis_settings():
    """Return a dict of settings for connecting to redis.

    Will return the correct settings, depending on which of the
    three environments it is running in. It attempts to set variables
    in the following order, where later environments override earlier
    ones.

        1. Local
        2. Tddium
        3. Test Docker container

    """
    settings = {}

    # Use local defaults, if TDDIUM vars aren't present.

    settings['host'] = os.environ.get('TDIUM_REDIS_HOST', 'localhost')
    settings['port'] = int(os.environ.get('TDIUM_REDIS_PORT', '6379'))

    # Look for env vars in test docker container.

    settings['host'] = _e('REDIS_PORT_6379_TCP_ADDR', settings['host'])
    settings['port'] = int(_e('REDIS_PORT_6379_TCP_PORT', settings['port']))

    return settings

def redis_multiple_settings():
    """Return a list of dicts of settings for connecting to redis.

    Will return the correct settings, depending on which of the
    three environments it is running in. It attempts to set variables
    in the following order, where later environments override earlier
    ones.

        1. Local
        2. Tddium
        3. Test Docker container
        4. Test docker-compose container

    """

    db1 = redis_settings()

    # When not using docker-compose, return immediately

    if not _e('COMPOSE', False):
        return [db1]

    db2 = db1.copy()

    # Update hostnames based on docker-compose env vars

    db1['host'] = _e('COMPOSE_REDIS_HOST_1', db1['host'])
    db2['host'] = _e('COMPOSE_REDIS_HOST_2', db2['host'])

    return [db1, db2]
