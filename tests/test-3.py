# This test is validating whether agent code closes off a trace
# automatically when parent web transaction is closed off
# without the trace being closed off.

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

environ = { "REQUEST_URI": "/test-3" }

for i in range(1000):
    with application.web_transaction(environ) as transaction:
        time.sleep(random.random()/10.0)
        trace = transaction.function_trace('function')
        trace.__enter__()
        time.sleep(random.random()/10.0)

_newrelic.harvest()

print "finished"
