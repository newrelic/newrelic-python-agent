# vi: set sw=4 expandtab :

from decorators import web_transaction, function_trace

def _load_object(mname, cname, fname):
    module = __import__(mname)

    for part in mname.split('.')[1:]:
        module = getattr(module, part)

    assert(mname and cname or fname)

    if cname and fname:
        parent = getattr(module, cname)
        name = fname
    elif cname and not fname:
        parent = module
        name = cname
    elif not cname and fname:
        parent = module
        name = fname

    object = getattr(parent, name)

    return (parent, name, object)

def _object_path(mname, cname, fname):
    path = mname

    if cname:
        path += '.'
        path += cname

    if fname:
        path += ':'
        path += fname

    return path

# TODO These should set __module__, __name__, __doc__ and update
# __dict__ to preserve introspection capabilities. See @wraps in
# functools of recent Python versions.

def _pre_function(pre_function):
    def decorator(function):
        def wrapper(*args, **kwargs):
            pre_function(*args, **kwargs)
            result = function(*args, **kwargs)
            return result
        return wrapper
    return decorator

def _wrap_pre_function(mname, cname, fname, function):
    parent, name, object = _load_object(mname, cname, fname)
    wrapper = _pre_function(function)(object)
    setattr(parent, name, wrapper)

def _post_function(post_function):
    def decorator(function):
        def wrapper(*args, **kwargs):
            result = function(*args, **kwargs)
            post_function(*args, **kwargs)
            return result
        return wrapper
    return decorator

def _wrap_post_function(mname, cname, fname, function):
    parent, name, object = _load_object(mname, cname, fname)
    wrapper = _post_function(function)(object)
    setattr(parent, name, wrapper)

def _pass_function(pass_function):
    def decorator(function):
        def wrapper(*args, **kwargs):
            return pass_function(function(*args, **kwargs))
        return wrapper
    return decorator

def _wrap_pass_function(mname, cname, fname, function):
    parent, name, object = _load_object(mname, cname, fname)
    wrapper = _pass_function(function)(object)
    setattr(parent, name, wrapper)

def _wrap_web_transaction(mname, cname, fname, application):
    parent, name, object = _load_object(mname, cname, fname)
    wrapper = web_transaction(application)(object)
    setattr(parent, name, wrapper)

def _wrap_function_trace(mname, cname, fname):
    parent, name, object = _load_object(mname, cname, fname)
    wrapper = function_trace(_object_path(mname, cname, fname))(object)
    setattr(parent, name, wrapper)
