import unittest

from newrelic.core.database_utils import obfuscated_sql, parsed_sql

SQL_PARSE_TESTS = [
  (
    # Empty.
    (None, None),
    ""
  ),
  (
    # Empty (whitespace).
    (None, None),
    " "
  ),
  (
    # Invalid.
    (None, None),
    """select"""
  ),

  (
    # Select.
    ('student_details', 'select'),
    """SELECT first_name FROM student_details"""
  ),
  (
    # Select using alias.
    ('student_details', 'select'),
    """SELECT first_name Name FROM student_details"""
  ),
  (
    # Select using alias.
    ('student_details', 'select'),
    """SELECT first_name AS Name FROM student_details"""
  ),
  (
    # Select using table alias.
    ('student_details', 'select'),
    """SELECT s.first_name FROM student_details s"""
  ),
  (
    # Select using table alias.
    ('student_details', 'select'),
    """SELECT s.first_name FROM student_details AS s"""
  ),
  (
    # Select with condition.
    ('student_details', 'select'),
    """SELECT first_name, last_name FROM student_details WHERE id = 100"""
  ),
  (
    # Select with condition and alias.
    ('employee', 'select'),
    """SELECT name, salary, salary*1.2 AS new_salary FROM employee 
    WHERE salary*1.2 > 30000"""
  ),
  (
    # Select with sub query.
    ('student_details', 'select'),
    """SELECT id, first_name FROM student_details WHERE first_name
    IN (SELECT first_name FROM student_details WHERE subject= 'Science')"""
  ),
  (
    # "Select with correlated sub query using table alias.
    ('product', 'select'),
    """SELECT p.product_name FROM product p WHERE p.product_id = (SELECT
    o.product_id FROM order_items o WHERE o.product_id = p.product_id)"""
  ),
  (
    # Select with correlated sub query using table alias.
    ('employee', 'select'),
    """SELECT employee_number, name FROM employee AS e1 WHERE salary >
    (SELECT avg(salary) FROM employee WHERE department = e1.department)"""
  ),
  (
    # Select with correlated sub query using aliases.
    ('app_devicesoftware', 'select'),
    """SELECT * FROM ( SELECT s.*, ds.version AS version2, ds.installed
    FROM app_devicesoftware ds, app_software s, app_vendor v WHERE s.id =
    ds.software_id AND s.manufacturer_id = v.id AND s.manufacturer_id <> %s
    AND s.approved = true AND v.approved = True AND installed IS NOT NULL
    AND ds.version IS NOT NULL ORDER BY name ASC, ds.version DESC,
    installed ASC ) AS temp GROUP BY id ORDER BY installed DESC LIMIT ?"""
  ),
  (
    # Select with correlated sub query using aliases.
    ('app_component', 'select'),
    """SELECT COUNT(t.manufacturer_id) AS total, v.* FROM ( SELECT
    c.manufacturer_id FROM app_component c WHERE manufacturer_id <> %s GROUP BY
    c.model, c.manufacturer_id ) AS t, app_vendor v WHERE v.id =
    t.manufacturer_id AND v.approved = true GROUP BY t.manufacturer_id ORDER BY
    COUNT(t.manufacturer_id) DESC LIMIT ?"""
  ),
  (
    # Select with correlated sub query using aliases.
    ('photos', 'select'),
    """SELECT count(?) AS count_1 FROM (SELECT DISTINCT photos.id AS photos_id
    FROM photos, item_map WHERE item_map.to_id IN (%s) AND item_map.to_type =
    %s AND item_map.from_id = photos.id AND item_map.from_type = %s AND
    item_map.deleted = %s) AS anon_1"""
  ),
  (
    # Select with sub query.
    ('entity_entity', 'select'),
    """SELECT COUNT(*) FROM (SELECT "entity_entity"."id" AS "id",
    "entity_site"."id" AS Col1, "entity_site"."updated_at",
    "entity_site"."created_at", "entity_site"."domain",
    "entity_site"."popularity_multiplier", "entity_site"."clicks",
    "entity_site"."monetized_clicks", "entity_site"."epc",
    "entity_site"."commission", "entity_site"."category_id",
    "entity_site"."subdomain", "entity_site"."blocked",
    "entity_site"."in_shop_list", "entity_site"."related_user_id",
    "entity_site"."description", "entity_site"."shop_name",
    "entity_site"."order", "entity_site"."featured",
    "entity_site"."shop_data_complete", "entity_site"."shop_url" FROM
    "entity_entity" LEFT OUTER JOIN "entity_site" ON
    ("entity_entity"."site_id" = "entity_site"."id")
    WHERE (NOT (("entity_site"."category_id" IN (%s, %s) AND NOT
    ("entity_site"."id" IS NULL))) AND "entity_entity"."id" <= %s
    ) LIMIT ?) subquery"""
  ),

  (
    # Delete.
    ('employee', 'delete'),
    """DELETE FROM employee"""
  ),
  (
    # Delete with condition.
    ('employee', 'delete'),
    """DELETE FROM employee WHERE id = 100"""
  ),
  (
    # Delete with sub query.
    ('t1', 'delete'),
    """DELETE FROM t1 WHERE s11 > ANY (SELECT COUNT(*) /* no hint */ FROM
    t2 WHERE NOT EXISTS (SELECT * FROM t3 WHERE ROW(5*t2.s1,77)= (SELECT
    50,11*s1 FROM t4 UNION SELECT 50,77 FROM (SELECT * FROM t5) AS t5)))"""
  ),

  (
    # Insert.
    ('employee', 'insert'),
    """INSERT INTO employee 
    VALUES (105, 'Srinath', 'Aeronautics', 27, 33000)"""
  ),
  (
    # Insert.
    ('employee', 'insert'),
    """INSERT INTO employee (id, name, dept, age, salary location)
    VALUES (105, 'Srinath', 'Aeronautics', 27, 33000)"""
  ),
  (
    # Insert from select.
    ('employee', 'insert'),
    """INSERT INTO employee SELECT * FROM temp_employee"""
  ),
  (
    # Insert from select.
    ('employee', 'insert'),
    """INSERT INTO employee (id, name, dept, age, salary location) SELECT
    emp_id, emp_name, dept, age, salary, location FROM temp_employee"""
  ),

  (
    # Update.
    ('employee', 'update'),
    """UPDATE employee SET location ='Mysore' WHERE id = 101"""
  ),
  (
    # Update.
    ('employee', 'update'),
    """UPDATE employee SET salary = salary + (salary * 0.2)"""
  ),

  (
    # Create.
    ('temp_employee', 'create'),
    """CREATE TABLE temp_employee SELECT * FROM employee"""
  ),
  (
    # Create.
    ('employee', 'create'),
    """CREATE TABLE employee ( id number(5), name char(20), dept char(10), 
    age number(2), salary number(10), location char(10) )"""
  ),

  (
    # Call.
    ('foo', 'call'),
    """CALL FOO(1, 2) """
  ),
  (
    # Call.
    ('foo', 'call'),
    """CALL FOO 1 2 """
  ),

  (
    # Show.
    ('profiles', 'show'),
    """SHOW PROFILES"""
  ),
  (
    # Show.
    ('columns from mytable from mydb', 'show'),
    """SHOW COLUMNS FROM mytable FROM mydb"""
  ),
  (
    # Show.
    ('columns from mydb.mytable', 'show'),
    """SHOW COLUMNS FROM mydb.mytable"""
  ),

  (
    # Set.
    ('language', 'set'),
    """SET LANGUAGE Australian"""
  ),
  (
    # Set.
    ('auto commit', 'set'),
    """SET AUTO COMMIT ON"""
  ),
  (
    # Set.
    ('transaction isolation level', 'set'),
    """SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"""
  ),
]

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

    def test_obfuscator_collapses_in_clause_very_large(self):
        select = "SELECT column1 FROM table1 WHERE column1 IN (" + \
                (50000 * "%s,") + "%s)"
        self.assertEqual("SELECT column1 FROM table1 WHERE column1 IN (?)",
                         obfuscated_sql('pyscopg2', select, collapsed=True))

    def test_obfuscator_very_large_in_clause(self):
        select = "SELECT column1 FROM table1 WHERE column1 IN (" + \
                (50000 * "%s,") + "%s)"
        self.assertEqual(('table1', 'select'), parsed_sql('pyscopg2', select))

    def test_parse_sql_tests(self):
        for result, sql in SQL_PARSE_TESTS:
            self.assertEqual(result, parsed_sql('pyscopg2', sql))

if __name__ == "__main__":
    unittest.main()
