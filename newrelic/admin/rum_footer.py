from __future__ import print_function

from newrelic.admin import command, usage

@command('rum-footer', 'config_file path [log_file]',
"""Prints out the RUM footer for a resource with the supplied path.
The application name as specified in the agent configuration file is
used.""", hidden=True)
def rum_footer(args):
    import os
    import sys
    import logging
    import time

    if len(args) < 2:
        usage('rum-footer')
        sys.exit(1)

    from newrelic.agent import initialize, register_application

    if len(args) >= 3:
        log_file = args[2]
    else:
        log_file = '/tmp/python-agent-test.log'

    log_level = logging.DEBUG

    try:
        os.unlink(log_file)
    except Exception:
        pass

    config_file = args[0]
    environment = os.environ.get('NEW_RELIC_ENVIRONMENT')

    if config_file == '-':
        config_file = os.environ.get('NEW_RELIC_CONFIG_FILE')

    initialize(config_file, environment, ignore_errors=False,
            log_file=log_file, log_level=log_level)

    _timeout = 30.0

    _start = time.time()
    _application = register_application(timeout=_timeout)
    _end = time.time()

    _duration = _end - _start

    _logger = logging.getLogger(__name__)

    if not _application.active:
        _logger.error('Unable to register application for test, '
            'connection could not be established within %s seconds.',
            _timeout)
        return

    from newrelic.api.web_transaction import (obfuscate,
            _rum_footer_long_fragment as footer)

    metric = 'WebTransaction/Static/%s' % args[1]

    name = obfuscate(metric, _application.settings.license_key[:13])

    print(str(footer % (_application.settings.episodes_file,
        _application.settings.beacon, _application.settings.browser_key,
        _application.settings.application_id, name, 0, 0)))
