import unittest
import time

from newrelic.common.stopwatch import start_timer

class TestStopWatch(unittest.TestCase):

    def test_stopwatch_timer(self):
        timer = start_timer()

        time_started_1 = timer.time_started()

        self.assertTrue(time_started_1 >= 0)

        checkpoint_1 = timer.elapsed_time()
        checkpoint_2 = timer.elapsed_time()

        self.assertTrue(checkpoint_1 >= 0)
        self.assertTrue(checkpoint_2 >= 0)

        self.assertTrue(checkpoint_2 >= checkpoint_1)

        elapsed_time_1 = timer.stop_timer()
        elapsed_time_2 = timer.stop_timer()

        self.assertTrue(elapsed_time_1 >= 0)
        self.assertTrue(elapsed_time_1 == elapsed_time_2)

        elapsed_time_3 = timer.restart_timer()

        self.assertTrue(elapsed_time_1 == elapsed_time_3)

        time_started_2 = timer.time_started()

        self.assertTrue(time_started_2 >= time_started_1)

if __name__ == '__main__':
    unittest.main()
