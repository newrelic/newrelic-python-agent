import sys
import types

from newrelic.agent import (wrap_function_wrapper, current_transaction,
    FunctionTrace, callable_name, FunctionWrapper)

module_gen = None

class GeneratorReturn(Exception): pass

def generator_wrapper(name):
    def _generator_wrapper(generator):
        try:
            value = None
            exc = None

            while True:
                transaction = current_transaction()

                params = {}

                gi_frame = generator.gi_frame

                params['filename'] = gi_frame.f_code.co_filename
                params['lineno'] = gi_frame.f_lineno

                with FunctionTrace(transaction, name, params=params):
                    try:
                        if exc is not None:
                            yielded = generator.throw(*exc)
                            exc = None
                        else:
                            yielded = generator.send(value)

                    except (GeneratorReturn, StopIteration):
                        raise

                    except Exception:
                        if transaction:
                            transaction.record_exception()
                        raise

                try:
                    value = yield yielded

                except Exception:
                    exc = sys.exc_info()

        finally:
            generator.close()

    return _generator_wrapper

def generator_function_wrapper(name):
    def _generator_function_wrapper(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)

        except (GeneratorReturn, StopIteration):
            raise

        except Exception:
            raise

        else:
            if isinstance(result, types.GeneratorType):
                wrapper = generator_wrapper(name)
                result = wrapper(result)

            return result

        finally:
            pass

    return _generator_function_wrapper

def coroutine_wrapper(wrapped, instance, args, kwargs):
    def _args(func, *args, **kwargs):
        return func

    func = _args(*args, **kwargs)

    name = callable_name(func)
    name = '%s (generator)' % name

    wrapper = generator_function_wrapper(name)
    func = FunctionWrapper(func, wrapper)

    return wrapped(func)

def task_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    name = callable_name(instance.func)

    with FunctionTrace(transaction, name):
        return wrapped(*args, **kwargs)

def instrument_tornado_gen(module):
    global module_gen
    module_gen = module

    global GeneratorReturn

    if hasattr(module, 'Return'):
        GeneratorReturn = module.Return

    if hasattr(module, 'coroutine'):
        wrap_function_wrapper(module, 'coroutine', coroutine_wrapper)

    if hasattr(module, 'engine'):
        wrap_function_wrapper(module, 'engine', coroutine_wrapper)

    if hasattr(module, 'Task'):
        if hasattr(module.Task, 'start'):
            # The start() method only existed prior to Tornado 4.0.

            wrap_function_wrapper(module, 'Task.start', task_wrapper)
