# This test checks decorators for transaction traces.

import sys
import os
import time
import random

import newrelic

print "starting"

newrelic.settings.logfile = "/tmp/newrelic-agent.log"
newrelic.settings.loglevel = newrelic.LOG_VERBOSEDEBUG

@newrelic.database_trace(1)
def database(period, sql):
    time.sleep(period)

@newrelic.memcache_trace(1)
def memcache(period, snippet):
    time.sleep(period)

@newrelic.external_trace(1)
def external(period, url):
    time.sleep(period)

@newrelic.function_trace("function1")
def function1(period):
    time.sleep(period)
    database(period, "select * from cat")
    memcache(period, "a")
    external(period, "http://localhost")

@newrelic.function_trace()
def function2(period):
    function1(period)
    function1(period)

@newrelic.web_transaction("Tests")
def handler(environ, start_response):
    time.sleep(0.2)
    function1(0.2)
    function2(0.2)
    function1(0.2)
    time.sleep(0.2)

environ = { "REQUEST_URI": "/test-6" }
handler(environ, None).close()

print "finished"
