from testing_support.fixtures import code_coverage_fixture

_coverage_source = [
    'newrelic.config',
    'newrelic.core.config',
]

code_coverage = code_coverage_fixture(source=_coverage_source)
