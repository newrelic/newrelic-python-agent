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

environ = { "REQUEST_URI": "/test-1" }

for i in range(1000):
    with application.web_transaction(environ) as transaction:
        time.sleep(random.random()/5.0)

_newrelic.harvest()

print "finished"
