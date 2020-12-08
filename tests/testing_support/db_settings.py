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
