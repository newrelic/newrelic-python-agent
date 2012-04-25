import time
import unittest
import logging

import newrelic.agent

import newrelic.api.settings

import newrelic.core.data_collector

_logger = logging.getLogger('newrelic')

# Hardwire settings for test script rather than agent configuration file
# as is easier to work with in test script. We override transaction and
# database trace thresholds so everything is collected. To the extent
# that the old logging system is still used in the code, possibly
# nothing at this point, anything will end up in log file in same
# directory as this script where name is this files name with '.log'
# appended.

settings = newrelic.api.settings.settings()

settings.host = 'staging-collector.newrelic.com'
settings.port = 80
settings.license_key = '84325f47e9dec80613e262be4236088a9983d501'

settings.app_name = 'Python Agent Test'

settings.log_file = '%s.log' % __file__
settings.log_level = logging.DEBUG

class TransactionTests(unittest.TestCase):

    # Note that you can only have a single test in this file
    # as code makes assumption that test is first to run and
    # nothing has been run before.

    def setUp(self):
        _logger.debug('STARTING - %s' % self._testMethodName)

    def tearDown(self):
        _logger.debug('STOPPING - %s' % self._testMethodName)

    def test_data_collector(self):

        # Initialise higher level instrumentation layers. Not
        # that they will be used in this test for now.

        newrelic.agent.initialize()

        session = newrelic.core.data_collector.create_session(
                settings.app_name, [], {}, {})

        print session.configuration

        metric_data = [[{'name': 'Custom/Test'}, [1,1,1,1,1,1]]]

        now = time.time()

        metric_ids = session.send_metric_data(now-60, now, metric_data)

        print metric_ids

        errors = ((0, "/WebTransaction/Uri/E", 'M', 'T', {}),)

        session.send_errors(errors)

if __name__ == '__main__':
    unittest.main()
