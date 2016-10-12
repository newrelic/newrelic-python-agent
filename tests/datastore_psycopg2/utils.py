import re

import psycopg2

from testing_support.settings import postgresql_multiple_settings


def _to_int(version_str):
    m = re.match(r'\d+', version_str)
    return int(m.group(0)) if m else 0

def version2tuple(version_str, parts_count=2):
    """Convert version, even if it contains non-numeric chars.

    >>> version2tuple('9.4rc1.1')
    (9, 4)

    """

    parts = version_str.split('.')[:parts_count]
    return tuple(map(_to_int, parts))

def postgresql_version():
    connection = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])

    try:
        cursor = connection.cursor()
        cursor.execute("""SELECT setting from pg_settings where name=%s""",
                ('server_version',))
        return cursor.fetchone()

    finally:
        connection.close()

DB_MULTIPLE_SETTINGS = postgresql_multiple_settings()
DB_SETTINGS = DB_MULTIPLE_SETTINGS[0]
POSTGRESQL_VERSION = version2tuple(postgresql_version()[0])
PSYCOPG2_VERSION = version2tuple(psycopg2.__version__, parts_count=3)
