# This test is check whether basic web transaction and traces work.

import sys
import os
import time
import random

import _newrelic

print "starting"

settings = _newrelic.Settings()

settings.logfile = "/tmp/newrelic-agent.log"
settings.loglevel = _newrelic.LOG_VERBOSEDEBUG

application = _newrelic.Application("Tests")

_newrelic.harvest()

for i in range(200):
    environ = { "REQUEST_URI": "/test-1" }
    ts= int((time.time()-(random.random()/5.0)) * 1000000)
    environ["HTTP_X_NEWRELIC_QUEUE_START"] = "t=%d" % ts
    with application.web_transaction(environ) as transaction:
        time.sleep(random.random()/5.0)
        with transaction.function_trace("function"):
            time.sleep(random.random()/5.0)
        with transaction.database_trace("select * from cat"):
            time.sleep(random.random()/5.0)
        with transaction.external_trace("http://www.newrelic.com/"):
            time.sleep(random.random()/5.0)
        with transaction.memcache_trace("data"):
            time.sleep(random.random()/5.0)
        time.sleep(random.random()/5.0)

_newrelic.harvest()

print "finished"
