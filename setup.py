import sys
import os

try:
    # Try and use setuptools first. This is
    # needed if we are being run from pip.

    from setuptools import setup

except:
    from distutils.core import setup

copyright = '(C) Copyright 2010-2011 New Relic Inc. All rights reserved.'

script_directory = os.path.dirname(__file__)
if not script_directory:
    script_directory = os.getcwd()

version_file = os.path.join(script_directory, 'VERSION')

if os.path.exists(version_file):
    # Being executed from released package.

    package_version = open(version_file).read().strip()
    package_directory = 'newrelic-%s' % package_version

else:
    # Being executed from repository package.

    import newrelic
    build_number = os.environ.get('HUDSON_BUILD_NUMBER', '0')
    package_version = "%s.%s" % (newrelic.version, build_number)
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
  extra_path = ("newrelic", "newrelic-%s" % package_version),
)
