from __future__ import print_function

import sys
import unittest

import newrelic.core.environment

class TestEnvironment(unittest.TestCase):

    def test_create(self):
        env = newrelic.core.environment.environment_settings()
        print(env)

if __name__ == "__main__":
    unittest.main()
