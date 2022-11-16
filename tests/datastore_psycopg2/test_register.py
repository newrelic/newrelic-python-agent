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
import psycopg2
import psycopg2.extras

from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from utils import DB_SETTINGS

from newrelic.api.background_task import background_task


@validate_transaction_metrics('test_register:test_register_json',
        background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
def test_register_json():
    with psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port']) as connection:

        cursor = connection.cursor()

        psycopg2.extras.register_json(connection, loads=lambda x: x)
        psycopg2.extras.register_json(cursor, loads=lambda x: x)

@validate_transaction_metrics('test_register:test_register_range',
        background_task=True)
@validate_transaction_errors(errors=[])
@background_task()
def test_register_range():
    with psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port']) as connection:

        type_name = "floatrange_" + str(os.getpid())

        create_sql = ('CREATE TYPE %s AS RANGE (' % type_name +
                      'subtype = float8,'
                      'subtype_diff = float8mi)')

        cursor = connection.cursor()

        cursor.execute("DROP TYPE if exists %s" % type_name)
        cursor.execute(create_sql)

        psycopg2.extras.register_range(type_name,
                psycopg2.extras.NumericRange, connection)

        cursor.execute("DROP TYPE if exists %s" % type_name)
        cursor.execute(create_sql)

        psycopg2.extras.register_range(type_name,
                psycopg2.extras.NumericRange, cursor)

        cursor.execute("DROP TYPE if exists %s" % type_name)
