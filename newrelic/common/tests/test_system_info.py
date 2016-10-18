import socket
import sys
import unittest

from newrelic.common import system_info

from newrelic.common.system_info import (docker_container_id,
        _process_cgroup_info, _validate_docker_container_id)


class TestsDockerContainerId(unittest.TestCase):

    def setUp(self):
        sys.platform = "linux"

    def test_not_linux(self):
        sys.platform = 'darwin'
        self.assertEqual(None, docker_container_id())

    # Test we parse ids we expect to see
    def test_native_no_systemd(self):
        cgroup_info = [
            "11:hugetlb:/",
            "10:perf_event:/docker/2a4f870e24a3b52eb9fe7f3e02858c31855e213e568cfa6c76cb046ffa5b8a28",
            "9:blkio:/docker/2a4f870e24a3b52eb9fe7f3e02858c31855e213e568cfa6c76cb046ffa5b8a28",
            "8:freezer:/docker/2a4f870e24a3b52eb9fe7f3e02858c31855e213e568cfa6c76cb046ffa5b8a28",
            "7:name=systemd:/",
            "6:devices:/docker/2a4f870e24a3b52eb9fe7f3e02858c31855e213e568cfa6c76cb046ffa5b8a28",
            "5:memory:/docker/2a4f870e24a3b52eb9fe7f3e02858c31855e213e568cfa6c76cb046ffa5b8a28",
            "4:cpuacct:/docker/2a4f870e24a3b52eb9fe7f3e02858c31855e213e568cfa6c76cb046ffa5b8a28",
            "3:cpu:/docker/2a4f870e24a3b52eb9fe7f3e02858c31855e213e568cfa6c76cb046ffa5b8a28",
            "2:cpuset:/"]
        self.assertEqual(
                "2a4f870e24a3b52eb9fe7f3e02858c31855e213e568cfa6c76cb046ffa5b8a28",
                _process_cgroup_info(cgroup_info))

    def test_native_systemd(self):
        cgroup_info = [
            "10:hugetlb:/",
            "9:perf_event:/",
            "8:blkio:/system.slice/docker-67f98c9e6188f9c1818672a15dbe46237b6ee7e77f834d40d41c5fb3c2f84a2f.scope",
            "7:net_cls:/",
            "6:freezer:/system.slice/docker-67f98c9e6188f9c1818672a15dbe46237b6ee7e77f834d40d41c5fb3c2f84a2f.scope",
            "5:devices:/system.slice/docker-67f98c9e6188f9c1818672a15dbe46237b6ee7e77f834d40d41c5fb3c2f84a2f.scope",
            "4:memory:/system.slice/docker-67f98c9e6188f9c1818672a15dbe46237b6ee7e77f834d40d41c5fb3c2f84a2f.scope",
            "3:cpuacct,cpu:/system.slice/docker-67f98c9e6188f9c1818672a15dbe46237b6ee7e77f834d40d41c5fb3c2f84a2f.scope",
            "2:cpuset:/",
            "1:name=systemd:/system.slice/docker-67f98c9e6188f9c1818672a15dbe46237b6ee7e77f834d40d41c5fb3c2f84a2f.scope"]
        self.assertEqual(
                "67f98c9e6188f9c1818672a15dbe46237b6ee7e77f834d40d41c5fb3c2f84a2f",
                _process_cgroup_info(cgroup_info))

    def test_lxc(self):
        cgroup_info = [
            "11:hugetlb:/lxc/cb8c113e5f3cf8332f5231f8154adc429ea910f7c29995372de4f571c55d3159",
            "10:perf_event:/lxc/cb8c113e5f3cf8332f5231f8154adc429ea910f7c29995372de4f571c55d3159",
            "9:blkio:/lxc/cb8c113e5f3cf8332f5231f8154adc429ea910f7c29995372de4f571c55d3159",
            "8:freezer:/lxc/cb8c113e5f3cf8332f5231f8154adc429ea910f7c29995372de4f571c55d3159",
            "7:name=systemd:/lxc/cb8c113e5f3cf8332f5231f8154adc429ea910f7c29995372de4f571c55d3159",
            "6:devices:/lxc/cb8c113e5f3cf8332f5231f8154adc429ea910f7c29995372de4f571c55d3159",
            "5:memory:/lxc/cb8c113e5f3cf8332f5231f8154adc429ea910f7c29995372de4f571c55d3159",
            "4:cpuacct:/lxc/cb8c113e5f3cf8332f5231f8154adc429ea910f7c29995372de4f571c55d3159",
            "3:cpu:/lxc/cb8c113e5f3cf8332f5231f8154adc429ea910f7c29995372de4f571c55d3159",
            "2:cpuset:/lxc/cb8c113e5f3cf8332f5231f8154adc429ea910f7c29995372de4f571c55d3159"]
        self.assertEqual(
                'cb8c113e5f3cf8332f5231f8154adc429ea910f7c29995372de4f571c55d3159',
                _process_cgroup_info(cgroup_info))

    def test_not_in_cgroup(self):
        cgroup_info = ["1:cpu:/"]
        self.assertEqual(None, _process_cgroup_info(cgroup_info))

    # Test for bad ids
    def test_id_has_unexpected_characters(self):
        cgroup_info = ["1:cpu:/docker/asdf1234#@%"]
        self.assertEqual(None, _process_cgroup_info(cgroup_info))

    def test_no_cpu_in_map(self):
        cgroup_info = [
            "11:hugetlb:/lxc/p1",
            "10:perf_event:/lxc/p1",
            "9:blkio:/lxc/p1"]
        self.assertEqual(None, _process_cgroup_info(cgroup_info))

    def test_unrecognized_id_format(self):
        cgroup_info = ["BAD_FORMAT"]
        self.assertEqual(None, _process_cgroup_info(cgroup_info))

    def test_validate_docker_container_id_length(self):
        container_id = 'a' * 64
        self.assertTrue(_validate_docker_container_id(container_id))
        container_id = 'a' * 65
        self.assertFalse(_validate_docker_container_id(container_id))


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
