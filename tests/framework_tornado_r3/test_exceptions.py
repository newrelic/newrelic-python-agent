from tornado_base_test import TornadoBaseTest

from tornado_fixtures import (
    tornado_validate_count_transaction_metrics,
    tornado_validate_errors, tornado_validate_transaction_cache_empty)

class ExceptionTest(TornadoBaseTest):

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
