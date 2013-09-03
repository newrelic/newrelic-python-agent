import time
import unittest

from newrelic.core.agent import agent_instance
from newrelic.core.config import global_settings

class TestCase(unittest.TestCase):

    agent = agent_instance()
    app_name = global_settings().app_name
    application = None

    # Set requires_collector to True in derived test case if the set
    # of test cases requires the collector so as to report data.

    requires_collector = False

    def setUp(self):
        # If set of test cases requires the collector so as to report
        # data, we force registration here, waiting up to 10 seconds.

        if self.requires_collector:
            if self.application is None:
                self.agent.activate_application(self.app_name, timeout=10.0)
                self.application = self.agent.application(self.app_name)

    def tearDown(self):
        # If set of test cases requires the collector so as to report
        # data, we check how long since the start of the current data
        # collection cycle and if we are within 1.1 seconds of the start
        # we add an artificial delay so we don't end up with data being
        # thrown away due to the period of the harvest cycle being too
        # short when data reported.

        if self.requires_collector:
            if self.application is not None:
                current_time = time.time()
                period_start = self.application._period_start
                cycle_duration = current_time - period_start

                if cycle_duration < 1.1:
                    time.sleep(1.1-cycle_duration)
