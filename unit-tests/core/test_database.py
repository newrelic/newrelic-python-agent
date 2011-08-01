'''
Created on Jul 27, 2011

@author: sdaubin
'''
import unittest
from newrelic.core import database

class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.obfuscator = database.obfuscator("postgresql")

    def test_obfuscator_returns_class_for_given_database_type(self):
        self.assertEqual("MysqlObfuscator", 
                         database.obfuscator("mysql").__class__.__name__)
        self.assertEqual("PostgresqlObfuscator", 
                         database.obfuscator("postgresql").__class__.__name__)
        self.assertEqual("PostgresqlObfuscator", 
                         database.obfuscator().__class__.__name__)

    def test_obfuscator_obfuscates_numeric_literals(self):
        select = "SELECT * FROM table WHERE table.column = 1 AND 2 = 3"
        self.assertEqual("SELECT * FROM table WHERE table.column = ? AND ? = ?",
                         self.obfuscator.obfuscate(select))
        insert = "INSERT INTO table VALUES (1,2, 3 ,  4)"
        self.assertEqual("INSERT INTO table VALUES (?,?, ? ,  ?)",
                         self.obfuscator.obfuscate(insert))

    def test_obfuscator_obfuscates_string_literals(self):
        insert = "INSERT INTO X values('', 'jim''s ssn',0, 1 , 'jim''s son''s son')"
        self.assertEqual("INSERT INTO X values(?, ?,?, ? , ?)",
                         self.obfuscator.obfuscate(insert))

    def test_obfuscator_does_not_obfuscate_table_or_column_names(self):
        select = 'SELECT "table"."column" FROM "table" WHERE "table"."column" = \'value\' LIMIT 1'
        self.assertEqual('SELECT "table"."column" FROM "table" WHERE "table"."column" = ? LIMIT ?',
                         self.obfuscator.obfuscate(select))

    def test_mysql_obfuscation(self):
        obfuscator = database.obfuscator("mysql")
        select = 'SELECT `table`.`column` FROM `table` WHERE `table`.`column` = \'value\' AND `table`.`other_column` = "other value" LIMIT 1'
        self.assertEqual('SELECT `table`.`column` FROM `table` WHERE `table`.`column` = ? AND `table`.`other_column` = ? LIMIT ?',
                         obfuscator.obfuscate(select))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
