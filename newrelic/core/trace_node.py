import collections

RootNode = collections.namedtuple('RootNode',
        ['start_time', 'request_params', 'custom_params', 'root'])

def root_start_time(root):
    return root.start_time / 1000.0

TraceNode = collections.namedtuple('TraceNode',
        ['start_time', 'end_time', 'name', 'params', 'children'])

def node_start_time(root, node):
    return int((node.start_time - root.start_time) * 1000.0)

def node_end_time(root, node):
    return int((node.end_time - root.start_time) * 1000.0)
