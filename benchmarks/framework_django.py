import sys
import newrelic.hooks.framework_django as framework_django
from benchmarks.util import (TimeWrapBase, TimeWrappedBase,
                             TimeInstrumentBase, MagicMock)

sys.modules['django'] = MagicMock()


class TimeDjangoInstrument(TimeInstrumentBase(framework_django)):
    pass


spec = (
    ('wrap_view_handler'),
    ('wrap_view_dispatch', {
        'extra_attr': ['http_method_names', 'http_method_not_allowed']
    }),
    ('wrap_url_reverse'),
    ('wrap_url_resolver'),
    ('wrap_url_resolver_nnn', {
        'extra_attr': ['name'],
        'returned_values': 2
    }),
    ('wrap_template_block', {
        'extra_attr': ['name'],
    }),
    ('wrap_handle_uncaught_exception', {
        'wrapped_params': 3,
        'extra_attr': ['name'],
    }),
    ('wrap_leading_middleware', {
        'returns_iterable': True
    }),
    ('wrap_trailing_middleware', {
        'returns_iterable': True
    }))


class WrapFrameworkDjangoSuite(TimeWrapBase(framework_django, *spec)):
    pass


class WrappedFrameworkDjangoSuite(TimeWrappedBase(framework_django, *spec)):
    pass
