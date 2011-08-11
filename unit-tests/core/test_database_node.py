import unittest

import newrelic.core.database_node

class DatabaseNodeTest(unittest.TestCase):
    def setUp(self):
        self.database_node = newrelic.core.database_node.DatabaseNode(
            database_module=None,
            connect_params=None,
            sql=None,
            children=None,
            start_time=1,
            end_time=5,
            duration=2,
            exclusive=1,
            stack_trace=None)

    def test_metric_name_for_select(self):
        sql = 'SELECT * FROM dude'
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/dude/select", select_node.metric_name())

    def test_metric_name_for_select_with_double_quotes(self):
        sql = 'SELECT * FROM "dude"'
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/dude/select", select_node.metric_name())

    def test_metric_name_for_select_with_back_ticks(self):
        sql = 'SELECT * FROM `dude`'
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/dude/select", select_node.metric_name())

    def test_metric_name_for_select_with_brackets(self):
        sql = 'SELECT * FROM [dude]'
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/dude/select", select_node.metric_name())

    def test_metric_name_comment_in_front(self):
        sql = '''
-- ignore the comment
select * from dude
'''
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/dude/select", select_node.metric_name())
        
    def test_metric_name_comment_in_middle(self):
        sql = 'select * /* ignore the comment */ from dude'
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/dude/select", select_node.metric_name())

    def test_metric_name_multi_line(self):
        sql = "Select *\nfrom MAN\nwhere id = 5"
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/man/select", select_node.metric_name())

    def test_metric_name_select_multiple_tables(self):
        sql = "SELECT * FROM man, dude where dude.id = man.id"
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/man/select", select_node.metric_name())

    def test_metric_name_update(self):
        sql = "Update  dude set man = 'yeah' where id = 666"
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/dude/update", select_node.metric_name())

    def test_metric_name_set(self):
        sql = "SET character_set_results=NULL"
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/character_set_results/set", 
                         select_node.metric_name())        

    def test_metric_name_insert_with_select(self):
        sql = "INSERT into   cars  select * from man"
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/cars/insert", 
                         select_node.metric_name())        

    def test_metric_name_insert_with_values(self):
        sql = "insert   into test(id, name) values(6, 'Bubba')"
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/test/insert", 
                         select_node.metric_name())        

    def test_metric_name_delete(self):
        sql = "delete from actors where title = 'The Dude'"
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/actors/delete", 
                         select_node.metric_name())        

    def test_metric_name_create_table(self):
        sql = "create table actors as select * from dudes"
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/table/create", 
                         select_node.metric_name())        

    def test_metric_name_create_proceedure(self):
        sql = "create procedure actors as select * from dudes"
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/procedure/create", 
                         select_node.metric_name())        
        
    def test_metric_name_call_stored_proc(self):
        sql = "CALL proc(@var)"
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/proc/ExecuteProcedure", 
                         select_node.metric_name())

    def test_metric_name_show(self):
        sql = "show stuff"
        select_node = self.database_node._replace(sql=sql)
        self.assertEqual("Database/stuff/show",
                         select_node.metric_name())

    def test_metric_name_commit(self):
        sql = "commit"
        parsed_sql = newrelic.core.database_node.SqlParser(sql)
        self.assertEqual(None, parsed_sql.table)
        self.assertEqual('commit', parsed_sql.operation)

    def test_metric_name_rollback(self):
        sql = "rollback"
        parsed_sql = newrelic.core.database_node.SqlParser(sql)
        self.assertEqual(None, parsed_sql.table)
        self.assertEqual('rollback', parsed_sql.operation)

if __name__ == '__main__':
    unittest.main()
