import newrelic.core.database_node
from newrelic.common import system_info

HOST='cookiemonster'

_backup_methods = {}

def setup_module(module):

    # Mock out the calls used to create the connect payload.
    def gethostname():
        return HOST
    _backup_methods['gethostname'] = system_info.gethostname
    system_info.gethostname = gethostname

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
        connect_params=((), {'host':'localhost', 'port':1234}),
        cursor_params=None,
        sql_parameters=None,
        execute_params=None,
        host='localhost',
        port_path_or_id='1234',
        database_name='bar')

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

