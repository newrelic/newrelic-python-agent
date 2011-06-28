import sys
import os

# Import all the magic into this namespace.

from _newrelic import *
from newrelic.profile import *

# If the configuration file hasn't been read in previously by
# the newrelic.config module having being imported first and
# load_configuration() called explicitly, or indirectly via the
# application factory, then attempt it here. We don't supply any
# arguments so will fallback to getting configuration file name
# and the name of deployment environment type from the process
# environment variables.

import newrelic.config

if not newrelic.config.config_file:
    newrelic.config.load_configuration()

import newrelic.patch

newrelic.patch.setup_instrumentation()
