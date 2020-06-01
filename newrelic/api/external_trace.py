import functools

from newrelic.common.async_wrapper import async_wrapper
from newrelic.api.cat_header_mixin import CatHeaderMixin
from newrelic.api.time_trace import TimeTrace, current_trace
from newrelic.core.external_node import ExternalNode
from newrelic.common.object_wrapper import FunctionWrapper, wrap_object


class ExternalTrace(CatHeaderMixin, TimeTrace):

    def __init__(self, library, url, method=None, **kwargs):
        parent = None
        if kwargs:
            if len(kwargs) > 1:
                raise TypeError("Invalid keyword arguments:", kwargs)
            parent = kwargs['parent']
        super(ExternalTrace, self).__init__(parent)

        self.library = library
        self.url = url
        self.method = method
        self.params = {}

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict(
                library=self.library, url=self.url, method=self.method))

    def process_response(self, status_code, headers):
        self._add_agent_attribute('http.statusCode', status_code)
        self.process_response_headers(headers)

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
                guid=self.guid,
                agent_attributes=self.agent_attributes,
                user_attributes=self.user_attributes)


def ExternalTraceWrapper(wrapped, library, url, method=None):

    def dynamic_wrapper(wrapped, instance, args, kwargs):
        wrapper = async_wrapper(wrapped)
        if not wrapper:
            parent = current_trace()
            if not parent:
                return wrapped(*args, **kwargs)
        else:
            parent = None

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

        trace = ExternalTrace(library, _url, _method, parent=parent)

        if wrapper:
            return wrapper(wrapped, trace)(*args, **kwargs)

        with trace:
            return wrapped(*args, **kwargs)

    def literal_wrapper(wrapped, instance, args, kwargs):
        wrapper = async_wrapper(wrapped)
        if not wrapper:
            parent = current_trace()
            if not parent:
                return wrapped(*args, **kwargs)
        else:
            parent = None

        trace = ExternalTrace(library, url, method, parent=parent)

        wrapper = async_wrapper(wrapped)
        if wrapper:
            return wrapper(wrapped, trace)(*args, **kwargs)

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
