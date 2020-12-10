import random
import string
import pytest
import memcache

from testing_support.fixtures import (code_coverage_fixture,
        collector_agent_registration_fixture, collector_available_fixture)

from testing_support.db_settings import memcached_settings

_coverage_source = [
    'newrelic.api.memcache_trace',
    'newrelic.hooks.datastore_memcache',
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (datastore_memcache)',
        default_settings=_default_settings,
        linked_applications=['Python Agent Test (datastore)'])

@pytest.fixture(scope='session')
def session_initialization(code_coverage, collector_agent_registration):
    pass

@pytest.fixture(scope='function')
def requires_data_collector(collector_available_fixture):
    pass

@pytest.fixture(scope='session')
def memcached_multi():
    """Generate keys that will go onto different servers"""
    DB_SETTINGS = memcached_settings()
    db_servers = ['%s:%s' % (s['host'], s['port']) for s in DB_SETTINGS]

    clients = [memcache.Client([s]) for s in db_servers]
    client_all = memcache.Client(db_servers)
    num_servers = len(db_servers)

    for try_num in range(10 * num_servers):
        multi_dict = {}
        for i in range(num_servers):
            random_chars = (random.choice(string.ascii_uppercase)
                    for _ in range(10))
            key_candidate = ''.join(random_chars)
            multi_dict[key_candidate] = key_candidate

        client_all.set_multi(multi_dict)

        server_hit = [False] * num_servers

        for key in multi_dict.keys():
            for i in range(num_servers):
                if clients[i].get(key):
                    server_hit[i] = True

        if all(server_hit):
            break
    else:
        assert False, "memcached_multi failed to map keys to multiple servers."

    return multi_dict
