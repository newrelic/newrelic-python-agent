from elasticsearch import Elasticsearch

from testing_support.fixtures import (validate_tt_collector_json,
    override_application_settings, validate_tt_parenting)
from testing_support.settings import elasticsearch_multiple_settings
from testing_support.util import instance_hostname

from newrelic.api.background_task import background_task

ES_SETTINGS = elasticsearch_multiple_settings()[0]
ES_URL = 'http://%s:%s' % (ES_SETTINGS['host'], ES_SETTINGS['port'])

# Settings

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
    'datastore_tracer.database_name_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
    'datastore_tracer.database_name_reporting.enabled': False,
}
_instance_only_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
    'datastore_tracer.database_name_reporting.enabled': False,
}

# Expected parameters

_enabled_required = {
    'host': instance_hostname(ES_SETTINGS['host']),
    'port_path_or_id': str(ES_SETTINGS['port']),
}
_enabled_forgone = {
    'db.instance': 'VALUE NOT USED',
}

_disabled_required = {}
_disabled_forgone = {
    'host': 'VALUE NOT USED',
    'port_path_or_id': 'VALUE NOT USED',
    'db.instance': 'VALUE NOT USED',
}

_instance_only_required = {
    'host': instance_hostname(ES_SETTINGS['host']),
    'port_path_or_id': str(ES_SETTINGS['port']),
}
_instance_only_forgone = {
    'db.instance': 'VALUE NOT USED',
}

_tt_parenting = (
    'TransactionNode', [
        ('DatastoreNode', []),
    ],
)


# Query

def _exercise_es(es):
    es.index('contacts', 'person',
            {'name': 'Joe Tester', 'age': 25, 'title': 'QA Master'}, id=1)


# Tests

@override_application_settings(_enable_instance_settings)
@validate_tt_collector_json(
        datastore_params=_enabled_required,
        datastore_forgone_params=_enabled_forgone)
@validate_tt_parenting(_tt_parenting)
@background_task()
def test_trace_node_datastore_params_enable_instance():
    client = Elasticsearch(ES_URL)
    _exercise_es(client)


@override_application_settings(_disable_instance_settings)
@validate_tt_collector_json(
        datastore_params=_disabled_required,
        datastore_forgone_params=_disabled_forgone)
@validate_tt_parenting(_tt_parenting)
@background_task()
def test_trace_node_datastore_params_disable_instance():
    client = Elasticsearch(ES_URL)
    _exercise_es(client)


@override_application_settings(_instance_only_settings)
@validate_tt_collector_json(
        datastore_params=_instance_only_required,
        datastore_forgone_params=_instance_only_forgone)
@validate_tt_parenting(_tt_parenting)
@background_task()
def test_trace_node_datastore_params_instance_only():
    client = Elasticsearch(ES_URL)
    _exercise_es(client)
