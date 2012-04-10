import sys
import types
import inspect

# From Python 3.X. In older Python versions it fails if attributes do
# not exist and don't maintain a __wrapped__ attribute.

WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__doc__', '__annotations__')
WRAPPER_UPDATES = ('__dict__',)

def update_wrapper(wrapper,
                   wrapped,
                   assigned = WRAPPER_ASSIGNMENTS,
                   updated = WRAPPER_UPDATES):
    """Update a wrapper function to look like the wrapped function

       wrapper is the function to be updated
       wrapped is the original function
       assigned is a tuple naming the attributes assigned directly
       from the wrapped function to the wrapper function (defaults to
       functools.WRAPPER_ASSIGNMENTS)
       updated is a tuple naming the attributes of the wrapper that
       are updated with the corresponding attribute from the wrapped
       function (defaults to functools.WRAPPER_UPDATES)
    """
    wrapper.__wrapped__ = wrapped
    for attr in assigned:
        try:
            value = getattr(wrapped, attr)
        except AttributeError:
            pass
        else:
            setattr(wrapper, attr, value)
    for attr in updated:
        getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
    # Return the wrapper so this can be used as a decorator via partial()
    return wrapper

def resolve_path(module, name):
    if not inspect.ismodule(module):
        __import__(module)
        module = sys.modules[module]

    parent = module

    path = name.split('.')
    attribute = path[0]

    original = getattr(parent, attribute)
    for attribute in path[1:]:
        parent = original
        original = getattr(original, attribute)

    return (parent, attribute, original)

def apply_patch(parent, attribute, replacement):
    setattr(parent, attribute, replacement)

def wrap_object(module, name, factory, args=()):
    (parent, attribute, original) = resolve_path(module, name)
    apply_patch(parent, attribute, factory(original, *args))

def object_context(object):
    m = inspect.getmodule(object)
    mname = m and m.__name__ or '<unknown>'

    cname = ''
    fname = ''

    if hasattr(object, '_nr_last_object'):
        object = object._nr_last_object

    # FIXME This will die if used on methods of Python objects
    # implemented in C.

    if inspect.isclass(object) or type(object) == types.TypeType:
        cname = object.__name__
        fname = ''
    elif inspect.ismethod(object):
        if object.im_self is not None and hasattr(object.im_self, '__name__'):
            cname = object.im_self.__name__
        else:
            cname = object.im_class.__name__
        fname = object.__name__
    elif inspect.isfunction(object):
        cname = ''
        fname = object.__name__
    elif type(object) == types.InstanceType:
        cname = object.__class__.__name__
        fname = ''
    elif hasattr(object, '__class__'):
        cname = object.__class__.__name__
        fname = ''

    path = ''

    if cname:
        path = cname

    if fname:
        if path:
            path += '.'
        path += fname

    return (mname, path)

def callable_name(object, separator=':'):
    if hasattr(object, '_nr_object_path'):
        name = object._nr_object_path
        if name is not None:
            return name
    (module, path) = object_context(object)
    name = "%s%s%s" % (module, separator, path)
    try:
        object._nr_object_path = name
    except:
        pass
    return name

class ObjectWrapper(object):

    def __init__(self, wrapped):
        if type(wrapped) == type(()):
            (instance, wrapped) = wrapped
        else:
            instance = None

        self._nr_instance = instance
        self._nr_next_object = wrapped

        try:
            self._nr_last_object = wrapped._nr_last_object
        except:
            self._nr_last_object = wrapped

        for attr in WRAPPER_ASSIGNMENTS:
            try:
                value = getattr(wrapped, attr)
            except AttributeError:
                pass
            else:
                object.__setattr__(self, attr, value)

    def __setattr__(self, name, value):
        if not name.startswith('_nr_'):
            setattr(self._nr_next_object, name, value)
        else:
            self.__dict__[name] = value

    def __getattr__(self, name):
        return getattr(self._nr_next_object, name)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        descriptor = self._nr_next_object.__get__(instance, owner)
        return self._nr_new_object((instance, descriptor))

    def _nr_new_object(self, wrapped):
        return self.__class__(wrapped)

    def __dir__(self):
        return dir(self._nr_next_object)

    def __call__(self, *args, **kwargs):
        return self._nr_next_object(*args, **kwargs)
