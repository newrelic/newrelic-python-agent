import sys
import newrelic.hooks.framework_django as framework_django
from benchmarks.util import (WrapBase, WrappedBase,
                             TimeInstrumentBase, MagicMock)


sys.modules['django'] = MagicMock()


class TimeDjangoInstrument(TimeInstrumentBase(framework_django)):
    pass


shared_spec = [
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
    })]


class WrapFrameworkDjangoSuite(WrapBase(framework_django, *shared_spec)):
    pass


wfw_spec = [
    ('_nr_wrapper_GZipMiddleware_process_response_', {
        'via_wrap_function_wrapper': True,
        'wrapped_params': 2,
    }),
    ('_nr_wrapper_BaseHandler_get_response_', {
        'via_wrap_function_wrapper': True,
        'wrapped_params': 2,
    }),
    ('_nr_wrapper_BaseCommand_run_from_argv_', {
        'via_wrap_function_wrapper': True,
        'extra_attr': ['handle'],
    }),
    ('_nr_wrapper_django_inclusion_tag_wrapper_', {
        'via_wrap_function_wrapper': True,
    }),
    ('_nr_wrapper_django_inclusion_tag_decorator_', {
        'via_wrap_function_wrapper': True
    }),
    ('_nr_wrapper_django_template_base_Library_inclusion_tag_', {
        'via_wrap_function_wrapper': True
    }),
    ('_nr_wrapper_django_template_base_InclusionNode_render_', {
        'via_wrap_function_wrapper': True
    }),
    ('_nr_wrapper_django_template_base_Library_tag_', {
        'via_wrap_function_wrapper': True,
        'wrapped_params': 6,
    })]


class WrappedFrameworkDjangoSuite(WrappedBase(framework_django, *(
        shared_spec + wfw_spec))):
    pass
