import sys
import os

try:
    from setuptools import setup
except:
    from distutils.core import setup

copyright = '(C) Copyright 2010-2011 New Relic Inc. All rights reserved.'

script_directory = os.path.dirname(__file__)
if not script_directory:
    script_directory = os.getcwd()

develop_file = os.path.join(script_directory, 'DEVELOP')
version_file = os.path.join(script_directory, 'VERSION')
license_file = os.path.join(script_directory, 'LICENSE')

if os.path.exists(develop_file):
    # Building from source repository.

    import newrelic

    build_number = os.environ.get('BUILD_NUMBER', '0')
    package_version = "%s.%s" % (newrelic.version, build_number)
    package_directory = '.'

    version_file_fds = open(version_file, 'w')
    print >> version_file_fds, package_version
    version_file_fds.close()

else:
    # Installing from release package.

    package_version = open(version_file, 'r').read().strip()
    package_directory = '.'


packages = [
  "newrelic",
  "newrelic.api",
  "newrelic.core",
  "newrelic.hooks",
  "newrelic.lib",
  "newrelic.lib.sqlparse",
  "newrelic.lib.sqlparse.engine",
  "newrelic.scripts",
]

setup(
  name = "newrelic",
  version = package_version,
  description = "Python agent for New Relic",
  author = "New Relic",
  author_email = "support@newrelic.com",
  license = copyright,
  url = "http://www.newrelic.com",
  packages = packages,
  package_dir = { 'newrelic': '%s/newrelic' % package_directory },
  package_data = { 'newrelic': ['newrelic.ini', 'LICENSE',
                                'lib/sqlparse/LICENSE'] },
  extra_path = ("newrelic", "newrelic-%s" % package_version),
)
