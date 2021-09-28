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

from __future__ import print_function

import os
import threading

import gearman

from newrelic.api.background_task import background_task

worker_thread = None
worker_event = threading.Event()

gm_client = None

GEARMAND_HOST = os.environ.get("GEARMAND_PORT_4730_TCP_ADDR", "localhost")
GEARMAND_PORT = os.environ.get("GEARMAND_PORT_4730_TCP_PORT", "4730")

GEARMAND_ADDR = "%s:%s" % (GEARMAND_HOST, GEARMAND_PORT)


class GearmanWorker(gearman.GearmanWorker):
    def after_poll(self, any_activity):
        try:
            worker_event_set = worker_event.is_set()
        except TypeError:
            worker_event_set = worker_event.isSet()

        return not worker_event_set


def setup_module(module):
    global worker_thread

    gm_worker = GearmanWorker([GEARMAND_ADDR])

    def task_listener_reverse(gearman_worker, gearman_job):
        return "".join(reversed(gearman_job.data))

    def task_listener_exception(gearman_worker, gearman_job):
        raise RuntimeError("error")

    gm_worker.set_client_id("gearman-instrumentation-tests")
    gm_worker.register_task("reverse", task_listener_reverse)
    gm_worker.register_task("exception", task_listener_exception)

    def startup():
        gm_worker.work(poll_timeout=1.0)

    worker_thread = threading.Thread(target=startup)
    worker_thread.start()

    global gm_client

    gm_client = gearman.GearmanClient([GEARMAND_ADDR])


def teardown_module(module):
    worker_event.set()
    worker_thread.join()


@background_task()
def test_successful():
    completed_job_request = gm_client.submit_job("reverse", "data")
    assert completed_job_request.complete


@background_task()
def test_exception():
    completed_job_request = gm_client.submit_job("exception", "data")
    assert completed_job_request.complete
