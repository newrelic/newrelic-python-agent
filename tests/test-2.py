# This test checks whether WSGI middleware wrapper works.

import sys
import os
import time
import random

import newrelic

print "starting"

newrelic.settings.logfile = "/tmp/newrelic-agent.log"
newrelic.settings.loglevel = newrelic.LOG_VERBOSEDEBUG

@newrelic.web_transaction("Tests")
def handler(environ, start_response):
    time.sleep(random.random()/5.0)

for i in range(1000):
    environ = { "REQUEST_URI": "/test-2" }
    ts= int((time.time()-(random.random()/5.0)) * 1000000)
    environ["HTTP_X_NEWRELIC_QUEUE_START"] = "t=%d" % ts
    handler(environ, None).close()

print "finished"
