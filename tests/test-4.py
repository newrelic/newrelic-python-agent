# This test checks adding of error information.

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
time.sleep(5.0)

environ = { "REQUEST_URI": "/test-4" }
ts= int((time.time()-(random.random()/5.0)) * 1000000)
environ["HTTP_X_NEWRELIC_QUEUE_START"] = "t=%d" % ts

with application.web_transaction(environ) as transaction:
    transaction.runtime_error("%s" % time.time())
    time.sleep(5.0)

_newrelic.harvest()

print "finished"
