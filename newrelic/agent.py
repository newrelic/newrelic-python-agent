import os

import newrelic.api.web_transaction
import newrelic.api.background_task

import newrelic.config

initialize = newrelic.config.initialize

wsgi_application = newrelic.api.web_transaction.wsgi_application
background_task = newrelic.api.background_task.background_task

# Setting from environment variables is only provided for backward
# compatibity with early Python agent BETA versions. This will be
# removed prior to general release.

_config_file = os.environ.get('NEWRELIC_CONFIG_FILE', None)
_environment = os.environ.get('NEWRELIC_ENVIRONMENT', None)

if _config_file:
    initialize(_config_file, _environment)
