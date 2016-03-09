import tornado
import threading

from newrelic.packages import six

from tornado_base_test import TornadoBaseTest

from tornado_fixtures import (
    tornado_validate_count_transaction_metrics,
    tornado_validate_errors, tornado_validate_transaction_cache_empty)

from _test_async_application import ScheduleAndCancelExceptionRequestHandler

def select_python_version(py2, py3):
    return six.PY3 and py3 or py2

class ExceptionTest(TornadoBaseTest):

    # Tests for exceptions occuring inside of a transaction.

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[select_python_version(
            py2='exceptions:ZeroDivisionError',
            py3='builtins:ZeroDivisionError')])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:SyncExceptionRequestHandler.get')
    def test_sync_exception(self):
        self.fetch_exception('/sync-exception')

    scoped_metrics = [('Function/_test_async_application:'
            'CallbackExceptionRequestHandler.get', 1),
            ('Function/_test_async_application:'
            'CallbackExceptionRequestHandler.counter_callback', 5)]

    @tornado_validate_errors(errors=[select_python_version(
            py2='exceptions:NameError', py3='builtins:NameError')])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CallbackExceptionRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_callback_exception(self):
        self.fetch_exception('/callback-exception')

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[
            '_test_async_application:Tornado4TestException'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CoroutineExceptionRequestHandler.get')
    def test_coroutine_exception_0(self):
        r = self.fetch_exception('/coroutine-exception/0')

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[
            '_test_async_application:Tornado4TestException'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CoroutineExceptionRequestHandler.get')
    def test_coroutine_exception_1(self):
        r = self.fetch_exception('/coroutine-exception/1')

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[
            '_test_async_application:Tornado4TestException'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CoroutineException2RequestHandler.get')
    def test_coroutine_exception_2(self):
        response = self.fetch_exception('/coroutine-exception-2')

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[
            '_test_async_application:Tornado4TestException'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CallbackFromCoroutineRequestHandler.get')
    def test_callback_from_coroutine_exception(self):
        response = self.fetch_exception('/callback-from-coroutine')

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[
            '_test_async_application:Tornado4TestException'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:SyncLateExceptionRequestHandler.get')
    def test_sync_late_exception(self):
        self.fetch_response('/sync-late-exception')

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[
            '_test_async_application:Tornado4TestException'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:AsyncLateExceptionRequestHandler.get')
    def test_async_late_exception(self):
        self.fetch_response('/async-late-exception')

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[
            '_test_async_application:Tornado4TestException'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CoroutineLateExceptionRequestHandler.get')
    def test_coroutine_late_exception(self):
        self.fetch_response('/coroutine-late-exception')

    scoped_metrics = [('Function/_test_async_application:'
            'ScheduleAndCancelExceptionRequestHandler.get', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:ScheduleAndCancelExceptionRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_schedule_and_cancel_exception(self):
        response = self.fetch_response('/almost-error')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                ScheduleAndCancelExceptionRequestHandler.RESPONSE)

    # Tests for exceptions happening outside of a transaction

    def after_divide(self):
        self.stop()

    def divide_by_zero(self):
        quotient = 0
        try:
            quotient = 5/0
        finally:
            self.io_loop.add_callback(self.after_divide)
        return quotient

    def schedule_divide_by_zero(self):
        self.io_loop.add_callback(self.divide_by_zero)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[], expect_transaction=False,
            app_exceptions=[select_python_version(
                    py2='exceptions:ZeroDivisionError',
                    py3='builtins:ZeroDivisionError')])
    def test_stack_context_no_transaction_exception(self):
        # This tests that we record exceptions when they are not in a
        # transaction, but they do occur within a stack context. That is they
        # are scheduled asynchronously in a way where one wants to keep track of
        # the stack context, such as via a context manager. Just as a note,
        # it is possible for code written by an application developer to occur
        # within an ExceptionStackContext implicitly, request handlers do this
        # for example.

        # The lambda here is an exception handler which swallows the exception.
        with tornado.stack_context.ExceptionStackContext(
                lambda type, value, traceback: True):
            self.schedule_divide_by_zero()
        self.wait(timeout=5.0)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[], expect_transaction=False,
            app_exceptions=[select_python_version(
                    py2='exceptions:ZeroDivisionError',
                    py3='builtins:ZeroDivisionError')])
    def test_threaded_no_transaction_exception(self):
        # This tests that we record exceptions when an error occurs outside a
        # transaction and outside a stack context. This can be done when a job
        # is scheduled from another thread or is initiated outside of an
        # ExceptionStackContext context manager. By default, tests are run
        # inside an ExceptionStackContext so we spawn a new thread for this
        # test.
        t = threading.Thread(target=self.schedule_divide_by_zero)
        t.start()
        t.join(5.0)
        self.wait(timeout=5.0)
