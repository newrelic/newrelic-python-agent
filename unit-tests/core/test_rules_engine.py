import unittest

from newrelic.core.rules_engine import *

class TestRulesEngine(unittest.TestCase):

    def setUp(self):
        self.rule = dict(match_expression = "[0-9]+", 
                         replacement = "*", 
                         ignore = False, 
                         eval_order = 1, 
                         terminate_chain = True, 
                         each_segment = False, 
                         replace_all = True)

        self.test_url = "/wallabies/ArticleDetails/tabid/1515/ArticleID/3773/Default.aspx"
        

    def test_rules_engine_should_initialize_with_multiple_rules(self):
        rule0 = self.rule
        rule1 = dict(match_expression = "/something else/", 
                     replacement = "?", 
                     ignore = False, 
                     eval_order = 1, 
                     terminate_chain = True, 
                     each_segment = False, 
                     replace_all = False)

        rules_engine = RulesEngine([rule0, rule1])
        
        self.assertEqual([NormalizationRule(**rule0),
                          NormalizationRule(**rule1)], rules_engine.rules)

    def test_rule_with_replace_all_and_no_each_segment(self):
        rules_engine = RulesEngine([self.rule])
        result = rules_engine.normalize(self.test_url)
        self.assertEqual("/wallabies/ArticleDetails/tabid/*/ArticleID/*/Default.aspx",
                         result)

    def test_rule_without_replace_all(self):
        rule = dict(match_expression = "[0-9]+", 
                    replacement = "*", 
                    ignore = False, 
                    eval_order = 1, 
                    terminate_chain = True, 
                    each_segment = False, 
                    replace_all = False)        

        rules_engine = RulesEngine([rule])
        result = rules_engine.normalize(self.test_url)
        self.assertEqual("/wallabies/ArticleDetails/tabid/*/ArticleID/3773/Default.aspx",
                         result)


    def test_multiple_rules_are_applied_in_eval_order(self):
        rule0 = dict(match_expression = "[0-9]+", 
                     replacement = "foo", 
                     ignore = False, 
                     eval_order = 0,
                     terminate_chain = False, 
                     each_segment = False, 
                     replace_all = True)

        rule1 = dict(match_expression = "foo", 
                     replacement = "bar",
                     ignore = False, 
                     eval_order = 1,
                     terminate_chain = False, 
                     each_segment = False, 
                     replace_all = True)

        rules_engine = RulesEngine([rule1, rule0])
        result = rules_engine.normalize(self.test_url)
        self.assertEqual("/wallabies/ArticleDetails/tabid/bar/ArticleID/bar/Default.aspx",
                         result)

    def test_rule_on_each_segment(self):
        rule = dict(match_expression = ".*",
                    replacement = "X",
                    ignore = False, 
                    eval_order = 0,
                    terminate_chain = False, 
                    each_segment = True, 
                    replace_all = True)

        rules_engine = RulesEngine([rule])
        result = rules_engine.normalize(self.test_url)
        self.assertEqual("/X/X/X/X/X/X/X", result)


    def test_rule_with_back_substition(self):
        rule = dict(match_expression = "([0-9].*)",
                    replacement = "\\1X",
                    ignore = False, 
                    eval_order = 0,
                    terminate_chain = False, 
                    each_segment = True, 
                    replace_all = True)

        rules_engine = RulesEngine([rule])
        result = rules_engine.normalize(self.test_url)
        self.assertEqual("/wallabies/ArticleDetails/tabid/1515X/ArticleID/3773X/Default.aspx", 
                         result)

    def test_rules_with_terminate_chain_with_match_expression(self):
        rule0 = dict(match_expression = "[0-9]+", 
                     replacement = "foo", 
                     ignore = False, 
                     eval_order = 0,
                     terminate_chain = True, 
                     each_segment = False, 
                     replace_all = True)

        rule1 = dict(match_expression = "foo", 
                     replacement = "bar",
                     ignore = False, 
                     eval_order = 1,
                     terminate_chain = False, 
                     each_segment = False, 
                     replace_all = True)

        rules_engine = RulesEngine([rule1, rule0])
        result = rules_engine.normalize(self.test_url)
        self.assertEqual("/wallabies/ArticleDetails/tabid/foo/ArticleID/foo/Default.aspx",
                         result)

    def test_rules_with_terminate_chain_without_match_expression(self):
        rule0 = dict(match_expression = "python_is_seriously_awesome", 
                     replacement = "foo", 
                     ignore = False, 
                     eval_order = 0,
                     terminate_chain = True, 
                     each_segment = False, 
                     replace_all = True)

        rule1 = dict(match_expression = "1515", 
                     replacement = "bar",
                     ignore = False, 
                     eval_order = 1,
                     terminate_chain = False, 
                     each_segment = False, 
                     replace_all = True)

        rules_engine = RulesEngine([rule1, rule0])
        result = rules_engine.normalize(self.test_url)
        self.assertEqual("/wallabies/ArticleDetails/tabid/bar/ArticleID/3773/Default.aspx",
                         result)

    def test_normalizer_reports_if_ignore_rule_was_applied(self):
        rule = dict(match_expression = "[0-9]+", 
                    replacement = "foo", 
                    ignore = True, 
                    eval_order = 0,
                    terminate_chain = False, 
                    each_segment = False, 
                    replace_all = True)

        rules_engine = RulesEngine([rule])
        result = rules_engine.normalize(self.test_url)

        # XXX Need to return ignore transaction flag.

if __name__ == "__main__":
    unittest.main()
