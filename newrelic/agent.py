import sys
import os

from _newrelic import *
from newrelic.profile import *

import newrelic.config
import newrelic.patch

# If the configuration file hasn't been read in previously by
# the newrelic.config module having being imported first and
# load_configuration() called explicitly, or indirectly via the
# application factory, then attempt it here. We don't supply any
# arguments so will fallback to getting configuration file name
# and the name of deployment environment type from the process
# environment variables.

if not newrelic.config.config_file:
    newrelic.config.load_configuration()

# Setup all the instrumentation hooks for builtin defaults and
# what has also been defined within the configuration file.

newrelic.patch.setup_instrumentation()
