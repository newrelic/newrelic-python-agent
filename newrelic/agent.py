import os

import newrelic.api.web_transaction
import newrelic.api.background_task

import newrelic.config

initialize = newrelic.config.initialize

wsgi_application = newrelic.api.web_transaction.wsgi_application
background_task = newrelic.api.background_task.background_task
