import functools

def data_source_generator(name=None, **properties):
    def _decorator(func):
        @functools.wraps(func)
        def _properties(settings):
            def _factory(environ):
                return func
            d = dict(properties)
            d['name'] = name
            d['factory'] = _factory
            return d
        return _properties
    return _decorator

def data_source_factory(name=None, **properties):
    def _decorator(func):
        @functools.wraps(func)
        def _properties(settings):
            def _factory(environ):
                return func(settings, environ)
            d = dict(properties)
            d['name'] = name
            d['factory'] = _factory
            return d
        return _properties
    return _decorator
