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

from celery import Celery, Task, shared_task

from newrelic.api.transaction import current_transaction

app = Celery(
    "tasks",
    broker_url="memory://",
    result_backend="cache+memory://",
    worker_hijack_root_logger=False,
    pool="solo",
    broker_heartbeat=0,
)

class CustomCeleryTaskWithSuper(Task):
    def __call__(self, *args, **kwargs):
        transaction = current_transaction()
        if transaction:
            transaction.add_custom_attribute("custom_task_attribute", "Called with super")
        return super().__call__(*args, **kwargs)

class CustomCeleryTaskWithRun(Task):
    def __call__(self, *args, **kwargs):
        transaction = current_transaction()
        if transaction:
            transaction.add_custom_attribute("custom_task_attribute", "Called with run")
        return self.run(*args, **kwargs)


@app.task
def add(x, y):
    return x + y


@app.task(base=CustomCeleryTaskWithSuper)
def add_with_super(x, y):
    return x + y


@app.task(base=CustomCeleryTaskWithRun)
def add_with_run(x, y):
    return x + y


@app.task
def tsum(nums):
    return sum(nums)


@app.task
def nested_add(x, y):
    return add(x, y)


@shared_task
def shared_task_add(x, y):
    return x + y
