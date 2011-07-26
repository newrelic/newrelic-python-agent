import os

from _newrelic import *

# To allow for transition while

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

if _agent_mode in ('ungud', 'julunggul'):
    from newrelic.core.object_wrapper import *
    from newrelic.core.trace_wrapper import *
    from newrelic.core.external_trace import *
    from newrelic.core.function_trace import *
    from newrelic.core.database_trace import *
    from newrelic.core.memcache_trace import *

from newrelic.config import *
from newrelic.profile import *

# Setting from environment variables is only provided for backward
# compatibity with early Python agent BETA versions. This will be
# removed prior to general release.

_config_file = os.environ.get('NEWRELIC_CONFIG_FILE', None)
_environment = os.environ.get('NEWRELIC_ENVIRONMENT', None)

if _config_file:
    initialize(_config_file, _environment)
