from distutils.core import setup, Extension
import sys

sources = [
  "agent/application.c",
  "agent/daemon_protocol.c",
  "agent/genericobject.c",
  "agent/globals.c",
  "agent/harvest.c",
  "agent/logging.c",
  "agent/metric_table.c",
  "agent/nrbuffer.c",
  "agent/nrthread.c",
  "agent/samplers.c",
  "agent/utils.c",
  "agent/web_transaction.c",
  "agent/wt_error.c",
  "agent/wt_external.c",
  "agent/wt_function.c",
  "agent/wt_memcache.c",
  "agent/wt_params.c",
  "agent/wt_sql.c",
  "agent/wt_utils.c",
  "wrapper/_newrelicmodule.c",
  "wrapper/py_application.c",
  "wrapper/py_background_task.c",
  "wrapper/py_database_trace.c",
  "wrapper/py_external_trace.c",
  "wrapper/py_function_trace.c",
  "wrapper/py_memcache_trace.c",
  "wrapper/py_pass_function.c",
  "wrapper/py_post_function.c",
  "wrapper/py_pre_function.c",
  "wrapper/py_settings.c",
  "wrapper/py_transaction.c",
  "wrapper/py_utilities.c",
  "wrapper/py_web_transaction.c",
]

define_macros = []
define_macros.append(('NEWRELIC_AGENT_LANGUAGE', '"python"'))
define_macros.append(('HAVE_CONFIG_H', '1'))

if sys.version_info[:2] < (2, 5):
    define_macros.append(('Py_ssize_t', 'int'))

extension = Extension(
  name = "_newrelic",
  sources = sources,
  define_macros = define_macros,
  include_dirs = ['..', '../php_agent'],
)

setup(
  name = "newrelic",
  description = "Python agent for NewRelic RPM",
  url = "http://www.newrelic.com",
  packages = ['newrelic'],
  ext_modules = [extension],
)
