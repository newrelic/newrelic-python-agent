from collections import namedtuple

TracedError = namedtuple('TracedError',
         ['start_time','path','message','type','parameters'])

def error_parameters(uri,backtrace=[],request_params={},custom_params={}):
    params = {}

    params["request_uri"] = uri
    params["stack_trace"] = backtrace
    if len(request_params) > 0:
        params["request_params"] = request_params

    if len(custom_params) > 0:
        params["custom_params"] = custom_params

    return params
