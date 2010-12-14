from distutils.core import setup, Extension

files = [
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

extension = Extension("_newrelic", files,
  include_dirs = ['agent', '..'],
)

setup(name="newrelic",
      ext_modules=[extension],
)
