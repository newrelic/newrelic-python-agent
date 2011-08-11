import collections

ErrorNode = collections.namedtuple('ErrorNode',
        ['type', 'message', 'stack_trace', 'custom_params',
        'file_name', 'line_number', 'source'])
