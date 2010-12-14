from distutils.core import setup, Extension

sources = [
  "agent/application.c",
  "agent/daemon_protocol.c",
  "agent/environment.c",
  "agent/generic_object.c",
  "agent/harvest.c",
  "agent/logging.c",
  "agent/metric_table.c",
  "agent/newrelic.c",
  "agent/params.c",
  "agent/samplers.c",
  "agent/web_transaction.c",
  "wrapper/_newrelicmodule.c",
  "wrapper/py_application.c",
  "wrapper/py_background_task.c",
  "wrapper/py_web_transaction.c",
]

extension = Extension(
  name = "_newrelic",
  sources = sources,
  include_dirs = ['agent', '..'],
)

setup(
  name = "newrelic",
  description = "Python agent for NewRelic RPM",
  url = "http://www.newrelic.com",
  packages = ['newrelic'],
  ext_modules = [extension],
)
