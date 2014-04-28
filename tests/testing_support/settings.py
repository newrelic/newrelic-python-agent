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
