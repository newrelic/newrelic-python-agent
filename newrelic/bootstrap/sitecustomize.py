import os

import newrelic.agent

config_file = os.environ.get('NEW_RELIC_CONFIG_FILE', None)
environment = os.environ.get('NEW_RELIC_ENVIRONMENT', None)

newrelic.agent.initialize(config_file, environment)
