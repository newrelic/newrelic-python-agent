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

from aiomysql.sa import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import Integer, String, Column, Float
from sqlalchemy.schema import CreateTable, DropTable

from testing_support.db_settings import mysql_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_database_trace_inputs import (
    validate_database_trace_inputs,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task

DB_SETTINGS = mysql_settings()[0]
TABLE_NAME = f"datastore_aiomysql_orm_{DB_SETTINGS['namespace']}"
PROCEDURE_NAME = f"hello_{DB_SETTINGS['namespace']}"

HOST = instance_hostname(DB_SETTINGS["host"])
PORT = DB_SETTINGS["port"]


Base = declarative_base()

class ABCModel(Base):
    __tablename__ = TABLE_NAME

    a = Column(Integer, primary_key=True)
    b = Column(Float)
    c = Column(String(100))
    

ABCTable = ABCModel.__table__


async def exercise(engine):
    async with engine.acquire() as conn:
        async with conn.begin():
            await conn.execute(DropTable(ABCTable, if_exists=True))
            await conn.execute(CreateTable(ABCTable))

            input_rows = [(1, 1.0, "1.0"), (2, 2.2, "2.2"), (3, 3.3, "3.3")]
            await conn.execute(ABCTable.insert().values(input_rows))
            cursor = await conn.execute(ABCTable.select())

            rows = []
            async for row in cursor:
                rows.append(row)

            assert rows == input_rows, f"Expected: {input_rows}, Got: {rows}"

            await conn.execute(ABCTable.update().where(ABCTable.columns.a == 1).values((4, 4.0, "4.0")))
            await conn.execute(ABCTable.delete().where(ABCTable.columns.a == 2))


SCOPED_METRICS = [
    ("Function/aiomysql.pool:Pool._acquire", 2),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/select", 1),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/insert", 1),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/update", 1),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/delete", 1),
    ("Datastore/operation/MySQL/drop", 1),
    ("Datastore/operation/MySQL/create", 1),
    ("Datastore/operation/MySQL/commit", 1),
    ("Datastore/operation/MySQL/begin", 1),
]

ROLLUP_METRICS = [
    ("Function/aiomysql.pool:Pool._acquire", 2),
    ("Datastore/all", 10),
    ("Datastore/allOther", 10),
    ("Datastore/MySQL/all", 10),
    ("Datastore/MySQL/allOther", 10),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/select", 1),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/insert", 1),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/update", 1),
    (f"Datastore/statement/MySQL/{TABLE_NAME}/delete", 1),
    ("Datastore/operation/MySQL/select", 1),
    ("Datastore/operation/MySQL/insert", 1),
    ("Datastore/operation/MySQL/update", 1),
    ("Datastore/operation/MySQL/delete", 1),
    ("Datastore/operation/MySQL/drop", 1),
    ("Datastore/operation/MySQL/create", 1),
    ("Datastore/operation/MySQL/commit", 1),
    (f"Datastore/instance/MySQL/{HOST}/{PORT}", 8),
]

@validate_transaction_metrics(
    "test_sqlalchemy:test_execute_via_engine",
    scoped_metrics=SCOPED_METRICS,
    rollup_metrics=ROLLUP_METRICS,
    background_task=True,
)
@validate_database_trace_inputs(sql_parameters_type=dict)
@background_task()
def test_execute_via_engine(loop):
    async def _test():
        engine = await create_engine(
            db=DB_SETTINGS["name"],
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            host=DB_SETTINGS["host"],
            port=DB_SETTINGS["port"],
            autocommit=True,
        )

        async with engine:
            await exercise(engine)

    loop.run_until_complete(_test())
