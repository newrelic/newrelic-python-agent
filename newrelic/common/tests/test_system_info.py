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


if __name__ == '__main__':
    unittest.main()
