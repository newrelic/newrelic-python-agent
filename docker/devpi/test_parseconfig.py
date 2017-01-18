import os
import shutil
import subprocess
import tempfile
import unittest

from pip._vendor.packaging.requirements import Requirement

import parseconfig

_new_tox = """
[tox]
setupdir = {toxinidir}/../..
envlist =
    {py26,py27}-flask{0006,0007,0008,0009}-{with,without}-extensions,
    {py26,py27,py33,py34,py35}-flask0010-{with,without}-extensions,
    pypy-flask{0006,0007,0008,0009,0010}-without-extensions,

[pytest]
usefixtures = session_initialization requires_data_collector

[testenv]
deps =
    Flask-Compress
    flask0006: flask<0.7
    flask0007: flask<0.8
    flask0008: flask<0.9
    flask0009: flask<0.10
    flask0010: flask<0.11
setenv =
    PYTHONPATH={toxinidir}/..
    TOX_ENVDIR = {envdir}
    without-extensions: NEW_RELIC_EXTENSIONS = false
    with-extensions: NEW_RELIC_EXTENSIONS = true

commands = py.test -v []

install_command=
    pip install -r {toxinidir}/../base_requirements.txt {opts} {packages}
"""

_old_tox = """
[tox]
setupdir = {toxinidir}/../..
toxworkdir = {toxinidir}/.tox-0010
envlist =
    py26-without-extensions,
    py27-without-extensions,
    py33-without-extensions,
    py34-without-extensions,
    py35-without-extensions,
    pypy-without-extensions,
    py26-with-extensions,
    py27-with-extensions,
    py33-with-extensions,
    py34-with-extensions,
    py35-with-extensions,

[pytest]
usefixtures = session_initialization requires_data_collector

[defaults]
deps =
    pytest==2.7.3
    pytest-cov
    WebTest==2.0.23
    flask<0.11
    Flask-Compress
setenv =
    PYTHONPATH={toxinidir}/..
    TOX_ENVDIR = {envdir}

[defaults-without-extensions]
setenv =
    {[defaults]setenv}
    NEW_RELIC_EXTENSIONS = false

[defaults-with-extensions]
setenv =
    {[defaults]setenv}
    NEW_RELIC_EXTENSIONS = true

[testenv:py26-without-extensions]
basepython = python2.6
deps = {[defaults]deps}
commands = py.test -v []
setenv = {[defaults-without-extensions]setenv}

[testenv:py27-without-extensions]
basepython = python2.7
deps = {[defaults]deps}
commands = py.test -v []
setenv = {[defaults-without-extensions]setenv}

[testenv:py33-without-extensions]
basepython = python3.3
deps = {[defaults]deps}
commands = py.test -v []
setenv = {[defaults-without-extensions]setenv}

[testenv:py34-without-extensions]
basepython = python3.4
deps = {[defaults]deps}
commands = py.test -v []
setenv = {[defaults-without-extensions]setenv}

[testenv:py35-without-extensions]
basepython = python3.5
deps = {[defaults]deps}
commands = py.test -v []
setenv = {[defaults-without-extensions]setenv}

[testenv:pypy-without-extensions]
basepython = pypy
deps = {[defaults]deps}
commands = py.test -v []
setenv = {[defaults-without-extensions]setenv}

[testenv:py26-with-extensions]
basepython = python2.6
deps = {[defaults]deps}
commands = py.test -v []
setenv = {[defaults-with-extensions]setenv}

[testenv:py27-with-extensions]
basepython = python2.7
deps = {[defaults]deps}
commands = py.test -v []
setenv = {[defaults-with-extensions]setenv}

[testenv:py33-with-extensions]
basepython = python3.3
deps = {[defaults]deps}
commands = py.test -v []
setenv = {[defaults-with-extensions]setenv}

[testenv:py34-with-extensions]
basepython = python3.4
deps = {[defaults]deps}
commands = py.test -v []
setenv = {[defaults-with-extensions]setenv}

[testenv:py35-with-extensions]
basepython = python3.5
deps = {[defaults]deps}
commands = py.test -v []
setenv = {[defaults-with-extensions]setenv}
"""

class TestExtractPackages(unittest.TestCase):

    def setUp(self):
        self.tox_file_new = tempfile.NamedTemporaryFile()
        self.tox_file_new.write(_new_tox)
        self.tox_file_new.seek(0)

        self.tox_file_old = tempfile.NamedTemporaryFile()
        self.tox_file_old.write(_old_tox)
        self.tox_file_old.seek(0)

    def tearDown(self):
        self.tox_file_new.close()
        self.tox_file_old.close()

    def test_new_filetype(self):
        expected = {
            'all': set(['flask<0.8', 'flask<0.9', 'flask<0.10', 'flask<0.11',
                'Flask-Compress', 'flask<0.7']),
            'py26': set([]),
            'py27': set([]),
            'py33': set([]),
            'py34': set([]),
            'py35': set([]),
            'pypy': set([]),
        }
        packages = parseconfig.extract_packages([self.tox_file_new.name], [], [])
        self.assertDictEqual(packages, expected)

    def test_new_filetype_with_exclude(self):
        expected = {
            'all': set(['flask<0.9', 'flask<0.10', 'flask<0.11',
                'Flask-Compress', 'flask<0.7']),
            'py26': set([]),
            'py27': set([]),
            'py33': set([]),
            'py34': set([]),
            'py35': set([]),
            'pypy': set([]),
        }
        packages = parseconfig.extract_packages(
                [self.tox_file_new.name], ['flask<0.8'], [])
        self.assertDictEqual(packages, expected)

    def test_new_filetype_with_extrapackages(self):
        expected = {
            'all': set(['flask<0.8', 'flask<0.9', 'flask<0.10', 'flask<0.11',
                'Flask-Compress', 'flask<0.7', 'super-package']),
            'py26': set([]),
            'py27': set([]),
            'py33': set([]),
            'py34': set([]),
            'py35': set([]),
            'pypy': set([]),
        }
        packages = parseconfig.extract_packages(
                [self.tox_file_new.name], [], ['super-package'])
        self.assertDictEqual(packages, expected)

    def test_old_filetype(self):
        expected = {
            'all': set([]),
            'py27': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'py26': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'py33': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'py34': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'py35': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'pypy': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
        }
        packages = parseconfig.extract_packages(
                [self.tox_file_old.name], [], [])
        self.assertDictEqual(packages, expected)

    def test_old_filetype_with_exclude(self):
        expected = {
            'all': set([]),
            'py27': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'Flask-Compress']),
            'py26': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'Flask-Compress']),
            'py33': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'Flask-Compress']),
            'py34': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'Flask-Compress']),
            'py35': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'Flask-Compress']),
            'pypy': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'Flask-Compress']),
        }
        packages = parseconfig.extract_packages(
                [self.tox_file_old.name], ['flask<0.11'], [])
        self.assertDictEqual(packages, expected)

    def test_old_filetype_with_extrapackages(self):
        expected = {
            'all': set(['super-package']),
            'py27': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'py26': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'py33': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'py34': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'py35': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'pypy': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
        }
        packages = parseconfig.extract_packages(
                [self.tox_file_old.name], [], ['super-package'])
        self.assertDictEqual(packages, expected)

    def test_both_filetypes_at_once(self):
        expected = {
            'all': set(['flask<0.8', 'flask<0.9', 'flask<0.10', 'flask<0.11',
                'Flask-Compress', 'flask<0.7']),
            'py27': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'py26': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'py33': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'py34': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'py35': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
            'pypy': set(['pytest==2.7.3', 'WebTest==2.0.23', 'pytest-cov',
                'flask<0.11', 'Flask-Compress']),
        }
        packages = parseconfig.extract_packages(
                [self.tox_file_old.name, self.tox_file_new.name], [], [])
        self.assertDictEqual(packages, expected)

class TestCreateWheelBuildFiles(unittest.TestCase):

    def setUp(self):
        self.out_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.out_dir)

    def test_file_created_for_each_env(self):
        packages = {
            'all': set([]),
            'py27': set([]),
            'py33': set([]),
        }
        parseconfig.create_wheel_build_files(packages, self.out_dir, [])
        created_files = os.listdir(self.out_dir)
        self.assertEqual(created_files, ['wheels-py27.txt', 'wheels-py33.txt'])

    def test_packages_from_all_env_added_to_all_envs(self):
        packages = {
            'all': set(['package-1', 'package-2']),
            'py27': set([]),
            'py33': set([]),
        }
        expected_contents = 'package-2\npackage-1'
        parseconfig.create_wheel_build_files(packages, self.out_dir, [])
        created_files = os.listdir(self.out_dir)
        for wheel_file in created_files:
            with open(os.path.join(self.out_dir, wheel_file)) as f:
                self.assertEqual(f.read(), expected_contents)

    def test_source_only_get_ignored(self):
        packages = {
            'all': set(['package-1', 'package-2']),
            'py27': set([]),
            'py33': set([]),
        }
        expected_contents = 'package-1'
        parseconfig.create_wheel_build_files(packages, self.out_dir,
                ['package-2'])
        created_files = os.listdir(self.out_dir)
        for wheel_file in created_files:
            with open(os.path.join(self.out_dir, wheel_file)) as f:
                self.assertEqual(f.read(), expected_contents)

class TestSetPackageDefaults(unittest.TestCase):

    def test_newstyle_flask_example(self):
        envlist = """
            {py26,py27}-flask{0006,0007,0008,0009}-{with,without}-extensions,
            {py26,py27,py33,py34,py35}-flask0010-{with,without}-extensions,
            pypy-flask{0006,0007,0008,0009,0010}-without-extensions,
            """
        packages = parseconfig._set_package_defaults({}, envlist)
        expected = {
            'py26': set([]),
            'py27': set([]),
            'py33': set([]),
            'py34': set([]),
            'py35': set([]),
            'pypy': set([]),
        }
        self.assertEqual(packages, expected)

    def test_correctly_ignores_package_names(self):
        envlist = '{py27,pypy}-pylibmc'
        packages = parseconfig._set_package_defaults({}, envlist)
        expected = {
            'py27': set([]),
            'pypy': set([]),
        }
        self.assertEqual(packages, expected)

    def test_handles_non_empty_package_dict(self):
        envlist = '{py27,pypy}-pylibmc'
        packages = {
            'all': set(['mypackage']),
            'py27': set(['another-package']),
            'py36': set(['this', 'that']),
        }
        packages = parseconfig._set_package_defaults(packages, envlist)
        expected = {
            'all': set(['mypackage']),
            'py27': set(['another-package']),
            'pypy': set([]),
            'py36': set(['this', 'that']),
        }
        self.assertEqual(packages, expected)

    def test_old_filetype_envlist(self):
        envlist = """
            py26-without-extensions,
            py27-without-extensions,
            py33-without-extensions,
            py34-without-extensions,
            py35-without-extensions,
            pypy-without-extensions,
            py26-with-extensions,
            py27-with-extensions,
            py33-with-extensions,
            py34-with-extensions,
            py35-with-extensions,
            """
        packages = parseconfig._set_package_defaults({}, envlist)
        expected = {
            'py26': set([]),
            'py27': set([]),
            'py33': set([]),
            'py34': set([]),
            'py35': set([]),
            'pypy': set([]),

        }
        self.assertEqual(packages, expected)

class TestDepListForAllToxFiles(unittest.TestCase):

    def get_all_toxes(self):
        cmd = 'find . -name "*tox*.ini" -type f'
        proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        assert not stderr, stderr
        return stdout.strip().split('\n')

    def test_no_illegal_chars_in_deps_list(self):
        toxes = self.get_all_toxes()
        packages = parseconfig.extract_packages(toxes, [], [])
        for packages in packages.values():
            for package in packages:
                # this will error if the package is malformed
                Requirement(package)

if __name__ == '__main__':
    unittest.main()
