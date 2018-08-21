import tempfile

import newrelic.common.log_file
import newrelic.config

from newrelic.admin.generate_config import generate_config

_newrelic_ini = tempfile.NamedTemporaryFile()
generate_config(('BOGUS LICENSE KEY HERE', _newrelic_ini.name))


class TimeInitialize(object):

    params = (None, _newrelic_ini.name)
    param_names = ('config_file', )

    def time_initialize(self, config_file):
        newrelic.common.log_file._initialized = False
        newrelic.config._configuration_done = False
        newrelic.config._instrumentation_done = False
        newrelic.config._data_sources_done = False
        newrelic.config.initialize(config_file=config_file, log_file='stdout')
