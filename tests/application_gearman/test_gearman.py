from __future__ import print_function

import gearman
import threading
import sys
import time

from newrelic.agent import (background_task, record_exception,
        add_custom_parameter)

worker_thread = None
worker_event = threading.Event()

gm_client = None

class GearmanWorker(gearman.GearmanWorker):

    def after_poll(self, any_activity):
        return not worker_event.isSet()

def setup_module(module):
    global worker_thread

    gm_worker = GearmanWorker(['localhost:4730','localhost:4731'])

    def task_listener_reverse(gearman_worker, gearman_job):
        return ''.join(reversed(gearman_job.data))

    def task_listener_exception(gearman_worker, gearman_job):
        raise RuntimeError('error')

    gm_worker.set_client_id('gearman-instrumentation-tests')
    gm_worker.register_task('reverse', task_listener_reverse)
    gm_worker.register_task('exception', task_listener_exception)

    def startup():
        gm_worker.work(poll_timeout=1.0)

    worker_thread = threading.Thread(target=startup)
    worker_thread.start()

    global gm_client

    gm_client = gearman.GearmanClient(['localhost:4730','localhost:4731'])

def teardown_module(module):
    worker_event.set()
    worker_thread.join()

@background_task()
def test_successful():
    completed_job_request = gm_client.submit_job('reverse', 'data')
    assert completed_job_request.complete

@background_task()
def test_exception():
    completed_job_request = gm_client.submit_job('exception', 'data')
    assert completed_job_request.complete
