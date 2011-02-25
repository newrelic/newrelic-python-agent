# vi: set sw=4 expandtab :

from middleware import wsgi_application
from decorators import function_trace

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
        path += '::'
        path += fname

    return path

def _wrap_wsgi_application(mname, cname, fname, application):
    parent, name, object = _load_object(mname, cname, fname)
    wrapper = wsgi_application(application)(object)
    setattr(parent, name, wrapper)

def _wrap_function_trace(mname, cname, fname, scope=None):
    parent, name, object = _load_object(mname, cname, fname)
    wrapper = function_trace(_object_path(mname, cname, fname), scope=scope)(object)
    setattr(parent, name, wrapper)
