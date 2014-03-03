import os
import sys
import pytest

from newrelic.core.database_utils import (_obfuscate_explain_plan_postgresql,
    _obfuscate_explain_plan_postgresql_substitute)

_test_explain_plan_obfuscation_postgresql_mask_true_tests = [

    # typed_string

    ("""'abcdef'::text""", """?::text"""),
    (""" 'abcdef'::text """, """ ?::text """),
    (""" 'abcdef'::text)""", """ ?::text)"""),
    ("""'abcdef'::"char\"""", """?::"char\""""),
    (""" 'abcdef'::"char\"""", """ ?::"char\""""),
    ("""'abcdef'::"char")""", """?::"char")"""),
    (""" 'abcdef'::"char")""", """ ?::"char")"""),
    ("""'abc''def'::text""", """?::text"""),
    ("""'123456'::text""", """?::text"""),

    # double_quotes

    ('''"'abcdef'::text"''', '''"'abcdef'::text"'''),
    ('''"abc'def"''', '''"abc'def"'''),
    ('''"abc'def" "ghi'jkl"''', '''"abc'def" "ghi'jkl"'''),
    ('''"abc'def" 'abcdef'::text''', '''"abc'def" ?::text'''),
    ('''"123456"''', '''"123456"'''),

    # single_quotes

    ("""'abcdef'""", """?"""),
    ("""'123456'""", """?"""),
    ("""'123 456'""", """?"""),
    ("""'123"456'""", """?"""),
    ("""'123"456','7"8'""", """?,?"""),

    # cost_analysis

    ("""(cost=0.00..34.00 rows=2400 width=4)""",
        """(cost=0.00..34.00 rows=2400 width=4)"""),
    (""" (cost=0.00..34.00 rows=2400 width=4)""",
        """ (cost=0.00..34.00 rows=2400 width=4)"""),
    (""" (cost=0.00..34.00 rows=2400 width=4) """,
        """ (cost=0.00..34.00 rows=2400 width=4) """),
    ("""(cost=0.00..34.00 rows=2400 width=4) """,
        """(cost=0.00..34.00 rows=2400 width=4) """),

    # sub_plan_ref

    ("""SubPlan 1""", """SubPlan 1"""),
    (""" SubPlan 1""", """ SubPlan 1"""),
    (""" SubPlan 1 """, """ SubPlan 1 """),
    ("""SubPlan 1 """, """SubPlan 1 """),
    ("""SubPlan 123""", """SubPlan 123"""),

    # init_plan_ref

    ("""InitPlan 1""", """InitPlan 1"""),
    (""" InitPlan 1""", """ InitPlan 1"""),
    (""" InitPlan 1 """, """ InitPlan 1 """),
    ("""InitPlan 1 """, """InitPlan 1 """),
    ("""InitPlan 123 """, """InitPlan 123 """),

    # dollar_var_ref

    ("""$1""", """$1"""),
    (""" $1""", """ $1"""),
    (""" $1 """, """ $1 """),
    ("""$1 """, """$1 """),
    ("""$123""", """$123"""),

]

_test_explain_plan_obfuscation_postgresql_mask_false_tests = list(
        _test_explain_plan_obfuscation_postgresql_mask_true_tests)

_test_explain_plan_obfuscation_postgresql_mask_false_tests.extend([

    # numeric_value

    ("""1""", """?"""),
    (""" 1""", """ ?"""),
    (""" 1 """, """ ? """),
    ("""1 """, """? """),
    ("""-1""", """?"""),
    (""" -1""", """ ?"""),
    (""" -1 """, """ ? """),
    ("""-1 """, """? """),
    ("""abc1""", """abc1"""),
    ("""abc_1""", """abc_1"""),
    ("""abc-1""", """abc-?"""),
    ("""1abc""", """1abc"""),
    ("""1_abc""", """1_abc"""),
    ("""1-abc""", """?-abc"""),
    ("""1.0""", """?"""),
    (""" 1.0""", """ ?"""),
    (""" 1.0 """, """ ? """),
    ("""1.0 """, """? """),
    ("""-1.0""", """?"""),
    (""" -1.0""", """ ?"""),
    (""" -1.0 """, """ ? """),
    ("""-1.0 """, """? """),
    ("""abc1.0 """, """abc1.? """),
    ("""abc_1.0 """, """abc_1.? """),
    ("""abc-1.0 """, """abc-? """),
    ("""1.0e2""", """?"""),
    (""" 1.0e2""", """ ?"""),
    (""" 1.0e2 """, """ ? """),
    ("""1.0e2 """, """? """),
    ("""1.0e22""", """?"""),
    (""" 1.0e22""", """ ?"""),
    (""" 1.0e22 """, """ ? """),
    ("""1.0e22 """, """? """),
    ("""1.0E22""", """?"""),
    (""" 1.0E22""", """ ?"""),
    (""" 1.0E22 """, """ ? """),
    ("""1.0E22 """, """? """),
    ("""1.0e-22""", """?"""),
    (""" 1.0e-22""", """ ?"""),
    (""" 1.0e-22 """, """ ? """),
    ("""1.0e-22 """, """? """),
    ("""1.0E-22""", """?"""),
    (""" 1.0E-22""", """ ?"""),
    (""" 1.0E-22 """, """ ? """),
    ("""1.0E-22 """, """? """),
    ("""1.0e+22""", """?"""),
    (""" 1.0e+22""", """ ?"""),
    (""" 1.0e+22 """, """ ? """),
    ("""1.0e+22 """, """? """),
    ("""1.0E+22""", """?"""),
    (""" 1.0E+22""", """ ?"""),
    (""" 1.0E+22 """, """ ? """),
    ("""1.0E+22 """, """? """),
    ("""-1.0e22""", """?"""),
    (""" -1.0e22""", """ ?"""),
    (""" -1.0e22 """, """ ? """),
    ("""-1.0e22 """, """? """),
    ("""-1.0e-22""", """?"""),
    (""" -1.0e-22""", """ ?"""),
    (""" -1.0e-22 """, """ ? """),
    ("""-1.0e-22 """, """? """),
    ("""-1.0e+22""", """?"""),
    (""" -1.0e+22""", """ ?"""),
    (""" -1.0e+22 """, """ ? """),
    ("""-1.0e+22 """, """? """),
    ("""abc1.0e22 """, """abc1.? """),
    ("""abc_1.0e22 """, """abc_1.? """),
    ("""abc-1.0e22 """, """abc-? """),

])

@pytest.mark.parametrize('value,expected',
        _test_explain_plan_obfuscation_postgresql_mask_false_tests)
def test_explain_plan_obfuscation_postgresql_substitute_mask_false(
        value, expected):

    output = _obfuscate_explain_plan_postgresql_substitute(value, mask=False)
    assert output == expected

@pytest.mark.parametrize('value,expected',
        _test_explain_plan_obfuscation_postgresql_mask_true_tests)
def test_explain_plan_obfuscation_postgresql_substitute_mask_true(
        value, expected):

    output = _obfuscate_explain_plan_postgresql_substitute(value, mask=True)
    assert output == expected

_test_explain_plan_obfuscation_postgresql_complete_tests = []

def _add_explain_plan_test(original, expected_simple, expected_complete):
    _test_explain_plan_obfuscation_postgresql_complete_tests.append(
            (original, expected_simple, expected_complete))

# CREATE: create table if not exists explain_plan_1 (c1 integer)
# DELETE: drop table if exists explain_plan_1

# QUERY: select * from explain_plan_1

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..34.00 rows=2400 width=4)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..34.00 rows=2400 width=4)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..34.00 rows=2400 width=4)
"""
)

# QUERY: select * from explain_plan_1 where c1 = 1

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = 1)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = ?)
"""
)

# QUERY: select * from explain_plan_1 where c1 = -1

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = -1)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = ?)
"""
)

# QUERY: select * from explain_plan_1 where c1 = 1.1;

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..46.00 rows=12 width=4)
  Filter: ((c1)::numeric = 1.1)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..46.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..46.00 rows=12 width=4)
  Filter: ((c1)::numeric = ?)
"""
)

# QUERY: select * from explain_plan_1 where c1 = -1.1;

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..46.00 rows=12 width=4)
  Filter: ((c1)::numeric = -1.1)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..46.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..46.00 rows=12 width=4)
  Filter: ((c1)::numeric = ?)
"""
)

# QUERY: select * from explain_plan_1 where c1 = 1e10

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..46.00 rows=12 width=4)
  Filter: ((c1)::numeric = 10000000000::numeric)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..46.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..46.00 rows=12 width=4)
  Filter: ((c1)::numeric = ?::numeric)
"""
)

# QUERY: select * from explain_plan_1 where c1 = -1e10

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..46.00 rows=12 width=4)
  Filter: ((c1)::numeric = (-10000000000)::numeric)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..46.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..46.00 rows=12 width=4)
  Filter: ((c1)::numeric = (?)::numeric)
"""
)

# QUERY: select * from explain_plan_1 where c1 in (1,2,3)

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..43.00 rows=36 width=4)
  Filter: (c1 = ANY ('{1,2,3}'::integer[]))
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..43.00 rows=36 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..43.00 rows=36 width=4)
  Filter: (c1 = ANY (?::integer[]))
"""
)

# QUERY: select * from explain_plan_1 where c1 in (1.1,2.2,3.3)

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..49.00 rows=36 width=4)
  Filter: ((c1)::numeric = ANY ('{1.1,2.2,3.3}'::numeric[]))
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..49.00 rows=36 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..49.00 rows=36 width=4)
  Filter: ((c1)::numeric = ANY (?::numeric[]))
"""
)

# CREATE: create table if not exists explain_plan_1 (c1 real)
# DELETE: drop table if exists explain_plan_1

# QUERY: select * from explain_plan_1 where c1 = 1.0

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = 1::double precision)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = ?::double precision)
"""
)

# QUERY: select * from explain_plan_1 where c1 = -1.0

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = (-1)::double precision)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = (?)::double precision)
"""
)

# QUERY: select * from explain_plan_1 where c1 = 1.1

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = 1.1::double precision)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = ?::double precision)
"""
)

# QUERY: select * from explain_plan_1 where c1 = -1.1

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = (-1.1)::double precision)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = (?)::double precision)
"""
)

# QUERY: select * from explain_plan_1 where c1 = 1.0e10;

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = 10000000000::double precision)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = ?::double precision)
"""
)

# QUERY: select * from explain_plan_1 where c1 = -1.0e10;

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = (-10000000000)::double precision)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = (?)::double precision)
"""
)

# QUERY: select * from explain_plan_1 where c1 = 1.0e-10;

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = 1e-10::double precision)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = ?::double precision)
"""
)

# QUERY: select * from explain_plan_1 where c1 = -1.0e-10;

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = (-1e-10)::double precision)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = (?)::double precision)
"""
)

# QUERY: select * from explain_plan_1 where c1 in (1,2,3)

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..43.00 rows=36 width=4)
  Filter: (c1 = ANY ('{1,2,3}'::real[]))
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..43.00 rows=36 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..43.00 rows=36 width=4)
  Filter: (c1 = ANY (?::real[]))
"""
)

# QUERY: select * from explain_plan_1 where c1 in (1.1,2.2,3.3)

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..43.00 rows=36 width=4)
  Filter: (c1 = ANY ('{1.1,2.2,3.3}'::real[]))
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..43.00 rows=36 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..43.00 rows=36 width=4)
  Filter: (c1 = ANY (?::real[]))
"""
)

# CREATE: create table if not exists explain_plan_1 (c1 text)
# CREATE: create table if not exists explain_plan_2 (c2 text)
# DELETE: drop table if exists explain_plan_1
# DELETE: drop table if exists explain_plan_2

# QUERY: select * from explain_plan_1 where c1 = 'abcdef'

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..26.38 rows=7 width=32)
  Filter: (c1 = 'abcdef'::text)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..26.38 rows=7 width=32)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..26.38 rows=7 width=32)
  Filter: (c1 = ?::text)
"""
)

# QUERY: select * from explain_plan_1 where c1 = 'abc''def'

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..26.38 rows=7 width=32)
  Filter: (c1 = 'abc''def'::text)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..26.38 rows=7 width=32)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..26.38 rows=7 width=32)
  Filter: (c1 = ?::text)
"""
)

# QUERY: select * from explain_plan_1 where c1 = 'abc\ndef'

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..26.38 rows=7 width=32)
  Filter: (c1 = 'abc
def'::text)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..26.38 rows=7 width=32)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..26.38 rows=7 width=32)
  Filter: (c1 = ?::text)
"""
)

# QUERY: select * from explain_plan_1 where c1 = '\xe2\x88\x9a'

_add_explain_plan_test(
b"""
Seq Scan on explain_plan_1  (cost=0.00..26.38 rows=7 width=32)
  Filter: (c1 = '\xe2\x88\x9a'::text)
""".decode('utf-8'),
"""
Seq Scan on explain_plan_1  (cost=0.00..26.38 rows=7 width=32)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..26.38 rows=7 width=32)
  Filter: (c1 = ?::text)
"""
)

# QUERY: select * from explain_plan_1 where c1 in ('1','2','3')

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..28.01 rows=20 width=32)
  Filter: (c1 = ANY ('{1,2,3}'::text[]))
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..28.01 rows=20 width=32)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..28.01 rows=20 width=32)
  Filter: (c1 = ANY (?::text[]))
"""
)

# QUERY: select * from explain_plan_1 where c1 in ('a','b','c')

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..28.01 rows=20 width=32)
  Filter: (c1 = ANY ('{a,b,c}'::text[]))
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..28.01 rows=20 width=32)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..28.01 rows=20 width=32)
  Filter: (c1 = ANY (?::text[]))
"""
)

# QUERY: select * from explain_plan_1 where c1 in ('a,b','c,d','e,f')

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..28.01 rows=20 width=32)
  Filter: (c1 = ANY ('{"a,b","c,d","e,f"}'::text[]))
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..28.01 rows=20 width=32)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..28.01 rows=20 width=32)
  Filter: (c1 = ANY (?::text[]))
"""
)

# QUERY: select * from explain_plan_1, explain_plan_2 where c1 = c2

_add_explain_plan_test(
"""
Merge Join  (cost=181.86..317.11 rows=8580 width=64)
  Merge Cond: (explain_plan_1.c1 = explain_plan_2.c2)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: explain_plan_1.c1
        ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: explain_plan_2.c2
        ->  Seq Scan on explain_plan_2  (cost=0.00..23.10 rows=1310 width=32)
""",
"""
Merge Join  (cost=181.86..317.11 rows=8580 width=64)
  Merge Cond: ?
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: ?
        ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: ?
        ->  Seq Scan on explain_plan_2  (cost=0.00..23.10 rows=1310 width=32)
""",
"""
Merge Join  (cost=181.86..317.11 rows=8580 width=64)
  Merge Cond: (explain_plan_1.c1 = explain_plan_2.c2)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: explain_plan_1.c1
        ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: explain_plan_2.c2
        ->  Seq Scan on explain_plan_2  (cost=0.00..23.10 rows=1310 width=32)
"""
)

# QUERY: select * from explain_plan_1 where c1 in (select * from explain_plan_2)

_add_explain_plan_test(
"""
Hash Join  (cost=30.88..71.99 rows=655 width=32)
  Hash Cond: (explain_plan_1.c1 = explain_plan_2.c2)
  ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
  ->  Hash  (cost=28.38..28.38 rows=200 width=32)
        ->  HashAggregate  (cost=26.38..28.38 rows=200 width=32)
              ->  Seq Scan on explain_plan_2  (cost=0.00..23.10 rows=1310 width=32)
""",
"""
Hash Join  (cost=30.88..71.99 rows=655 width=32)
  Hash Cond: ?
  ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
  ->  Hash  (cost=28.38..28.38 rows=200 width=32)
        ->  HashAggregate  (cost=26.38..28.38 rows=200 width=32)
              ->  Seq Scan on explain_plan_2  (cost=0.00..23.10 rows=1310 width=32)
""",
"""
Hash Join  (cost=30.88..71.99 rows=655 width=32)
  Hash Cond: (explain_plan_1.c1 = explain_plan_2.c2)
  ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
  ->  Hash  (cost=28.38..28.38 rows=200 width=32)
        ->  HashAggregate  (cost=26.38..28.38 rows=200 width=32)
              ->  Seq Scan on explain_plan_2  (cost=0.00..23.10 rows=1310 width=32)
"""
)

# QUERY: insert into explain_plan_1 select * from explain_plan_2 where explain_plan_2.c2 not in (select * from explain_plan_1)

_add_explain_plan_test(
"""
Insert on explain_plan_1  (cost=26.38..52.75 rows=655 width=32)
  ->  Seq Scan on explain_plan_2  (cost=26.38..52.75 rows=655 width=32)
        Filter: (NOT (hashed SubPlan 1))
        SubPlan 1
          ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
""",
"""
Insert on explain_plan_1  (cost=26.38..52.75 rows=655 width=32)
  ->  Seq Scan on explain_plan_2  (cost=26.38..52.75 rows=655 width=32)
        Filter: ?
        SubPlan 1
          ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
""",
"""
Insert on explain_plan_1  (cost=26.38..52.75 rows=655 width=32)
  ->  Seq Scan on explain_plan_2  (cost=26.38..52.75 rows=655 width=32)
        Filter: (NOT (hashed SubPlan 1))
        SubPlan 1
          ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
"""
)

# QUERY: explain select *, (select length('abcdef')) from explain_plan_1

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.01..23.11 rows=1310 width=32)
  InitPlan 1 (returns $0)
    ->  Result  (cost=0.00..0.01 rows=1 width=0)
""",
"""
Seq Scan on explain_plan_1  (cost=0.01..23.11 rows=1310 width=32)
  InitPlan 1 (returns $0)
    ->  Result  (cost=0.00..0.01 rows=1 width=0)
""",
"""
Seq Scan on explain_plan_1  (cost=0.01..23.11 rows=1310 width=32)
  InitPlan 1 (returns $0)
    ->  Result  (cost=0.00..0.01 rows=1 width=0)
"""
)

# QUERY: select * from explain_plan_1 join explain_plan_2 on explain_plan_2.c2 = concat(explain_plan_1.c1, 'abcdef')

_add_explain_plan_test(
"""
Merge Join  (cost=181.86..341.83 rows=8580 width=64)
  Merge Cond: ((pg_catalog.concat(explain_plan_1.c1, 'abcdef')) = explain_plan_2.c2)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: (pg_catalog.concat(explain_plan_1.c1, 'abcdef'))
        ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: explain_plan_2.c2
        ->  Seq Scan on explain_plan_2  (cost=0.00..23.10 rows=1310 width=32)
""",
"""
Merge Join  (cost=181.86..341.83 rows=8580 width=64)
  Merge Cond: ?
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: ?
        ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: ?
        ->  Seq Scan on explain_plan_2  (cost=0.00..23.10 rows=1310 width=32)
""",
"""
Merge Join  (cost=181.86..341.83 rows=8580 width=64)
  Merge Cond: ((pg_catalog.concat(explain_plan_1.c1, ?)) = explain_plan_2.c2)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: (pg_catalog.concat(explain_plan_1.c1, ?))
        ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: explain_plan_2.c2
        ->  Seq Scan on explain_plan_2  (cost=0.00..23.10 rows=1310 width=32)
"""
)

# QUERY: select * from explain_plan_1 join explain_plan_2 on explain_plan_2.c2 = concat(explain_plan_1.c1, 'abc\ndef')

_add_explain_plan_test(
"""
Merge Join  (cost=181.86..341.83 rows=8580 width=64)
  Merge Cond: ((pg_catalog.concat(explain_plan_1.c1, 'abc
def')) = explain_plan_2.c2)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: (pg_catalog.concat(explain_plan_1.c1, 'abc
def'))
        ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: explain_plan_2.c2
        ->  Seq Scan on explain_plan_2  (cost=0.00..23.10 rows=1310 width=32)
""",
"""
Merge Join  (cost=181.86..341.83 rows=8580 width=64)
  Merge Cond: ?
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: ?
        ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: ?
        ->  Seq Scan on explain_plan_2  (cost=0.00..23.10 rows=1310 width=32)
""",
"""
Merge Join  (cost=181.86..341.83 rows=8580 width=64)
  Merge Cond: ((pg_catalog.concat(explain_plan_1.c1, ?)) = explain_plan_2.c2)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: (pg_catalog.concat(explain_plan_1.c1, ?))
        ->  Seq Scan on explain_plan_1  (cost=0.00..23.10 rows=1310 width=32)
  ->  Sort  (cost=90.93..94.20 rows=1310 width=32)
        Sort Key: explain_plan_2.c2
        ->  Seq Scan on explain_plan_2  (cost=0.00..23.10 rows=1310 width=32)
"""
)

# CREATE: create table if not exists explain_plan_1 (c1 date)
# DELETE: drop table if exists explain_plan_1

# QUERY: select * from explain_plan_1 where c1 = current_date

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..52.00 rows=12 width=4)
  Filter: (c1 = ('now'::cstring)::date)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..52.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..52.00 rows=12 width=4)
  Filter: (c1 = (?::cstring)::date)
"""
)

# QUERY: select * from explain_plan_1 where c1 = date '2000-01-01'

_add_explain_plan_test(
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = '2000-01-01'::date)
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: ?
""",
"""
Seq Scan on explain_plan_1  (cost=0.00..40.00 rows=12 width=4)
  Filter: (c1 = ?::date)
"""
)

# CREATE: create table if not exists "explain_plan'1" (c1 text)
# DELETE: drop table if exists "explain_plan'1"

# QUERY: select * from "explain_plan'1" where c1 = 'abcdef'

_add_explain_plan_test(
"""
Seq Scan on "explain_plan'1"  (cost=0.00..26.38 rows=7 width=32)
  Filter: (c1 = 'abcdef'::text)
""",
"""
Seq Scan on "explain_plan'1"  (cost=0.00..26.38 rows=7 width=32)
  Filter: ?
""",
"""
Seq Scan on "explain_plan'1"  (cost=0.00..26.38 rows=7 width=32)
  Filter: (c1 = ?::text)
"""
)

@pytest.mark.parametrize('original,expected_masked,expected_complete',
        _test_explain_plan_obfuscation_postgresql_complete_tests)
def test_explain_plan_obfuscation_postgresql_mask_true(original,
        expected_masked, expected_complete):

    input_columns = ('Query Plan',)
    input_rows = [(_,) for _ in original.split('\n')]

    output = _obfuscate_explain_plan_postgresql(input_columns, input_rows,
            mask=True)

    output_rows = output[1]

    generated = '\n'.join(item[0] for item in output_rows)

    assert expected_masked == generated

@pytest.mark.parametrize('original,expected_masked,expected_complete',
        _test_explain_plan_obfuscation_postgresql_complete_tests)
def test_explain_plan_obfuscation_postgresql_mask_false(original,
        expected_masked, expected_complete):

    input_columns = ('Query Plan',)
    input_rows = [(_,) for _ in original.split('\n')]

    output = _obfuscate_explain_plan_postgresql(input_columns, input_rows,
            mask=False)

    output_rows = output[1]

    generated = '\n'.join(item[0] for item in output_rows)

    assert expected_complete == generated
