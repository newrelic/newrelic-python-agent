import os

from _newrelic import *

from newrelic.config import *
from newrelic.profile import *

# Setting from environment variables is only provided for backward
# compatibity with early Python agent BETA versions. This will be
# removed prior to general release.

_config_file = os.environ.get('NEWRELIC_CONFIG_FILE', None)
_environment = os.environ.get('NEWRELIC_ENVIRONMENT', None)

if _config_file:
    initialize(_config_file, _environment)
