import warnings

warnings.warn((
    'All existing Tornado instrumentation and feature flags will be removed '
    'in a future release of our agent. Only Tornado 6.x and up will be '
    'supported without feature flags in a future release of the Python '
    'Agent. For more information see '
    'https://discuss.newrelic.com/t/python-tornado-support/75613'),
    DeprecationWarning)
print(
'DeprecationWarning: All existing Tornado instrumentation and feature flags '
'will be removed in a future release of our agent. Only Tornado 6.x and up '
'will be supported without feature flags in a future release of the Python '
'Agent. For more information see '
'https://discuss.newrelic.com/t/python-tornado-support/75613')
