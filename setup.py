from distutils.core import setup, Extension

sources = [
  "wrapper/_newrelicmodule.c",
  "agent/generic_object.c",
  "agent/logging.c",
  "agent/web_transaction.c",
  "agent/daemon_protocol.c",
  "agent/application.c",
  "agent/harvest.c",
  "agent/metric_table.c",
  "agent/params.c",
  "agent/samplers.c",
  "agent/environment.c",
  "agent/newrelic.c",
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
