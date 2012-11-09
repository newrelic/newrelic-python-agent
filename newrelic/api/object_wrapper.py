import sys
import types
import inspect

from newrelic.api.transaction import current_transaction

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

def wrap_object(module, name, factory, args=(), kwargs={}):
    (parent, attribute, original) = resolve_path(module, name)
    wrapper = factory(original, *args, **kwargs)
    apply_patch(parent, attribute, wrapper)
    return wrapper

def _module_name(object):
    if hasattr(object, '__module__'):
        if object.__module__ in sys.modules:
            return object.__module__

def object_context(object):
    if hasattr(object, '_nr_last_object'):
        object = object._nr_last_object

    mname = None
    cname = None
    fname = None

    # FIXME This will die if used on methods of Python objects
    # implemented in C.

    if inspect.isclass(object) or type(object) == types.TypeType:
        # This is called for new and old style class objects.

        mname = _module_name(object)
        cname = object.__name__
        fname = None

    elif inspect.ismethod(object):
        # This is called for both bound and unbound class methods.
        # In the case of an unbound method the im_self attribute
        # will be None.

        if object.im_self is not None and hasattr(object.im_self, '__name__'):
            mname = _module_name(object.im_self)
            cname = object.im_self.__name__

        else:
            mname = _module_name(object.im_class)
            cname = object.im_class.__name__

        fname = object.__name__

    elif inspect.isfunction(object):
        # This is called for normal functions and static methods.

        mname = _module_name(object)
        cname = None
        fname = object.__name__

    elif isinstance(object, types.InstanceType):
        # This is called for instances of old style classes.

        mname = _module_name(object)

        # Where instance has __name__ attribute, assume it is
        # likely going to be a decorator implemented as a class.

        if hasattr(object, '__name__'):
            cname = None
            fname = object.__name__
        else:
            cname = object.__class__.__name__
            fname = None

    elif hasattr(object, '__class__'):
        # This is called for instances of new style classes.

        mname = _module_name(object)

        # Where instance has __name__ attribute, assume it is
        # likely going to be a decorator implemented as a class.

        if hasattr(object, '__name__'):
            cname = None
            fname = object.__name__
        else:
            cname = object.__class__.__name__
            fname = None

    path = ''

    if not mname:
        mname = '<unknown>'

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
    
    def __init__(self, wrapped, instance, wrapper):
        self._nr_next_object = wrapped

        self._nr_instance = instance
        self._nr_wrapper = wrapper
        
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
        return self.__class__(descriptor, instance, self._nr_wrapper)

    def __enter__(self):
        return self._nr_next_object.__enter__()

    def __exit__(self, *args, **kwargs):
        return self._nr_next_object.__exit__(*args, **kwargs)

    def __dir__(self): 
        return dir(self._nr_next_object)

    def __iter__(self):
        return iter(self._nr_next_object)

    def __call__(self, *args, **kwargs):
        return self._nr_wrapper(self._nr_next_object,
                self._nr_instance, args, kwargs)

    def __eq__(self, other):
        if isinstance(other, ObjectWrapper):
            return self._nr_last_object == other._nr_last_object
        return self._nr_last_object == other

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return hash(self._nr_last_object)

    def __repr__(self): 
        return '<ObjectWrapper for %s>' % (str(self._nr_last_object))
