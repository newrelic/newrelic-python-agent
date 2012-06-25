import sys
import os

with_setuptools = False

try:
    from setuptools import setup
    with_setuptools = True
except:
    from distutils.core import setup

from distutils.core import Extension
from distutils.command.build_ext import build_ext
from distutils.errors import (CCompilerError, DistutilsExecError,
        DistutilsPlatformError)

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

    package_version = newrelic.version

    version_file_fds = open(version_file, 'w')
    print >> version_file_fds, package_version
    version_file_fds.close()

else:
    # Installing from release package.

    package_version = open(version_file, 'r').read().strip()

if sys.platform == 'win32' and sys.version_info > (2, 6):
   build_ext_errors = (CCompilerError, DistutilsExecError,
           DistutilsPlatformError, IOError)
else:
   build_ext_errors = (CCompilerError, DistutilsExecError,
           DistutilsPlatformError)

class BuildExtFailed(Exception):
    pass

class optional_build_ext(build_ext):
    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError, x:
            raise BuildExtFailed()

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except build_ext_errors, x:
            raise BuildExtFailed()

packages = [
  "newrelic",
  "newrelic.api",
  "newrelic.core",
  "newrelic.extras",
  "newrelic.extras.framework_django",
  "newrelic.extras.framework_django.templatetags",
  "newrelic.hooks",
  "newrelic.lib",
  #"newrelic.lib.sqlparse",
  #"newrelic.lib.sqlparse.engine",
  "newrelic.lib.namedtuple",
  "newrelic.lib.simplejson",
  "newrelic.lib.requests",
  "newrelic.lib.requests.packages",
  "newrelic.lib.requests.packages.urllib3",
  "newrelic.lib.requests.packages.urllib3.packages",
  "newrelic.lib.requests.packages.urllib3.packages.ssl_match_hostname",
  "newrelic.lib.requests.packages.oreos",
  "newrelic.bootstrap",
]

kwargs = dict(
  name = "newrelic",
  version = package_version,
  description = "Python agent for New Relic",
  author = "New Relic",
  author_email = "support@newrelic.com",
  license = copyright,
  url = "http://www.newrelic.com",
  packages = packages,
  package_data = { 'newrelic': ['newrelic.ini', 'LICENSE',
                                'lib/sqlparse/LICENSE'] },
  extra_path = ( "newrelic", "newrelic-%s" % package_version ),
  scripts = [ 'scripts/newrelic-admin', 'scripts/newrelic-console' ],
)

if with_setuptools:
    kwargs['entry_points'] = {
      'console_scripts': ['newrelic-admin = newrelic.admin:main',
                          'newrelic-console = newrelic.console:main'],
    }

def run_setup(with_extensions):
    kwargs_tmp = dict(kwargs)

    if with_extensions:
        kwargs_tmp['ext_modules'] = [Extension(
            "newrelic.lib.simplejson._speedups",
            ["newrelic/lib/simplejson/_speedups.c"])]
        kwargs_tmp['cmdclass'] = dict(build_ext=optional_build_ext)

    setup(**kwargs_tmp)

WARNING = """
WARNING: The optional C extension components of the Python agent could
not be compiled. This can occur where a compiler is not present on the
target system or the Python installation does not have the corresponding
developer package installed. The Python agent will instead be installed
without the extensions. The consequence of this is that although the
Python agent will still run, JSON encoding/decoding speedups will not be
available, nor will some of the non core features of the Python agent.
"""

try:
    run_setup(with_extensions=True)

except BuildExtFailed:

    print 75 * '*'

    print WARNING
    print "INFO: Trying to build the Python agent now without extensions."

    print
    print 75 * '*'

    run_setup(with_extensions=False)

    print 75 * '*'

    print WARNING
    print "INFO: Only pure Python parts of the Python agent were installed."

    print
    print 75 * '*'
