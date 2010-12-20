# This test checks whether WSGI middleware wrapper works.

import sys
import os
import time
import random

import newrelic

print "starting"

newrelic.settings.logfile = "/tmp/newrelic-agent.log"
newrelic.settings.loglevel = newrelic.LOG_VERBOSEDEBUG

@newrelic.application_monitor("Tests")
def handler(environ, start_response):
    time.sleep(random.random()/5.0)

environ = { "REQUEST_URI": "/test-2" }

for i in range(1000):
    handler(environ, None).close()

print "finished"
