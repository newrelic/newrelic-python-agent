import newrelic.core.datastore_node

from newrelic.common import system_info

HOST='foo'

_backup_methods = {}

def setup_module(module):

    # Mock out the calls used to create the connect payload.
    def gethostname():
        return HOST
    _backup_methods['gethostname'] = system_info.gethostname
    system_info.gethostname = gethostname

def teardown_module(module):
    system_info.gethostname = _backup_methods['gethostname']

_ds_node = newrelic.core.datastore_node.DatastoreNode(
        product='Redis',
        target=None,
        operation='get',
        children=[],
        start_time=0.1,
        end_time=0.9,
        duration=0.8,
        exclusive=0.8,
        host='localhost',
        port_path_or_id='1234',
        database_name='bar')

def test_instance_hostname():
    assert _ds_node.instance_hostname == HOST
