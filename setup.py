from distutils.core import setup, Extension

files = [
#  "_newrelicmodule.c",
  "generic_object.c",
  "logging.c",
  "web_transaction.c",
  "daemon_protocol.c",
  "application.c",
  "harvest.c",
  "metric_table.c",
  "params.c",
  "samplers.c",
]

extension = Extension("_newrelic", files,
  define_macros = [('ZTS', '1'), ('HAVE_CONFIG_H', '1'),],
  include_dirs = ['.'],
)

setup(name="newrelic",
      ext_modules=[extension],
)
