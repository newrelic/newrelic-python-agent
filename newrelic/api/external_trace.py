import functools

from newrelic.common.coroutine import async_proxy, TraceContext
from newrelic.api.cat_header_mixin import CatHeaderMixin
from newrelic.api.time_trace import TimeTrace
from newrelic.api.transaction import current_transaction
from newrelic.core.external_node import ExternalNode
from newrelic.common.object_wrapper import FunctionWrapper, wrap_object


class ExternalTrace(TimeTrace, CatHeaderMixin):

    def __init__(self, transaction, library, url, method=None):
        super(ExternalTrace, self).__init__(transaction)

        self.library = library
        self.url = url
        self.method = method
        self.params = {}

        self.settings = self.transaction and self.transaction.settings or None

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(
                library=self.library, url=self.url, method=self.method))

    def terminal_node(self):
        return True

    def create_node(self):
        return ExternalNode(
                library=self.library,
                url=self.url,
                method=self.method,
                children=self.children,
                start_time=self.start_time,
                end_time=self.end_time,
                duration=self.duration,
                exclusive=self.exclusive,
                params=self.params,
                is_async=self.is_async,
                guid=self.guid,
                agent_attributes=self.agent_attributes)


def ExternalTraceWrapper(wrapped, library, url, method=None):

    def dynamic_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if callable(url):
            if instance is not None:
                _url = url(instance, *args, **kwargs)
            else:
                _url = url(*args, **kwargs)

        else:
            _url = url

        if callable(method):
            if instance is not None:
                _method = method(instance, *args, **kwargs)
            else:
                _method = method(*args, **kwargs)

        else:
            _method = method

        trace = ExternalTrace(transaction, library, _url, _method)

        proxy = async_proxy(wrapped)
        if proxy:
            return proxy(wrapped(*args, **kwargs), TraceContext(trace))

        with trace:
            return wrapped(*args, **kwargs)

    def literal_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        trace = ExternalTrace(transaction, library, url, method)

        proxy = async_proxy(wrapped)
        if proxy:
            return proxy(wrapped(*args, **kwargs), TraceContext(trace))

        with trace:
            return wrapped(*args, **kwargs)

    if callable(url) or callable(method):
        return FunctionWrapper(wrapped, dynamic_wrapper)

    return FunctionWrapper(wrapped, literal_wrapper)


def external_trace(library, url, method=None):
    return functools.partial(ExternalTraceWrapper, library=library,
            url=url, method=method)


def wrap_external_trace(module, object_path, library, url, method=None):
    wrap_object(module, object_path, ExternalTraceWrapper,
            (library, url, method))
