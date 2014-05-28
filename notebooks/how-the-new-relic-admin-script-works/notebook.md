
# How the newrelic-admin script works

*Specifically, how does ``run-program`` and ``run-python`` options work.*

The ``run-program`` option is used to wrap execution of a Python script which
would normally be run as an executable. That is, has a ``#!/usr/bin/env python``
or similar line at start and script is executable.

```
newrelic-admin run-program gunicorn wsgi:application
```

The ``run-python`` option is used to start up the Python interpreter itself. It
can therefore be passed as argument a Python script to run.

```
newrelic-admin run-python manage.py runserver
```

In both cases the point of the script is to automatically embed and initialise
the agent in the running Python process.

This is done by the scripts setting the ``PYTHONPATH`` environment variable to
include a directory containing a ``sitecustomize.py`` file. When Python finds
that ``sitecustomize.py`` file it will automatically import it, allowing us to
perform actions on interpreter startup before any user code is run.

As it relies on ``PYTHONPATH`` being set, if the command being run under
``newrelic-admin`` replaces ``PYTHONPATH`` completely, then the bootstrapping
will not work. Specifically ``sitecustomize.py`` is not imported and run.

## Location of newrelic-admin script commands

Code for ``run-program`` is in repository at:

```
newrelic/admin/run_program.py
```

Code for ``run-python`` is in repository at:

```
newrelic/admin/run_python.py
```

## Location of the sitecustomize.py bootstrap directory

The bootstrap directory is in the repository at:

```
newrelic/bootstrap
```

At runtime, it will be part of the installed ``newrelic`` package.

To find it, and then set ``PYTHONPATH``, the ``newrelic-admin`` commands will
do:

```
    from newrelic import version, __file__ as root_directory

    root_directory = os.path.dirname(root_directory)
    boot_directory = os.path.join(root_directory, 'bootstrap')

    log_message('root_directory = %r', root_directory)
    log_message('boot_directory = %r', boot_directory)

    python_path = boot_directory

    if 'PYTHONPATH' in os.environ:
        path = os.environ['PYTHONPATH'].split(os.path.pathsep)
        if not boot_directory in path:
            python_path = "%s%s%s" % (boot_directory, os.path.pathsep,
                    os.environ['PYTHONPATH'])

    os.environ['PYTHONPATH'] = python_path

    ...

    os.environ['NEW_RELIC_PYTHON_PREFIX'] = os.path.realpath(
            os.path.normpath(sys.prefix))
    os.environ['NEW_RELIC_PYTHON_VERSION'] = '.'.join(
            map(str, sys.version_info[:2]))
```

## Actions performed by the sitecustomize.py module

When the ``sitecustomize.py`` module from the bootstrap directory is imported,
it performs the following actions.

Step 1: Import the original ``sitecustomize.py`` file. This is necessary as the
user could have specified their own, or they are on Ubuntu and relying on the
system wide ``sitecustomize.py`` file which is enabling the Python support for
the [Ubuntu crash
reporter](http://en.wikipedia.org/wiki/Apport_%28software%29#Ubuntu).

This is done using the code:

```
import imp

boot_directory = os.path.dirname(__file__)
root_directory = os.path.dirname(os.path.dirname(boot_directory))

log_message('root_directory = %r', root_directory)
log_message('boot_directory = %r', boot_directory)

path = list(sys.path)

if boot_directory in path:
    del path[path.index(boot_directory)]

try:
    (file, pathname, description) = imp.find_module('sitecustomize', path)
except ImportError:
    pass
else:
    log_message('sitecustomize = %r', (file, pathname, description))

    imp.load_module('sitecustomize', file, pathname, description)
```

It works by removing the bootstrap directory from ``sys.path`` and then using
``imp.find_module()`` and ``imp.load_module()`` to import the original
``sitecustomize.py`` by following our modified path. This is used instead of
``import`` or ``__import__``, because our ``sitecustomize`` will already be
present in ``sys.modules`` and it would find ours again and cause a loop.

Step 2. Ensure that ``newrelic-admin`` is being run from the same Python
installation or virtual environment as the Python application to be monitored is
using. If it isn't the agent will not initialise itself.

```
expected_python_prefix = os.environ.get('NEW_RELIC_PYTHON_PREFIX')
actual_python_prefix = os.path.realpath(os.path.normpath(sys.prefix))

expected_python_version = os.environ.get('NEW_RELIC_PYTHON_VERSION')
actual_python_version = '.'.join(map(str, sys.version_info[:2]))

python_prefix_matches = expected_python_prefix == actual_python_prefix
python_version_matches = expected_python_version == actual_python_version

log_message('python_prefix_matches = %r', python_prefix_matches)
log_message('python_version_matches = %r', python_version_matches)

if python_prefix_matches and python_version_matches:
    ... initialise agent
```

Step 3: Work out whether the required environment variables for the
configuration file or license key have been set and if they are and so logically
can initialise agent, keep going.

```
    license_key = os.environ.get('NEW_RELIC_LICENSE_KEY', None)

    config_file = os.environ.get('NEW_RELIC_CONFIG_FILE', None)
    environment = os.environ.get('NEW_RELIC_ENVIRONMENT', None)

    log_message('initialize_agent = %r', bool(license_key or config_file))

    if license_key or config_file:
        ...
```

Step 4: Perform a fiddle to get the ``newrelic`` package imported into the
process. Up till this point, only ``sitecustomize.py`` has been imported. The
issue is that under a buildout environment, it constructs as ``sys.path`` in the
user's application script file, which execludes the Python installation ``site-
packages`` directory and any ``.pth`` registered subdirectories. This means that
if ``newrelic`` is only installed into the Python installation and not listed as
a package in the buildout description, it will not be found when imported. Thus
need to add into ``sys.path`` ourselves, the ``newrelic-A.B.C.D`` directory in
``site-packages`` that contains ``newrelic`` package.

```
        if root_directory not in sys.path:
            sys.path.insert(0, root_directory)

        import newrelic.agent

        log_message('agent_version = %r', newrelic.version)

        try:
            del sys.path[sys.path.index(root_directory)]
        except Exception:
            pass
```

For good measure we remove the directory from ``sys.path`` afterwards, but that
is okay as ``newrelic`` package is already in ``sys.modules`` and will be found
okay by later imports.

Step 4: Finally initialise the actual agent.

```
        newrelic.agent.initialize(config_file, environment)
```

## Debugging newrelic-admin wrapper script startup

To debug the startup sequence when using ``newrelic-admin``, you can set the
environment variable ``NEW_RELIC_STARTUP_DEBUG`` to a non empty value. This will
yield something like:

```
(test-env)grumpy-old-man:python_agent graham$ NEW_RELIC_STARTUP_DEBUG=true
newrelic-admin run-program python
NEWRELIC: 2014-04-16 10:44:32 (20306) - New Relic Admin Script
(/Users/graham/Work/python_agent/test-env/lib/python2.7/site-packages/newrelic-2
.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/admin/run_program.pyc)
NEWRELIC: 2014-04-16 10:44:32 (20306) - working_directory =
'/Users/graham/Work/python_agent'
NEWRELIC: 2014-04-16 10:44:32 (20306) - current_command =
['/Users/graham/Work/python_agent/test-env/bin/newrelic-admin', 'run-program',
'python']
NEWRELIC: 2014-04-16 10:44:32 (20306) - sys.prefix =
'/Users/graham/Work/python_agent/test-env'
NEWRELIC: 2014-04-16 10:44:32 (20306) - sys.real_prefix =
'/System/Library/Frameworks/Python.framework/Versions/2.7'
NEWRELIC: 2014-04-16 10:44:32 (20306) - sys.version_info =
sys.version_info(major=2, minor=7, micro=2, releaselevel='final', serial=0)
NEWRELIC: 2014-04-16 10:44:32 (20306) - sys.executable =
'/Users/graham/Work/python_agent/test-env/bin/python'
NEWRELIC: 2014-04-16 10:44:32 (20306) - sys.flags = sys.flags(debug=0,
py3k_warning=0, division_warning=0, division_new=0, inspect=0, interactive=0,
optimize=0, dont_write_bytecode=0, no_user_site=0, no_site=0,
ignore_environment=0, tabcheck=0, verbose=0, unicode=0, bytes_warning=0)
NEWRELIC: 2014-04-16 10:44:32 (20306) - sys.path = [...]
NEWRELIC: 2014-04-16 10:44:32 (20306) - NEW_RELIC_STARTUP_DEBUG = 'true'
NEWRELIC: 2014-04-16 10:44:32 (20306) - root_directory =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic'
NEWRELIC: 2014-04-16 10:44:32 (20306) - boot_directory =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/bootstrap'
NEWRELIC: 2014-04-16 10:44:32 (20306) - program_exe_path =
'/Users/graham/Work/python_agent/test-env/bin/python'
NEWRELIC: 2014-04-16 10:44:32 (20306) - execl_arguments =
['/Users/graham/Work/python_agent/test-env/bin/python', 'python']
NEWRELIC: 2014-04-16 10:44:32 (20306) - New Relic Bootstrap
(/Users/graham/Work/python_agent/test-env/lib/python2.7/site-packages/newrelic-2
.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/bootstrap/sitecustomize.pyc)
NEWRELIC: 2014-04-16 10:44:32 (20306) - working_directory =
'/Users/graham/Work/python_agent'
NEWRELIC: 2014-04-16 10:44:32 (20306) - sys.prefix =
'/Users/graham/Work/python_agent/test-env'
NEWRELIC: 2014-04-16 10:44:32 (20306) - sys.real_prefix =
'/System/Library/Frameworks/Python.framework/Versions/2.7'
NEWRELIC: 2014-04-16 10:44:32 (20306) - sys.version_info =
sys.version_info(major=2, minor=7, micro=2, releaselevel='final', serial=0)
NEWRELIC: 2014-04-16 10:44:32 (20306) - sys.executable =
'/Users/graham/Work/python_agent/test-env/bin/python'
NEWRELIC: 2014-04-16 10:44:32 (20306) - sys.flags = sys.flags(debug=0,
py3k_warning=0, division_warning=0, division_new=0, inspect=0, interactive=0,
optimize=0, dont_write_bytecode=0, no_user_site=0, no_site=0,
ignore_environment=0, tabcheck=0, verbose=0, unicode=0, bytes_warning=0)
NEWRELIC: 2014-04-16 10:44:32 (20306) - sys.path = [...]
NEWRELIC: 2014-04-16 10:44:32 (20306) - NEW_RELIC_ADMIN_COMMAND =
"['/Users/graham/Work/python_agent/test-env/bin/newrelic-admin', 'run-program',
'python']"
NEWRELIC: 2014-04-16 10:44:32 (20306) - NEW_RELIC_PYTHON_PREFIX =
'/Users/graham/Work/python_agent/test-env'
NEWRELIC: 2014-04-16 10:44:32 (20306) - NEW_RELIC_PYTHON_VERSION = '2.7'
NEWRELIC: 2014-04-16 10:44:32 (20306) - NEW_RELIC_STARTUP_DEBUG = 'true'
NEWRELIC: 2014-04-16 10:44:32 (20306) - PYTHONPATH =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/bootstrap'
NEWRELIC: 2014-04-16 10:44:32 (20306) - root_directory =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg'
NEWRELIC: 2014-04-16 10:44:32 (20306) - boot_directory =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/bootstrap'
NEWRELIC: 2014-04-16 10:44:32 (20306) - python_prefix_matches = True
NEWRELIC: 2014-04-16 10:44:32 (20306) - python_version_matches = True
NEWRELIC: 2014-04-16 10:44:32 (20306) - initialize_agent = False
Python 2.7.2 (default, Oct 11 2012, 20:14:37)
[GCC 4.2.1 Compatible Apple Clang 4.0 (tags/Apple/clang-418.0.60)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

Important to note in this output is the lines:

```
NEWRELIC: 2014-04-16 10:44:32 (20306) - python_prefix_matches = True
NEWRELIC: 2014-04-16 10:44:32 (20306) - python_version_matches = True
```

These must both show ``True``. If they don't it means that step 2 above where it
checks for mixed Python installations has failed. The agent will consequently
not do anything.

For example, if ``newrelic-admin`` is in a Python virtual environment, but was
run against a program which actually used system Python, we would get the
following.

```
(test-env)grumpy-old-man:python_agent graham$ NEW_RELIC_STARTUP_DEBUG=true
newrelic-admin run-program /usr/bin/python
NEWRELIC: 2014-04-16 10:47:22 (20325) - New Relic Admin Script
(/Users/graham/Work/python_agent/test-env/lib/python2.7/site-packages/newrelic-2
.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/admin/run_program.pyc)
NEWRELIC: 2014-04-16 10:47:22 (20325) - working_directory =
'/Users/graham/Work/python_agent'
NEWRELIC: 2014-04-16 10:47:22 (20325) - current_command =
['/Users/graham/Work/python_agent/test-env/bin/newrelic-admin', 'run-program',
'/usr/bin/python']
NEWRELIC: 2014-04-16 10:47:22 (20325) - sys.prefix =
'/Users/graham/Work/python_agent/test-env'
NEWRELIC: 2014-04-16 10:47:22 (20325) - sys.real_prefix =
'/System/Library/Frameworks/Python.framework/Versions/2.7'
NEWRELIC: 2014-04-16 10:47:22 (20325) - sys.version_info =
sys.version_info(major=2, minor=7, micro=2, releaselevel='final', serial=0)
NEWRELIC: 2014-04-16 10:47:22 (20325) - sys.executable =
'/Users/graham/Work/python_agent/test-env/bin/python'
NEWRELIC: 2014-04-16 10:47:22 (20325) - sys.flags = sys.flags(debug=0,
py3k_warning=0, division_warning=0, division_new=0, inspect=0, interactive=0,
optimize=0, dont_write_bytecode=0, no_user_site=0, no_site=0,
ignore_environment=0, tabcheck=0, verbose=0, unicode=0, bytes_warning=0)
NEWRELIC: 2014-04-16 10:47:22 (20325) - sys.path = [...]
NEWRELIC: 2014-04-16 10:47:22 (20325) - NEW_RELIC_STARTUP_DEBUG = 'true'
NEWRELIC: 2014-04-16 10:47:22 (20325) - root_directory =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic'
NEWRELIC: 2014-04-16 10:47:22 (20325) - boot_directory =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/bootstrap'
NEWRELIC: 2014-04-16 10:47:22 (20325) - program_exe_path = '/usr/bin/python'
NEWRELIC: 2014-04-16 10:47:22 (20325) - execl_arguments = ['/usr/bin/python',
'/usr/bin/python']
NEWRELIC: 2014-04-16 10:47:22 (20325) - New Relic Bootstrap
(/Users/graham/Work/python_agent/test-env/lib/python2.7/site-packages/newrelic-2
.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/bootstrap/sitecustomize.pyc)
NEWRELIC: 2014-04-16 10:47:22 (20325) - working_directory =
'/Users/graham/Work/python_agent'
NEWRELIC: 2014-04-16 10:47:22 (20325) - sys.prefix =
'/System/Library/Frameworks/Python.framework/Versions/2.7'
NEWRELIC: 2014-04-16 10:47:22 (20325) - sys.version_info =
sys.version_info(major=2, minor=7, micro=2, releaselevel='final', serial=0)
NEWRELIC: 2014-04-16 10:47:22 (20325) - sys.executable = '/usr/bin/python'
NEWRELIC: 2014-04-16 10:47:22 (20325) - sys.flags = sys.flags(debug=0,
py3k_warning=0, division_warning=0, division_new=0, inspect=0, interactive=0,
optimize=0, dont_write_bytecode=0, no_user_site=0, no_site=0,
ignore_environment=0, tabcheck=0, verbose=0, unicode=0, bytes_warning=0)
NEWRELIC: 2014-04-16 10:47:22 (20325) - sys.path = [...]
NEWRELIC: 2014-04-16 10:47:22 (20325) - NEW_RELIC_ADMIN_COMMAND =
"['/Users/graham/Work/python_agent/test-env/bin/newrelic-admin', 'run-program',
'/usr/bin/python']"
NEWRELIC: 2014-04-16 10:47:22 (20325) - NEW_RELIC_PYTHON_PREFIX =
'/Users/graham/Work/python_agent/test-env'
NEWRELIC: 2014-04-16 10:47:22 (20325) - NEW_RELIC_PYTHON_VERSION = '2.7'
NEWRELIC: 2014-04-16 10:47:22 (20325) - NEW_RELIC_STARTUP_DEBUG = 'true'
NEWRELIC: 2014-04-16 10:47:22 (20325) - PYTHONPATH =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/bootstrap'
NEWRELIC: 2014-04-16 10:47:22 (20325) - root_directory =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg'
NEWRELIC: 2014-04-16 10:47:22 (20325) - boot_directory =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/bootstrap'
NEWRELIC: 2014-04-16 10:47:22 (20325) - python_prefix_matches = False
NEWRELIC: 2014-04-16 10:47:22 (20325) - python_version_matches = True
Python 2.7.2 (default, Oct 11 2012, 20:14:37)
[GCC 4.2.1 Compatible Apple Clang 4.0 (tags/Apple/clang-418.0.60)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

In other words, the ``sys.prefix`` test failed.

Similarly, if run ``newrelic-admin`` against program which uses a different
Python version, we would get the following.

```
(test-env)grumpy-old-man:python_agent graham$ NEW_RELIC_STARTUP_DEBUG=true
newrelic-admin run-program python2.6
NEWRELIC: 2014-04-16 10:49:39 (20340) - New Relic Admin Script
(/Users/graham/Work/python_agent/test-env/lib/python2.7/site-packages/newrelic-2
.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/admin/run_program.pyc)
NEWRELIC: 2014-04-16 10:49:39 (20340) - working_directory =
'/Users/graham/Work/python_agent'
NEWRELIC: 2014-04-16 10:49:39 (20340) - current_command =
['/Users/graham/Work/python_agent/test-env/bin/newrelic-admin', 'run-program',
'python2.6']
NEWRELIC: 2014-04-16 10:49:39 (20340) - sys.prefix =
'/Users/graham/Work/python_agent/test-env'
NEWRELIC: 2014-04-16 10:49:39 (20340) - sys.real_prefix =
'/System/Library/Frameworks/Python.framework/Versions/2.7'
NEWRELIC: 2014-04-16 10:49:39 (20340) - sys.version_info =
sys.version_info(major=2, minor=7, micro=2, releaselevel='final', serial=0)
NEWRELIC: 2014-04-16 10:49:39 (20340) - sys.executable =
'/Users/graham/Work/python_agent/test-env/bin/python'
NEWRELIC: 2014-04-16 10:49:39 (20340) - sys.flags = sys.flags(debug=0,
py3k_warning=0, division_warning=0, division_new=0, inspect=0, interactive=0,
optimize=0, dont_write_bytecode=0, no_user_site=0, no_site=0,
ignore_environment=0, tabcheck=0, verbose=0, unicode=0, bytes_warning=0)
NEWRELIC: 2014-04-16 10:49:39 (20340) - sys.path = [...]
NEWRELIC: 2014-04-16 10:49:39 (20340) - NEW_RELIC_STARTUP_DEBUG = 'true'
NEWRELIC: 2014-04-16 10:49:39 (20340) - root_directory =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic'
NEWRELIC: 2014-04-16 10:49:39 (20340) - boot_directory =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/bootstrap'
NEWRELIC: 2014-04-16 10:49:39 (20340) - program_exe_path = '/usr/bin/python2.6'
NEWRELIC: 2014-04-16 10:49:39 (20340) - execl_arguments = ['/usr/bin/python2.6',
'python2.6']
NEWRELIC: 2014-04-16 10:49:39 (20340) - New Relic Bootstrap
(/Users/graham/Work/python_agent/test-env/lib/python2.7/site-packages/newrelic-2
.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/bootstrap/sitecustomize.py)
NEWRELIC: 2014-04-16 10:49:39 (20340) - working_directory =
'/Users/graham/Work/python_agent'
NEWRELIC: 2014-04-16 10:49:39 (20340) - sys.prefix =
'/System/Library/Frameworks/Python.framework/Versions/2.6'
NEWRELIC: 2014-04-16 10:49:39 (20340) - sys.version_info = (2, 6, 7, 'final', 0)
NEWRELIC: 2014-04-16 10:49:39 (20340) - sys.executable = '/usr/bin/python2.6'
NEWRELIC: 2014-04-16 10:49:39 (20340) - sys.flags = sys.flags(debug=0,
py3k_warning=0, division_warning=0, division_new=0, inspect=0, interactive=0,
optimize=0, dont_write_bytecode=0, no_user_site=0, no_site=0,
ignore_environment=0, tabcheck=0, verbose=0, unicode=0, bytes_warning=0)
NEWRELIC: 2014-04-16 10:49:39 (20340) - sys.path = [...]
NEWRELIC: 2014-04-16 10:49:39 (20340) - NEW_RELIC_ADMIN_COMMAND =
"['/Users/graham/Work/python_agent/test-env/bin/newrelic-admin', 'run-program',
'python2.6']"
NEWRELIC: 2014-04-16 10:49:39 (20340) - NEW_RELIC_PYTHON_PREFIX =
'/Users/graham/Work/python_agent/test-env'
NEWRELIC: 2014-04-16 10:49:39 (20340) - NEW_RELIC_PYTHON_VERSION = '2.7'
NEWRELIC: 2014-04-16 10:49:39 (20340) - NEW_RELIC_STARTUP_DEBUG = 'true'
NEWRELIC: 2014-04-16 10:49:39 (20340) - PYTHONPATH =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/bootstrap'
NEWRELIC: 2014-04-16 10:49:39 (20340) - root_directory =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg'
NEWRELIC: 2014-04-16 10:49:39 (20340) - boot_directory =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/bootstrap'
NEWRELIC: 2014-04-16 10:49:39 (20340) - python_prefix_matches = False
NEWRELIC: 2014-04-16 10:49:39 (20340) - python_version_matches = False
Python 2.6.7 (r267:88850, Oct 11 2012, 20:15:00)
[GCC 4.2.1 Compatible Apple Clang 4.0 (tags/Apple/clang-418.0.60)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

So both ``sys.prefix`` and ``sys.version_info[:2]`` tests failed.

A final case is where ``PYTHONPATH`` was overridden by the script being run and
so ``sitecustomize.py`` isn't imported. In this case, you will only see half of
the above log output.

```
(test-env)grumpy-old-man:python_agent graham$ NEW_RELIC_STARTUP_DEBUG=true
newrelic-admin run-program /bin/sh
NEWRELIC: 2014-04-17 11:19:14 (34913) - New Relic Admin Script
(/Users/graham/Work/python_agent/test-env/lib/python2.7/site-packages/newrelic-2
.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/admin/run_program.pyc)
NEWRELIC: 2014-04-17 11:19:14 (34913) - working_directory =
'/Users/graham/Work/python_agent'
NEWRELIC: 2014-04-17 11:19:14 (34913) - current_command =
['/Users/graham/Work/python_agent/test-env/bin/newrelic-admin', 'run-program',
'/bin/sh']
NEWRELIC: 2014-04-17 11:19:14 (34913) - sys.prefix =
'/Users/graham/Work/python_agent/test-env'
NEWRELIC: 2014-04-17 11:19:14 (34913) - sys.real_prefix =
'/System/Library/Frameworks/Python.framework/Versions/2.7'
NEWRELIC: 2014-04-17 11:19:14 (34913) - sys.version_info =
sys.version_info(major=2, minor=7, micro=2, releaselevel='final', serial=0)
NEWRELIC: 2014-04-17 11:19:14 (34913) - sys.executable =
'/Users/graham/Work/python_agent/test-env/bin/python'
NEWRELIC: 2014-04-17 11:19:14 (34913) - sys.flags = sys.flags(debug=0,
py3k_warning=0, division_warning=0, division_new=0, inspect=0, interactive=0,
optimize=0, dont_write_bytecode=0, no_user_site=0, no_site=0,
ignore_environment=0, tabcheck=0, verbose=0, unicode=0, bytes_warning=0)
NEWRELIC: 2014-04-17 11:19:14 (34913) - sys.path = [...]
NEWRELIC: 2014-04-17 11:19:14 (34913) - NEW_RELIC_STARTUP_DEBUG = 'true'
NEWRELIC: 2014-04-17 11:19:14 (34913) - root_directory =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic'
NEWRELIC: 2014-04-17 11:19:14 (34913) - boot_directory =
'/Users/graham/Work/python_agent/test-env/lib/python2.7/site-
packages/newrelic-2.19.0.0-py2.7-macosx-10.8-intel.egg/newrelic/bootstrap'
NEWRELIC: 2014-04-17 11:19:14 (34913) - program_exe_path = '/bin/sh'
NEWRELIC: 2014-04-17 11:19:14 (34913) - execl_arguments = ['/bin/sh', '/bin/sh']
```

In this case, the last line will be ``execl_arguments`` value. There will be no
'New Relic Bootstrap' section in the output as ``sitecustomize.py`` was never
imported.
