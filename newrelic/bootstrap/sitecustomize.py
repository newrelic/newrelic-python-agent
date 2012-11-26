import os
import sys

# When installed as egg with buildout, the root directory for packages
# is not listed in sys.path and scripts instead set after Python has
# started up. This will cause importing of 'newrelic' module to fail.
# What we do is see if the root directory where package is held is in
# sys.path and if not insert it. For good measure we remove it after
# having import 'newrelic' module to reduce chance that will cause any
# issues. If it is a buildout created script, it will replace the whole
# sys.path again later anyway.

here = os.path.dirname(__file__)
root = os.path.dirname(os.path.dirname(here))

if root not in sys.path:
    sys.path.insert(0, root)

import newrelic.agent

try:
    del sys.path[sys.path.index(root)]
except:
    pass

license_key = os.environ.get('NEW_RELIC_LICENSE_KEY', None)

config_file = os.environ.get('NEW_RELIC_CONFIG_FILE', None)
environment = os.environ.get('NEW_RELIC_ENVIRONMENT', None)

# We skip agent initialisation if neither the license key or config file
# environment variables are set. We do this as some people like to use a
# common startup script which always uses the wrapper script, and which
# controls whether the agent is actually run based on the presence of
# the environment variables.

if license_key or config_file:
    newrelic.agent.initialize(config_file, environment)
