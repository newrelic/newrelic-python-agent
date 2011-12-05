import unittest

from newrelic.core.database_utils import obfuscated_sql

class TestDatabase(unittest.TestCase):
    def test_obfuscator_obfuscates_numeric_literals(self):
        select = "SELECT * FROM table WHERE table.column = 1 AND 2 = 3"
        self.assertEqual("SELECT * FROM table WHERE table.column = ? AND ? = ?",
                         obfuscated_sql('pyscopg2', select))
        insert = "INSERT INTO table VALUES (1,2, 3 ,  4)"
        self.assertEqual("INSERT INTO table VALUES (?,?, ? ,  ?)",
                         obfuscated_sql('psycopg2', insert))

    def test_obfuscator_obfuscates_string_literals(self):
        insert = "INSERT INTO X values('', 'jim''s ssn',0, 1 , 'jim''s son''s son')"
        self.assertEqual("INSERT INTO X values(?, ?,?, ? , ?)",
                         obfuscated_sql('psycopg2', insert))

    def test_obfuscator_does_not_obfuscate_table_or_column_names(self):
        select = 'SELECT "table"."column" FROM "table" WHERE "table"."column" = \'value\' LIMIT 1'
        self.assertEqual('SELECT "table"."column" FROM "table" WHERE "table"."column" = ? LIMIT ?',
                         obfuscated_sql('psycopg2', select))

    def test_mysql_obfuscation(self):
        select = 'SELECT `table`.`column` FROM `table` WHERE `table`.`column` = \'value\' AND `table`.`other_column` = "other value" LIMIT 1'
        self.assertEqual('SELECT `table`.`column` FROM `table` WHERE `table`.`column` = ? AND `table`.`other_column` = ? LIMIT ?',
                         obfuscated_sql('MySQLdb', select))

    def test_obfuscator_does_not_obfuscate_trailing_integers(self):
        select = "SELECT * FROM table1 WHERE table2.column3 = 1 AND 2 = 3"
        self.assertEqual("SELECT * FROM table1 WHERE table2.column3 = ? AND ? = ?",
                         obfuscated_sql('pyscopg2', select))

    def test_obfuscator_does_not_obfuscate_integer_word_boundaries(self):
        select = "A1 #2 ,3 .4 (5) =6 <7 :8 /9 B0C"
        self.assertEqual("A1 #? ,? .? (?) =? <? :? /? B0C",
                         obfuscated_sql('pyscopg2', select))

    def test_obfuscator_collapses_in_clause_literal(self):
        select = "SELECT column1 FROM table1 WHERE column1 IN (1,2,3)"
        self.assertEqual("SELECT column1 FROM table1 WHERE column1 IN (?)",
                         obfuscated_sql('pyscopg2', select, collapsed=True))

    def test_obfuscator_collapses_in_clause_parameterised(self):
        select = "SELECT column1 FROM table1 WHERE column1 IN (%s,%s,%s)"
        self.assertEqual("SELECT column1 FROM table1 WHERE column1 IN (?)",
                         obfuscated_sql('pyscopg2', select, collapsed=True))

if __name__ == "__main__":
    unittest.main()
