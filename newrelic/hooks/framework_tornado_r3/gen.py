import logging

from newrelic.agent import (callable_name, function_wrapper,
    wrap_function_wrapper)
from .util import retrieve_current_transaction

_logger = logging.getLogger(__name__)

try:
    # sys._getframe is not part of the python spec and is not guaranteed to
    # exist in all python implemenations. However, it does exists in the
    # reference implemenations of cpython 2, 3 and in pypy.
    # It is about 3 orders of magnitude faster than inspect in python 2.7
    # on my laptop. Inspect touches the disk to get filenames and possibly
    # other information which we don't need.
    import sys
    get_frame = sys._getframe
except:
    import inspect
    def getframe(depth):
        return inspect.stack(0)[depth]
    get_frame = getframe


# To pass the name of the coroutine back we attach it as an attribute to a
# returned value. If this returned value is None, we instead pass up a
# NoneProxy object with the attribute. When the attribute is consumed we must
# restore the None value.
class NoneProxy(object):
    pass

def _coroutine_name(func):
    # Because of how coroutines get scheduled they will look like plain
    # functions (and not methods) in python 2 and will not have a class
    # associated with them. In particular, func will not have the attribute
    # im_class. This means callable_name will return the function name without
    # the class prefix. See PYTHON-1798.
    return '%s %s' % (callable_name(func), '(coroutine)')

def _nr_wrapper_Runner__init__(wrapped, instance, args, kwargs):
    # We want to associate a function name from _make_coroutine_wrapper with
    # a call to Runner.__init__. This way we know the name of the function
    # running in Runner and can associate metrics with it.
    # One strategy would be to store the function name on the transaction.
    # This can be problematic because an asynchronous/blocking call can occur
    # in _make_coroutine_wrapper.wrapper before the call to Runner.__init__.
    # This means other coroutines could run in the transaction between when we
    # record the function name in the transaction and before Runner.__init__
    # is called. Since these coroutines run asynchronously and don't nest, we
    # can't use a stack to keep track of which _make_coroutine_wrapper.wrapper
    # call belongs to which Runner.__init__ call.
    # Instead of storing the name in the transaction, we will look up the call
    # stack to get the function name.

    transaction = retrieve_current_transaction()
    if transaction is None:
        return wrapped(*args, **kwargs)

    try:
        # The only place in the Tornado code where a Runner is instantiated
        # is in _make_coroutine_wrapper in Tornado's gen.py. We look up the
        # stack from this call to __init__ to get the function name.
        # In Python 2 we look up one frame. In Python 3 and PyPy, our wrapping
        # gets in the way and we have to look up 2 frames. In general, we want
        # to go up the call stack until we first encounter the tornado.gen
        # module. We verify that the first or second frame outside of
        # this function is in tornado.gen.
        frame_record = get_frame(1)
        if frame_record.f_globals['__name__'] != 'tornado.gen':
            frame_record = get_frame(2)

    except ValueError:
        _logger.debug('tornado.gen.Runner is being created at the top of the '
                'stack. That means the Runner object is being created outside '
                'of a tornado.gen decorator. NewRelic will not be able to '
                'name this instrumented function meaningfully (it will be '
                'named lambda.')
        return wrapped(*args, **kwargs)

    if ('__name__' in frame_record.f_globals and
            frame_record.f_globals['__name__'] == 'tornado.gen' and
            'func' in frame_record.f_locals):
        instance._nr_coroutine_name = _coroutine_name(
                frame_record.f_locals['func'])
    else:
        _logger.debug('tornado.gen.Runner is being called outside of a '
                'tornado.gen decorator. NewRelic will not be able to name '
                'this instrumented function meaningfully (it will be named '
                'lambda).')

    return wrapped(*args, **kwargs)

def _nr_wrapper_Runner_run_(wrapped, instance, args, kwargs):
    # We attach the running coroutine name as an attribute on the runner
    # result. The consumer of the name should also check if the result is
    # NoneProxy and, if so, set it to None before passing the result up.

    result = wrapped(*args, **kwargs)

    transaction = retrieve_current_transaction()
    if transaction is None:
        return result

    if result is None:
        result = NoneProxy()

    if (hasattr(instance, '_nr_coroutine_name') and
            instance._nr_coroutine_name is not None):
        result._nr_coroutine_name = instance._nr_coroutine_name

    return result

def instrument_tornado_gen(module):
    wrap_function_wrapper(module, 'Runner.__init__', _nr_wrapper_Runner__init__)
    wrap_function_wrapper(module, 'Runner.run', _nr_wrapper_Runner_run_)
