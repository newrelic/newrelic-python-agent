try:
    from collections import namedtuple
except ImportError:
    from newrelic.lib.namedtuple import namedtuple

ErrorNode = namedtuple('ErrorNode',
        ['timestamp', 'type', 'message', 'stack_trace', 'custom_params',
        'file_name', 'line_number', 'source'])
