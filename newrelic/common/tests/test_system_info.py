import pytest
import socket
import unittest

from mock import patch
from newrelic.common import system_info


class MocketSocket(object):
    ip_v4 = None
    error_on_init = False

    def __init__(self, ip_version, socket_type):
        if self.error_on_init:
            1 / 0

    def connect(self, addr):
        pass

    def close(self):
        pass

    def getsockname(self):
        return (self.ip_v4, 0)


class TestGetHostName(unittest.TestCase):

    def setUp(self):
        self.original_socket_gethostname = socket.gethostname
        self.original_socket_getfqdn = socket.getfqdn
        self.original_socket_socket = socket.socket

        self.original_cache_hostname = system_info._nr_cached_hostname
        self.original_cache_fqdn = system_info._nr_cached_fqdn
        self.original_cache_ip_address = system_info._nr_cached_ip_address

        socket.gethostname = self._mock_gethostname_1
        socket.getfqdn = self._mock_getfqdn_1
        socket.socket = MocketSocket
        MocketSocket.ip_v4 = '127.0.0.1'

        system_info._nr_cached_hostname = None
        system_info._nr_cached_fqdn = None
        system_info._nr_cached_ip_address = None

    def tearDown(self):
        socket.gethostname = self.original_socket_gethostname
        socket.getfqdn = self.original_socket_getfqdn
        socket.socket = self.original_socket_socket

        system_info._nr_cached_hostname = self.original_cache_hostname
        system_info._nr_cached_fqdn = self.original_cache_fqdn
        system_info._nr_cached_ip_address = self.original_cache_ip_address

    def _mock_gethostname_1(self):
        return 'mock-hostname-1'

    def _mock_gethostname_2(self):
        return 'mock-hostname-2'

    def _mock_getfqdn_1(self):
        return 'www.mock-hostname-1'

    def _mock_getfqdn_2(self):
        return 'www.mock-hostname-2'

    def test_gethostname_initial_value(self):
        self.assertEqual(system_info._nr_cached_hostname, None)

    def test_gethostname_first_access(self):
        hostname = system_info.gethostname()
        self.assertEqual(hostname, 'mock-hostname-1')

    def test_getfqdn_first_access(self):
        fqdn = system_info.getfqdn()
        self.assertEqual(fqdn, 'www.mock-hostname-1')

    def test_getips_first_access(self):
        ip = system_info.getips()
        self.assertEqual(ip, ['127.0.0.1'])

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

    def test_getfqdn_returns_cached_value(self):
        fqdn_1 = system_info.getfqdn()

        # Monkeypatch socket.getfqdn again.

        socket.getfqdn = self._mock_getfqdn_2
        self.assertEqual(socket.getfqdn(), 'www.mock-hostname-2')

        # If system_info.getfqdn() calls socket.getfqdn()
        # instead of returning cached value, then this assert
        # will fail.

        fqdn_2 = system_info.getfqdn()
        self.assertEqual(fqdn_1, fqdn_2)

    def test_ip_address_returns_cached_value(self):
        ip_1 = system_info.getips()

        # Monkeypatch socket.getaddrinfo again.

        MocketSocket.ip_v4 = None
        s = socket.socket(socket.AF_INET, None)
        s.connect(('1.1.1.1', 1))
        self.assertEqual(s.getsockname(), (None, 0))

        # If system_info.getips() calls socket.getaddrinfo()
        # instead of returning cached value, then this assert
        # will fail.

        ip_2 = system_info.getips()
        self.assertEqual(ip_1, ip_2)

    def test_getips_catches_error_on_init(self):
        MocketSocket.error_on_init = True
        try:
            self.assertEqual([], system_info.getips())
        finally:
            MocketSocket.error_on_init = False

    def test_getips_catches_error_on_getsockname(self):
        original_getsockname = MocketSocket.getsockname
        MocketSocket.getsockname = lambda s: 1 / 0

        try:
            self.assertEqual([], system_info.getips())

        finally:
            MocketSocket.getsockname = original_getsockname

    def test_gethostname_returns_dyno(self):
        with patch.dict('os.environ', {'DYNO': 'dynosaurus'}):
            hostname = system_info.gethostname(use_dyno_names=True)

            self.assertEqual(hostname, 'dynosaurus')

    def test_gethostname_ignores_dyno_when_disabled(self):
        with patch.dict('os.environ', {'DYNO': 'dynosaurus'}):
            hostname = system_info.gethostname(use_dyno_names=False)

            self.assertEqual(hostname, 'mock-hostname-1')

    def test_gethostname_dyno_prefixes_are_collapsed(self):
        with patch.dict('os.environ', {'DYNO': 'prefix.dynosaurus'}):
            hostname = system_info.gethostname(use_dyno_names=True,
                    dyno_shorten_prefixes=['prefix'])

            self.assertEqual(hostname, 'prefix.*')

    def test_gethostname_dyno_only_shortens_on_prefix_match(self):
        with patch.dict('os.environ', {'DYNO': 'dynosaurus'}):
            hostname = system_info.gethostname(use_dyno_names=True,
                    dyno_shorten_prefixes=['meow'])

            self.assertEqual(hostname, 'dynosaurus')

    def test_gethostname_prefixes_allow_csv(self):
        with patch.dict('os.environ', {'DYNO': 'dynosaurus.1'}):
            hostname = system_info.gethostname(use_dyno_names=True,
                    dyno_shorten_prefixes=['rex', 'dynosaurus'])

            self.assertEqual(hostname, 'dynosaurus.*')

    def test_gethostname_prefix_empty_string(self):
        with patch.dict('os.environ', {'DYNO': 'dynosaurus.1'}):
            hostname = system_info.gethostname(use_dyno_names=True,
                    dyno_shorten_prefixes=[''])
            self.assertEqual(hostname, 'dynosaurus.1')

    def test_gethostname_unsupported_object(self):
        with patch.dict('os.environ', {'DYNO': 'dynosaurus.1'}):
            with pytest.raises(TypeError):
                system_info.gethostname(use_dyno_names=True,
                        dyno_shorten_prefixes=[{'meow': 'wruff'}])


if __name__ == '__main__':
    unittest.main()
