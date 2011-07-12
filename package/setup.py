import os, sys, string, re

import distutils.core
import distutils.command.install_data
import distutils.command.install

copyright = '(C) Copyright 2010-2011 New Relic Inc. All rights reserved.'

python_version = '%d.%d' % sys.version_info[:2]
unicode_variant = { 65535: 'ucs2', 1114111: 'ucs4' }[sys.maxunicode]
package_name = 'python-%s-%s' % (python_version, unicode_variant)

script_directory = os.path.dirname(__file__)
if not script_directory:
  script_directory = os.getcwd()

version_file = os.path.join(script_directory, 'VERSION')
platform_file = os.path.join(script_directory, 'PLATFORM')

package_version = open(version_file).read().strip()
package_platform = open(platform_file).read().strip()

config_guess = os.path.join(script_directory, 'scripts/config.guess')

try:
  import subprocess
  actual_platform = subprocess.Popen(config_guess,
      stdout=subprocess.PIPE).stdout.read().strip()
except:
  actual_platform = os.popen4(config_guess)[1].read().strip()

actual_platform = re.sub('[0-9.]*$', '', actual_platform)

if package_platform != actual_platform:
  print >> sys.stderr
  print >> sys.stderr, 'Sorry, this is the wrong release for this platform.'
  print >> sys.stderr, 'Require release for "%s" platform.' % actual_platform
  print >> sys.stderr
  raise SystemExit(1)

target_directory = os.path.join(script_directory, 'agent', package_name)

if not os.path.isdir(target_directory):
  print >> sys.stderr
  print >> sys.stderr, 'Sorry, no matching package for Python installation.'
  print >> sys.stderr, 'Require package for "%s".' % package_name
  print >> sys.stderr
  raise SystemExit(1)

print
print 'Using package %s.' % package_name
print

os.chdir(target_directory)

class install_override(distutils.command.install.install):
  def run(self):
    install_cmd = self.get_finalized_command('install')
    install_cmd.force = True
    self.install_dir = getattr(install_cmd, 'install_lib')
    return distutils.command.install.install.run(self)

class install_data_override(distutils.command.install_data.install_data):
  def run(self):
    install_cmd = self.get_finalized_command('install')
    install_cmd.force = True
    self.install_dir = getattr(install_cmd, 'install_lib')
    return distutils.command.install_data.install_data.run(self)

packages = [
  "newrelic",
  "newrelic.commands",
  "newrelic.imports",
  "newrelic.imports.database",
  "newrelic.imports.external",
  "newrelic.imports.framework",
  "newrelic.imports.memcache",
  "newrelic.imports.template",
]

distutils.core.setup(
  name = "newrelic",
  version = '.'.join(package_version.split('.')[:-1]),
  description = "Python agent for New Relic",
  author = "New Relic",
  author_email = "support@newrelic.com",
  license = copyright,
  url = "http://www.newrelic.com",
  packages = packages,
  data_files = [('', ['newrelic-%s/_newrelic.so' % package_version])],
  package_dir = { 'newrelic': 'newrelic-%s/newrelic' % package_version },
  extra_path = ("newrelic", "newrelic-%s" % package_version),
  platforms = [package_platform],
  cmdclass = { 'install_data' : install_data_override,
               'install' : install_override },
)
