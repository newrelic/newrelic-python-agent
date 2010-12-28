# This test is see what happens when web transactions are nested.

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

environ1 = { "REQUEST_URI": "/test-5/1" }
environ2 = { "REQUEST_URI": "/test-5/2" }

with application.web_transaction(environ1):
    time.sleep(1.0)
    with application.web_transaction(environ2):
        time.sleep(1.0)

_newrelic.harvest()

print "finished"
