from testing_support.fixtures import (code_coverage_fixture,  # noqa
        collector_agent_registration_fixture, collector_available_fixture)

_default_settings = {
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True,
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (template_mako)',
        default_settings=_default_settings)

_coverage_source = [
    'newrelic.hooks.template_mako',
]

code_coverage = code_coverage_fixture(source=_coverage_source)
