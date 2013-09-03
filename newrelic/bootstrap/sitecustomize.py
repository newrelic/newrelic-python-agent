from __future__ import print_function

import os
import sys

# First see if the user had defined any sitecustomize.py file which are
# are overriding. If they are, then load it so it is still executed.

site_customize = os.environ.get('NEW_RELIC_SITE_CUSTOMIZE')

if site_customize:
    import imp

    if site_customize.endswith('.py'):
        imp.load_source('_newrelic_sitecustomize', site_customize)
    elif site_customize.endswith('.pyc') or site_customize.endswith('.pyo'):
        imp.load_compiled('_newrelic_sitecustomize', site_customize)

# When installed as egg with buildout, the root directory for packages
# is not listed in sys.path and scripts instead set after Python has
# started up. This will cause importing of 'newrelic' module to fail.
# What we do is see if the root directory where package is held is in
# sys.path and if not insert it. For good measure we remove it after
# having import 'newrelic' module to reduce chance that will cause any
# issues. If it is a buildout created script, it will replace the whole
# sys.path again later anyway.

boot_directory = os.path.dirname(__file__)
root_directory = os.path.dirname(os.path.dirname(boot_directory))

if root_directory not in sys.path:
    sys.path.insert(0, root_directory)

import newrelic.agent

try:
    del sys.path[sys.path.index(root_directory)]
except Exception:
    pass

license_key = os.environ.get('NEW_RELIC_LICENSE_KEY', None)

config_file = os.environ.get('NEW_RELIC_CONFIG_FILE', None)
environment = os.environ.get('NEW_RELIC_ENVIRONMENT', None)

debug_startup = os.environ.get('NEW_RELIC_STARTUP_DEBUG',
        'off').lower() in ('on', 'true', '1')

if debug_startup:
    import time

    def _log(text, *args):
        text = text % args
        print('NEWRELIC: %s (%d) - %s' % (time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime()),
                os.getpid(), text))

    _log('New Relic Bootstrap (%s)', newrelic.version)

    _log('working_directory = %r', os.getcwd())

    for name in sorted(os.environ.keys()):
        if name.startswith('NEW_RELIC_') or name.startswith('PYTHON'):
            _log('%s = %r', name, os.environ.get(name))

    _log('root_directory = %r', root_directory)
    _log('boot_directory = %r', boot_directory)

# We skip agent initialisation if neither the license key or config file
# environment variables are set. We do this as some people like to use a
# common startup script which always uses the wrapper script, and which
# controls whether the agent is actually run based on the presence of
# the environment variables.

if license_key or config_file:
    newrelic.agent.initialize(config_file, environment)
