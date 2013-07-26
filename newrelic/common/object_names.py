"""This module implements functions for deriving the full name of an object.

"""

import sys
import types
import inspect

from ..packages import six

# Object model terminology for quick reference.
#
# class:
#
#   __module__:
#     name of module in which this class was defined
#
# method:
#
#   __name__:
#     name with which this method was defined
#   __qualname__:
#     qualified name with which this method was defined
#   im_class:
#     class object that asked for this method
#   im_func or __func__:
#     function object containing implementation of method
#   im_self or __self__:
#     instance to which this method is bound, or None
#
# function:
#
#   __name__:
#     name with which this function was defined
#   __qualname__:
#     qualified name with which this function was defined
#   func_name:
#     (same as __name__)
#
# descriptor:
#
#   __objclass__:
#     class object that the descriptor is bound to
#
# builtin:
#
#   __name__:
#     original name of this function or method         
#   __self__:
#     instance to which a method is bound, or None

def _module_name(object):
    mname = None

    # For the module name we first need to deal with the special
    # case of getset and member descriptors. In this case we
    # grab the module name from the class the descriptor was
    # being used in which is held in __objclass__.

    if hasattr(object, '__objclass__'):
        mname = getattr(object.__objclass__, '__module__', None)

    # The standard case is that we can just grab the __module__
    # attribute from the object.

    if mname is None:
        mname = getattr(object, '__module__', None)

    # An exception to that is builtins or any types which are
    # implemented in C code. For that we need to grab the module
    # name from the __class__.

    if mname is None and hasattr(object, '__class__'):
        mname = getattr(object.__class__, '__module__', None)

    # Finally, if the module name isn't in sys.modules, we will
    # format it within '<>' to denote that it is a generated
    # class of some sort where a fake namespace was used. This
    # happens for example with namedtuple classes in Python 3.

    if mname and mname not in sys.modules:
        mname = '<%s>' % mname

    # If unable to derive the module name, fallback to unknown.

    if not mname:
        mname = '<unknown>'

    return mname

def _object_context_py2(object):

    cname = None
    fname = None

    if inspect.isclass(object) or isinstance(object, type):
        # Old and new style class types.

        cname = object.__name__

    elif inspect.ismethod(object):
        # Bound and unbound class methods. In the case of an
        # unbound method the im_self attribute will be None. The
        # rules around whether im_self is an instance or a class
        # type are strange so need to cope with both.

        if object.im_self is not None:
            cname = getattr(object.im_self, '__name__', None)
            if cname is None:
                cname = getattr(object.im_self.__class__, '__name__')

        else:
            cname = object.im_class.__name__

        fname = object.__name__

    elif inspect.isfunction(object):
        # Normal functions and static methods. For a static we
        # method don't know of any way of being able to work out
        # the name of the class the static method is against.

        fname = object.__name__

    elif inspect.isbuiltin(object):
        # Builtin function. Can also be be bound to class to
        # create a method. Uses __self__ instead of im_self. The
        # rules around whether __self__ is an instance or a class
        # type are strange so need to cope with both.

        if object.__self__ is not None:
            cname = getattr(object.__self__, '__name__', None)
            if cname is None:
                cname = getattr(object.__self__.__class__, '__name__')

        fname = object.__name__

    elif isinstance(object, types.InstanceType):
        # Instances of old style classes. Instances of a class
        # don't normally have __name__. Where the object has a
        # __name__, assume it is likely going to be a decorator
        # implemented as a class and don't use the class name
        # else it mucks things up.

        fname = getattr(object, '__name__', None)

        if fname is None:
            cname = object.__class__.__name__

    elif hasattr(object, '__class__'):
        # Instances of new style classes. Instances of a class
        # don't normally have __name__. Where the object has a
        # __name__, assume it is likely going to be a decorator
        # implemented as a class and don't use the class name
        # else it mucks things up. The exception to this is when
        # it is a descriptor and has __objclass__, in which case
        # the class name from __objclass__ is used.

        fname = getattr(object, '__name__', None)

        if fname is not None:
            if hasattr(object, '__objclass__'):                                 
                cname = object.__objclass__.__name__
            elif not hasattr(object, '__get__'):
                cname = object.__class__.__name__
        else:
            cname = object.__class__.__name__

    # Calculate the qualified path from the class name and the
    # function name.

    path = ''

    if cname:
        path = cname

    if fname:
        if path:
            path += '.'
        path += fname

    # Now calculate the name of the module object is defined in.

    mname = _module_name(object)

    return (mname, path)

def _object_context_py3(object):
    # For functions and methods the __qualname__ attribute gives
    # us the name. This will be a qualified name including the
    # context which the function or method is defined in, such
    # as a class, or outer function in the case of a nested
    # function. Because it includes the class, we don't need to
    # work that out separately.

    path = getattr(object, '__qualname__', None)

    # If there is no __qualname__ it should mean it is a type
    # object of some sort. In this case we use the name from the
    # __class__. That also can be nested so need to use the
    # qualified name.

    if path is None and hasattr(object, '__class__'):
        path = getattr(object.__class__, '__qualname__')

    # Now calculate the name of the module object is defined in.

    mname = _module_name(object)

    return (mname, path)

def object_context(object):
    """Returns a tuple identifying the supplied object. This will be of
    the form (module, object_path).

    """

    # Check whether the object is actually one of our own
    # wrapper classes. For these we use the convention that the
    # attribute _nr_last_object refers to the wrapped object
    # beneath the wrappers, there possibly being more than one
    # wrapper. We use this object instead and bypass any chained
    # calls that may occur through the wrappers to get the
    # attributes of the original.

    if hasattr(object, '_nr_last_object'):
        object = object._nr_last_object

    if six.PY3:
        return _object_context_py3(object)
    else:
        return _object_context_py2(object)

def callable_name(object, separator=':'):
    """Returns a string name identifying the supplied object. This will be
    of the form 'module:object_path'.

    If object were a function, then the name would be 'module:function. If
    a class, 'module:class'. If a member function, 'module:class.function'.

    By default the separator between the module path and the object path is
    ':' but can be overridden if necessary. The convention used by the
    Python Agent is that of using a ':' so it is clearer which part is the
    module name and which is the name of the object.

    """

    # Check whether we have previously calculated the name
    # details for this object and cached it against the object.
    # Do this to avoid recalculating all the time if possible.

    details = getattr(object, '_nr_object_path', None)

    # If it wasn't cached we generate the name details and then
    # attempt to cache them against the object. We may not be
    # able to cache it if it is a type implemented as C code or
    # an object with slots, which doesn't allow arbitrary
    # addition of extra attributes.

    if details is None:
        details = object_context(object)

        try:
            object._nr_object_path = details
        except Exception:
            pass

    # The details are the module name and path. Join them with
    # the specified separator.

    return separator.join(details)
