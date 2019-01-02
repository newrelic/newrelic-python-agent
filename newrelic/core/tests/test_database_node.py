import newrelic.core.database_node
from newrelic.common import system_info

HOST = 'cookiemonster'

_backup_methods = {}


def setup_module(module):

    # Mock out the calls used to create the connect payload.
    def gethostname():
        return HOST
    _backup_methods['gethostname'] = system_info.gethostname
    system_info.gethostname = gethostname


class Settings(object):
    attribute_filter = None


def teardown_module(module):
    system_info.gethostname = _backup_methods['gethostname']


_db_node = newrelic.core.database_node.DatabaseNode(
        dbapi2_module=None,
        sql='COMMIT',
        children=[],
        start_time=0.1,
        end_time=0.9,
        duration=0.8,
        exclusive=0.8,
        stack_trace=[],
        sql_format='obfuscated',
        connect_params=((), {'host': 'localhost', 'port': 1234}),
        cursor_params=None,
        sql_parameters=None,
        execute_params=None,
        host='localhost',
        port_path_or_id='1234',
        database_name='bar',
        is_async=True,
        guid=None,
        agent_attributes={},
)


def test_product_property():
    assert _db_node.product is None


def test_operation():
    assert _db_node.operation == 'commit'


def test_target():
    assert _db_node.target == ''


def test_formatted():
    assert _db_node.formatted == 'COMMIT'


def test_instance_hostname():
    assert _db_node.instance_hostname == HOST


def test_span_event():
    span_event = _db_node.span_event(Settings())
    i_attrs = span_event[0]

    # Verify that all hostnames have been converted to instance_hostname

    host, port = i_attrs['peer.address'].split(':')
    assert host == HOST
    assert port == '1234'

    assert i_attrs['peer.hostname'] == HOST
