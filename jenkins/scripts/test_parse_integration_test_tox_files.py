#!/usr/bin/env python2.7

"""
These tests test parse_integration_test_tox_files.py and should not be run as
part of our continuous integration.
"""

import os
import tempfile
import unittest

from parse_integration_test_tox_files import (possibly_group_envs, get_envs,
        str2bool, parse_tox_file, get_tests, strip_workspace)


class TestPossiblyGroupEnvs(unittest.TestCase):
    range_3 = ['0', '1', '2']
    range_6 = ['0', '1', '2', '3', '4', '5']

    def test_env_list_smaller_than_max(self):
        expected = [('0,1,2', 'group0')]
        actual = possibly_group_envs(self.range_3, 10)

        self.assertEqual(expected, actual)

    def test_env_list_equal_to_max(self):
        expected = [('0,1,2', 'group0')]
        actual = possibly_group_envs(self.range_3, 3)

        self.assertEqual(expected, actual)

    def test_env_list_exactly_twice_max(self):
        expected = [
            ('0,2,4', 'group0'),
            ('1,3,5', 'group1'),
        ]
        actual = possibly_group_envs(self.range_6, 3)

        self.assertEqual(expected, actual)

    def test_env_list_not_evenly_divisible_by_max(self):
        expected = [
            ('0,2,4', 'group0'),
            ('1,3,5', 'group1'),
        ]
        actual = possibly_group_envs(self.range_6, 4)

        self.assertEqual(expected, actual)


_test_get_envs_tox_file_simple = """
[tox]
envlist =
    env1,
    env2,
    env3,
"""

_test_get_envs_tox_file_complex = """
[tox]
setupdir = {toxinidir}/../..
envlist =
    {py27,py35,py36}-Django0110-{old,new}-middleware-{with,without}-extensions,
    pypy-Django0110-{old,new}-middleware-without-extensions,

[jenkins]
mostrecent = Django0110

[pytest]
usefixtures = session_initialization requires_data_collector

[testenv]
deps =
    Django0103: Django<1.4
    Django0104: Django<1.5
    Django0105: Django<1.6
    Django0106: Django<1.7
    Django0107: Django<1.8
    Django0108: Django<1.9
    Django0109: Django<1.10
    Django0110: Django<1.11
setenv =
    PYTHONPATH={toxinidir}/..
    TOX_ENVDIR = {envdir}
    without-extensions: NEW_RELIC_EXTENSIONS = false
    with-extensions: NEW_RELIC_EXTENSIONS = true
    Django0110-old-middleware: DJANGO_SETTINGS_MODULE=settings_0110_old
    Django0110-new-middleware: DJANGO_SETTINGS_MODULE=settings_0110_new

commands = py.test -v []

install_command=
    pip install -r {toxinidir}/../base_requirements.txt {opts} {packages}
"""

_test_get_envs_tox_file_multi_version = """
[tox]
setupdir = {toxinidir}/../..
envlist =
    {py26,py27}-Django{0103,0104}-{with,without}-extensions,
    {py26,py27,py33}-Django{0105,0106}-{with,without}-extensions,
    {py27,py33}-Django{0107}-{with,without}-extensions,
    {py27,py33,py35,py36}-Django{0108}-{with,without}-extensions,
    {py27,py35,py36}-Django0109-{with,without}-extensions,
    {py27,py35,py36}-Django0110-{old,new}-middleware-{with,without}-extensions,
    pypy-Django{0103,0104,0105,0106,0107,0108,0109}-without-extensions,
    pypy-Django0110-{old,new}-middleware-without-extensions,
    pypy3-Django{0105,0106,0107,0108}-without-extensions,

[jenkins]
mostrecent = Django0110

[pytest]
usefixtures = session_initialization requires_data_collector

[testenv]
deps =
    Django0103: Django<1.4
    Django0104: Django<1.5
    Django0105: Django<1.6
    Django0106: Django<1.7
    Django0107: Django<1.8
    Django0108: Django<1.9
    Django0109: Django<1.10
    Django0110: Django<1.11
setenv =
    PYTHONPATH={toxinidir}/..
    TOX_ENVDIR = {envdir}
    without-extensions: NEW_RELIC_EXTENSIONS = false
    with-extensions: NEW_RELIC_EXTENSIONS = true
    Django0110-old-middleware: DJANGO_SETTINGS_MODULE=settings_0110_old
    Django0110-new-middleware: DJANGO_SETTINGS_MODULE=settings_0110_new

commands = py.test -v []

install_command=
    pip install -r {toxinidir}/../base_requirements.txt {opts} {packages}
"""

_test_get_envs_all_django_envs = [
    'py26-Django0103-with-extensions',
    'py26-Django0103-without-extensions',
    'py26-Django0104-with-extensions',
    'py26-Django0104-without-extensions',
    'py27-Django0103-with-extensions',
    'py27-Django0103-without-extensions',
    'py27-Django0104-with-extensions',
    'py27-Django0104-without-extensions',
    'py26-Django0105-with-extensions',
    'py26-Django0105-without-extensions',
    'py26-Django0106-with-extensions',
    'py26-Django0106-without-extensions',
    'py27-Django0105-with-extensions',
    'py27-Django0105-without-extensions',
    'py27-Django0106-with-extensions',
    'py27-Django0106-without-extensions',
    'py33-Django0105-with-extensions',
    'py33-Django0105-without-extensions',
    'py33-Django0106-with-extensions',
    'py33-Django0106-without-extensions',
    'py27-Django0107-with-extensions',
    'py27-Django0107-without-extensions',
    'py33-Django0107-with-extensions',
    'py33-Django0107-without-extensions',
    'py27-Django0108-with-extensions',
    'py27-Django0108-without-extensions',
    'py33-Django0108-with-extensions',
    'py33-Django0108-without-extensions',
    'py35-Django0108-with-extensions',
    'py35-Django0108-without-extensions',
    'py36-Django0108-with-extensions',
    'py36-Django0108-without-extensions',
    'py27-Django0109-with-extensions',
    'py27-Django0109-without-extensions',
    'py35-Django0109-with-extensions',
    'py35-Django0109-without-extensions',
    'py36-Django0109-with-extensions',
    'py36-Django0109-without-extensions',
    'py27-Django0110-old-middleware-with-extensions',
    'py27-Django0110-old-middleware-without-extensions',
    'py27-Django0110-new-middleware-with-extensions',
    'py27-Django0110-new-middleware-without-extensions',
    'py35-Django0110-old-middleware-with-extensions',
    'py35-Django0110-old-middleware-without-extensions',
    'py35-Django0110-new-middleware-with-extensions',
    'py35-Django0110-new-middleware-without-extensions',
    'py36-Django0110-old-middleware-with-extensions',
    'py36-Django0110-old-middleware-without-extensions',
    'py36-Django0110-new-middleware-with-extensions',
    'py36-Django0110-new-middleware-without-extensions',
    'pypy-Django0103-without-extensions',
    'pypy-Django0104-without-extensions',
    'pypy-Django0105-without-extensions',
    'pypy-Django0106-without-extensions',
    'pypy-Django0107-without-extensions',
    'pypy-Django0108-without-extensions',
    'pypy-Django0109-without-extensions',
    'pypy-Django0110-old-middleware-without-extensions',
    'pypy-Django0110-new-middleware-without-extensions',
    'pypy3-Django0105-without-extensions',
    'pypy3-Django0106-without-extensions',
    'pypy3-Django0107-without-extensions',
    'pypy3-Django0108-without-extensions',
]

_test_get_envs_django_0110_envs = [
    'py27-Django0110-old-middleware-with-extensions',
    'py27-Django0110-old-middleware-without-extensions',
    'py27-Django0110-new-middleware-with-extensions',
    'py27-Django0110-new-middleware-without-extensions',
    'py35-Django0110-old-middleware-with-extensions',
    'py35-Django0110-old-middleware-without-extensions',
    'py35-Django0110-new-middleware-with-extensions',
    'py35-Django0110-new-middleware-without-extensions',
    'py36-Django0110-old-middleware-with-extensions',
    'py36-Django0110-old-middleware-without-extensions',
    'py36-Django0110-new-middleware-with-extensions',
    'py36-Django0110-new-middleware-without-extensions',
    'pypy-Django0110-old-middleware-without-extensions',
    'pypy-Django0110-new-middleware-without-extensions',
]

_test_get_envs_django_0110_envs_no_cext = [
    'py27-Django0110-old-middleware-without-extensions',
    'py27-Django0110-new-middleware-without-extensions',
    'py35-Django0110-old-middleware-without-extensions',
    'py35-Django0110-new-middleware-without-extensions',
    'py36-Django0110-old-middleware-without-extensions',
    'py36-Django0110-new-middleware-without-extensions',
    'pypy-Django0110-old-middleware-without-extensions',
    'pypy-Django0110-new-middleware-without-extensions',
]


class TestGetEnvs(unittest.TestCase):

    def get_tox_file(self, contents):
        tox_file = tempfile.NamedTemporaryFile()
        tox_file.write(contents.encode('utf-8'))
        tox_file.seek(0)
        return tox_file

    def tearDown(self):
        self.tox_file.close()

    def test_simple_tox_file_restrict_to_none(self):
        self.tox_file = self.get_tox_file(_test_get_envs_tox_file_simple)

        actual = get_envs(self.tox_file.name, restrict_to=None)
        expected = ['env1', 'env2', 'env3']

        self.assertEqual(actual, expected)

    def test_simple_tox_file_restrict_to_in_env_list(self):
        self.tox_file = self.get_tox_file(_test_get_envs_tox_file_simple)

        actual = get_envs(self.tox_file.name, restrict_to='env1')
        expected = ['env1']

        self.assertEqual(actual, expected)

    def test_simple_tox_file_restrict_to_not_in_env_list(self):
        self.tox_file = self.get_tox_file(_test_get_envs_tox_file_simple)

        actual = get_envs(self.tox_file.name, restrict_to='not_env1')
        expected = []

        self.assertEqual(actual, expected)

    def test_complex_tox_file_restrict_to_none(self):
        self.tox_file = self.get_tox_file(_test_get_envs_tox_file_complex)

        actual = get_envs(self.tox_file.name, restrict_to=None)
        expected = _test_get_envs_django_0110_envs

        self.assertEqual(actual, expected)

    def test_complex_tox_file_restrict_to_in_env_list(self):
        self.tox_file = self.get_tox_file(_test_get_envs_tox_file_complex)

        actual = get_envs(self.tox_file.name, restrict_to='Django0110')
        expected = _test_get_envs_django_0110_envs

        self.assertEqual(actual, expected)

    def test_complex_tox_file_restrict_to_not_in_env_list(self):
        self.tox_file = self.get_tox_file(_test_get_envs_tox_file_complex)

        actual = get_envs(self.tox_file.name, restrict_to='not_Django0110')
        expected = []

        self.assertEqual(actual, expected)

    def test_multi_version_tox_file_restrict_to_none(self):
        self.tox_file = self.get_tox_file(
                _test_get_envs_tox_file_multi_version)

        actual = get_envs(self.tox_file.name, restrict_to=None)
        expected = _test_get_envs_all_django_envs

        self.assertEqual(actual, expected)

    def test_multi_version_tox_file_restrict_to_in_env_list(self):
        self.tox_file = self.get_tox_file(
                _test_get_envs_tox_file_multi_version)

        actual = get_envs(self.tox_file.name, restrict_to='Django0110')
        expected = _test_get_envs_django_0110_envs

        self.assertEqual(actual, expected)

    def test_multi_version_tox_file_restrict_to_not_in_env_list(self):
        self.tox_file = self.get_tox_file(
                _test_get_envs_tox_file_multi_version)

        actual = get_envs(self.tox_file.name, restrict_to='not_Django0110')
        expected = []

        self.assertEqual(actual, expected)

    def test_multi_version_tox_file_exclude_cext_environments(self):
        self.tox_file = self.get_tox_file(
                _test_get_envs_tox_file_multi_version)

        actual = get_envs(self.tox_file.name, restrict_to='Django0110',
                include_cext=False)
        expected = _test_get_envs_django_0110_envs_no_cext

        self.assertEqual(actual, expected)


_test_is_disabled_tox_file_no_jenkins_section = """
[tox]
envlist =
    {py27,py35,py36}-Django0110-{old,new}-middleware-{with,without}-extensions,
    pypy-Django0110-{old,new}-middleware-without-extensions,

[pytest]
usefixtures = session_initialization requires_data_collector
"""

_test_is_disabled_tox_file_no_disabled_option = """
[tox]
envlist =
    {py27,py35,py36}-Django0110-{old,new}-middleware-{with,without}-extensions,
    pypy-Django0110-{old,new}-middleware-without-extensions,

[jenkins]
mostrecent = Django0110

[pytest]
usefixtures = session_initialization requires_data_collector
"""

_test_is_disabled_tox_file_disabled_true = """
[tox]
envlist =
    {py27,py35,py36}-Django0110-{old,new}-middleware-{with,without}-extensions,
    pypy-Django0110-{old,new}-middleware-without-extensions,

[jenkins]
mostrecent = Django0110
disabled = true

[pytest]
usefixtures = session_initialization requires_data_collector
"""

_test_is_disabled_tox_file_disabled_false = """
[tox]
envlist =
    {py27,py35,py36}-Django0110-{old,new}-middleware-{with,without}-extensions,
    pypy-Django0110-{old,new}-middleware-without-extensions,

[jenkins]
mostrecent = Django0110
disabled = false

[pytest]
usefixtures = session_initialization requires_data_collector
"""


class TestIsDisabled(unittest.TestCase):

    def get_tox_file(self, contents):
        tox_file = tempfile.NamedTemporaryFile()
        tox_file.write(contents.encode('utf-8'))
        tox_file.seek(0)
        return tox_file

    def tearDown(self):
        self.tox_file.close()

    def test_no_jenkins_section(self):
        self.tox_file = self.get_tox_file(
                _test_is_disabled_tox_file_no_jenkins_section)
        self.assertEqual(parse_tox_file(self.tox_file.name)[1], False)

    def test_no_disabled_option(self):
        self.tox_file = self.get_tox_file(
                _test_is_disabled_tox_file_no_disabled_option)
        self.assertEqual(parse_tox_file(self.tox_file.name)[1], False)

    def test_disabled_true(self):
        self.tox_file = self.get_tox_file(
                _test_is_disabled_tox_file_disabled_true)
        self.assertEqual(parse_tox_file(self.tox_file.name)[1], True)

    def test_disabled_false(self):
        self.tox_file = self.get_tox_file(
                _test_is_disabled_tox_file_disabled_false)
        self.assertEqual(parse_tox_file(self.tox_file.name)[1], False)


_test_most_recent_tox_file_no_jenkins_section = """
[tox]
envlist =
    {py27,py35,py36}-Django0110-{old,new}-middleware-{with,without}-extensions,
    pypy-Django0110-{old,new}-middleware-without-extensions,

[pytest]
usefixtures = session_initialization requires_data_collector
"""

_test_most_recent_tox_file_no_most_recent_option = """
[tox]
envlist =
    {py27,py35,py36}-Django0110-{old,new}-middleware-{with,without}-extensions,
    pypy-Django0110-{old,new}-middleware-without-extensions,

[jenkins]
disabled = true

[pytest]
usefixtures = session_initialization requires_data_collector
"""

_test_most_recent_tox_file_most_recent_option_set = """
[tox]
envlist =
    {py27,py35,py36}-Django0110-{old,new}-middleware-{with,without}-extensions,
    pypy-Django0110-{old,new}-middleware-without-extensions,

[jenkins]
mostrecent = Django0110

[pytest]
usefixtures = session_initialization requires_data_collector
"""


class TestMostRecent(unittest.TestCase):

    def get_tox_file(self, contents):
        tox_file = tempfile.NamedTemporaryFile()
        tox_file.write(contents.encode('utf-8'))
        tox_file.seek(0)
        return tox_file

    def tearDown(self):
        self.tox_file.close()

    def test_no_jenkins_section(self):
        self.tox_file = self.get_tox_file(
                _test_most_recent_tox_file_no_jenkins_section)
        self.assertEqual(parse_tox_file(self.tox_file.name)[0], None)

    def test_no_most_recent_option(self):
        self.tox_file = self.get_tox_file(
                _test_most_recent_tox_file_no_most_recent_option)
        self.assertEqual(parse_tox_file(self.tox_file.name)[0], None)

    def test_most_recent_set(self):
        self.tox_file = self.get_tox_file(
                _test_most_recent_tox_file_most_recent_option_set)
        self.assertEqual(parse_tox_file(self.tox_file.name)[0], 'Django0110')


class TestStr2Bool(unittest.TestCase):

    def test_true_strings(self):
        self.assertEqual(str2bool('True'), True)
        self.assertEqual(str2bool('true'), True)
        self.assertEqual(str2bool('TRUE'), True)

    def test_false_strings(self):
        self.assertEqual(str2bool('False'), False)
        self.assertEqual(str2bool('false'), False)
        self.assertEqual(str2bool('FALSE'), False)

    def test_0_string(self):
        self.assertEqual(str2bool('0'), False)

    def test_1_string(self):
        self.assertEqual(str2bool('1'), True)

    def test_0_integer(self):
        self.assertEqual(str2bool(0), False)

    def test_1_integer(self):
        self.assertEqual(str2bool(1), True)

    def test_yes_strings(self):
        self.assertEqual(str2bool('Yes'), True)
        self.assertEqual(str2bool('yes'), True)
        self.assertEqual(str2bool('YES'), True)

    def test_no_strings(self):
        self.assertEqual(str2bool('No'), False)
        self.assertEqual(str2bool('no'), False)
        self.assertEqual(str2bool('NO'), False)


class TestGetTests(unittest.TestCase):

    def setUp(self):
        self.test_suffix = '_test_suffix'
        self.max_group_size = 4

    def make_tox_file(self, contents):
        self.tox_file = tempfile.NamedTemporaryFile(suffix='tox.ini')
        self.tox_file.write(contents.encode('utf-8'))
        self.tox_file.seek(0)

    def tearDown(self):
        if hasattr(self, 'tox_file'):
            self.tox_file.close()

    def verify_tests(self, tests, num_envs):
        all_envs = []

        for name, tox, envs, compose in tests:
            self.assertTrue(name.startswith(
                os.path.basename(tempfile.gettempdir())))
            self.assertTrue(name.endswith(self.test_suffix))

            self.assertEqual(len(tox.split(os.path.sep)), 3)

            envs = envs.split(',')
            self.assertTrue(len(envs) <= self.max_group_size)
            all_envs.extend(envs)

            self.assertTrue(compose is None)

        self.assertEqual(len(all_envs), num_envs)

    def test_get_tests_simple_most_recent_true(self):
        self.make_tox_file(_test_get_envs_tox_file_simple)
        tests = get_tests(self.test_suffix, True, self.max_group_size,
                tempfile.gettempdir())
        self.verify_tests(tests, num_envs=3)

    def test_get_tests_simple_most_recent_false(self):
        self.make_tox_file(_test_get_envs_tox_file_simple)
        tests = get_tests(self.test_suffix, False, self.max_group_size,
                tempfile.gettempdir())
        self.verify_tests(tests, num_envs=3)

    def test_get_tests_complex_most_recent_true(self):
        self.make_tox_file(_test_get_envs_tox_file_complex)
        tests = get_tests(self.test_suffix, True, self.max_group_size,
                tempfile.gettempdir())
        self.verify_tests(tests, num_envs=18)

    def test_get_tests_complex_most_recent_false(self):
        self.make_tox_file(_test_get_envs_tox_file_complex)
        tests = get_tests(self.test_suffix, False, self.max_group_size,
                tempfile.gettempdir())
        self.verify_tests(tests, num_envs=18)

    def test_get_tests_multi_most_recent_true(self):
        self.make_tox_file(_test_get_envs_tox_file_multi_version)
        tests = get_tests(self.test_suffix, True, self.max_group_size,
                tempfile.gettempdir())
        self.verify_tests(tests, num_envs=18)

    def test_get_tests_multi_most_recent_false(self):
        self.make_tox_file(_test_get_envs_tox_file_multi_version)
        tests = get_tests(self.test_suffix, False, self.max_group_size,
                tempfile.gettempdir())
        self.verify_tests(tests, num_envs=77)

    def test_get_tests_disabled_most_recent_true(self):
        self.make_tox_file(_test_get_envs_tox_file_multi_version)
        tests = get_tests(self.test_suffix, True, self.max_group_size,
                tempfile.gettempdir())
        self.verify_tests(tests, num_envs=18)

    def test_get_tests_disabled_most_recent_false(self):
        tests = get_tests(self.test_suffix, False, self.max_group_size,
                tempfile.gettempdir())
        self.verify_tests(tests, num_envs=0)

    def test_get_tests_no_tox_file_most_recent_true(self):
        tests = get_tests(self.test_suffix, True, self.max_group_size,
                tempfile.gettempdir())
        self.verify_tests(tests, num_envs=0)

    def test_get_tests_no_tox_file_most_recent_false(self):
        tests = get_tests(self.test_suffix, False, self.max_group_size,
                tempfile.gettempdir())
        self.verify_tests(tests, num_envs=0)


class TestStripWorkspace(unittest.TestCase):

    def test_looooong_tox_path(self):
        path = '/foo/bar/baz/bax/bingo/bango/bongo/tox.ini'
        actual = strip_workspace(path)
        expected = 'bango/bongo/tox.ini'
        self.assertEqual(actual, expected)

    def test_loooooong_compose_path(self):
        path = '/foo/bar/baz/bax/bingo/bango/bongo/docker-compose.yml'
        actual = strip_workspace(path)
        expected = 'bango/bongo/docker-compose.yml'
        self.assertEqual(actual, expected)

    def test_short_tox_path(self):
        path = '/foo/bar/tox.ini'
        actual = strip_workspace(path)
        expected = 'foo/bar/tox.ini'
        self.assertEqual(actual, expected)

    def test_short_compose_path(self):
        path = '/foo/bar/docker-compose.yml'
        actual = strip_workspace(path)
        expected = 'foo/bar/docker-compose.yml'
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
