import os, sys, string
from distutils.core import setup
from distutils.command.install_data import install_data

copyright = '(C) Copyright 2010-2011 New Relic Inc. All rights reserved.'

python_version = '%d.%d' % sys.version_info[:2]
unicode_variant = { 65535: 'ucs2', 1114111: 'ucs4' }[sys.maxunicode]
package_name = 'python-%s-%s' % (python_version, unicode_variant)

script_directory = os.path.dirname(__file__)
if not script_directory:
  script_directory = os.getcwd()

release_name = os.path.basename(script_directory)

release_fields = string.splitfields(release_name, '-', 3)

try:
  package_version, package_platform = release_fields[-2:]
except ValueError:
  print >> sys.stderr
  print >> sys.stderr, 'Package corrupted, did you rename the directory?'
  print >> sys.stderr
  raise SystemExit(1)

config_guess = 'config.guess | sed -e "s/[0-9.]*$//"'
config_guess = os.path.join(script_directory, config_guess)

try:
  import subprocess
  actual_platform = subprocess.Popen(config_guess,
      stdout=subprocess.PIPE).stdout.read().strip()
except:
  actual_platform = os.popen4(config_guess)[1].read().strip()

if package_platform != actual_platform:
  print >> sys.stderr
  print >> sys.stderr, 'Sorry, this is the wrong release for this platform.'
  print >> sys.stderr, 'Require release for "%s" platform.' % actual_platform
  print >> sys.stderr
  raise SystemExit(1)

target_directory = os.path.join(script_directory, package_name)

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

class install_lib(install_data):
  def run(self):
    install_cmd = self.get_finalized_command('install')
    self.install_dir = getattr(install_cmd, 'install_lib')
    return install_data.run(self)

print package_version

setup(
  name = "newrelic",
  version = '.'.join(package_version.split('.')[:-1]),
  description = "Python agent for New Relic",
  author = "New Relic",
  author_email = "support@newrelic.com",
  license = copyright,
  url = "http://www.newrelic.com",
  packages = ["newrelic"],
  data_files = [('', ['_newrelic.so'])],
  platforms = [package_platform],
  cmdclass = { 'install_data' : install_lib },
)
