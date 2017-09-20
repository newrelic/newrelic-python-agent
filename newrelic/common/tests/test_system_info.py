import os
import pytest
import socket
import unittest

from newrelic.common import system_info


class TestGetHostName(unittest.TestCase):

    def setUp(self):
        self.original_socket_gethostname = socket.gethostname
        self.original_cached_hostname = system_info._nr_cached_hostname

        socket.gethostname = self._mock_gethostname_1
        system_info._nr_cached_hostname = None

    def tearDown(self):
        socket.gethostname = self.original_socket_gethostname
        system_info._nr_cached_hostname = self.original_cached_hostname

    def _mock_gethostname_1(self):
        return 'mock-hostname-1'

    def _mock_gethostname_2(self):
        return 'mock-hostname-2'

    def test_gethostname_initial_value(self):
        self.assertEqual(system_info._nr_cached_hostname, None)

    def test_gethostname_first_access(self):
        hostname = system_info.gethostname()
        self.assertEqual(hostname, 'mock-hostname-1')

    def test_gethostname_consecutive_access(self):
        hostname_1 = system_info.gethostname()
        hostname_2 = system_info.gethostname()
        self.assertEqual(hostname_1, hostname_2)

    def test_gethostname_returns_cached_value(self):
        hostname_1 = system_info.gethostname()

        # Monkeypatch socket.gethostname again.

        socket.gethostname = self._mock_gethostname_2
        self.assertEqual(socket.gethostname(), 'mock-hostname-2')

        # If system_info.gethostname() calls socket.gethostname()
        # instead of returning cached value, then this assert
        # will fail.

        hostname_2 = system_info.gethostname()
        self.assertEqual(hostname_1, hostname_2)

    def test_gethostname_returns_dyno(self):
        os.environ['DYNO'] = 'dynosaurus'
        hostname = system_info.gethostname(use_dyno_names=True)

        self.assertEqual(hostname, 'dynosaurus')

    def test_gethostname_ignores_dyno_when_disabled(self):
        os.environ['DYNO'] = 'dynosaurus'
        hostname = system_info.gethostname(use_dyno_names=False)

        self.assertEqual(hostname, 'mock-hostname-1')

    def test_gethostname_dyno_prefixes_are_collapsed(self):
        os.environ['DYNO'] = 'prefix.dynosaurus'
        hostname = system_info.gethostname(use_dyno_names=True,
                dyno_shorten_prefixes=['prefix'])

        self.assertEqual(hostname, 'prefix.*')

    def test_gethostname_dyno_only_shortens_on_prefix_match(self):
        os.environ['DYNO'] = 'dynosaurus'
        hostname = system_info.gethostname(use_dyno_names=True,
                dyno_shorten_prefixes=['meow'])
        self.assertEqual(hostname, 'dynosaurus')

    def test_gethostname_prefixes_allow_csv(self):
        os.environ['DYNO'] = 'dynosaurus.1'
        hostname = system_info.gethostname(use_dyno_names=True,
                dyno_shorten_prefixes=['rex', 'dynosaurus'])
        self.assertEqual(hostname, 'dynosaurus.*')

    def test_gethostname_prefix_empty_string(self):
        os.environ['DYNO'] = 'dynosaurus.1'
        hostname = system_info.gethostname(use_dyno_names=True,
                dyno_shorten_prefixes=[''])
        self.assertEqual(hostname, 'dynosaurus.1')

    def test_gethostname_unsupported_object(self):
        os.environ['DYNO'] = 'dynosaurus.1'

        with pytest.raises(TypeError):
            hostname = system_info.gethostname(use_dyno_names=True,
                    dyno_shorten_prefixes=[{'meow': 'wruff'}])


if __name__ == '__main__':
    unittest.main()
