import sys
import os
import time
import random

import newrelic

print "starting"

application = newrelic.Application("Django")

for i in range(1000):
  with application.web_transaction() as transaction:
    time.sleep(random.random()/5.0)

application = None

print "finished"
