import unittest
import newrelic.core.database_node

class TestDatabaseNodeProperties(unittest.TestCase):

    def setUp(self):
        self.db_node = newrelic.core.database_node.DatabaseNode(
                dbapi2_module=None,
                sql='COMMIT',
                children=[],
                start_time=0.1,
                end_time=0.9,
                duration=0.8,
                exclusive=0.8,
                stack_trace=[],
                sql_format='obfuscated',
                connect_params=((), {'host':'foo', 'port':1234}),
                cursor_params=None,
                sql_parameters=None,
                execute_params=None,
                host='1.2.3.4',
                port_path_or_id='1234',
                database_name='bar')

    def test_product_property(self):
        assert self.db_node.product is None

    def test_operation(self):
        assert self.db_node.operation == 'commit'

    def test_target(self):
        assert self.db_node.target == ''

    def test_formatted(self):
        assert self.db_node.formatted == 'COMMIT'

if __name__ == '__main__':
    unittest.main()
