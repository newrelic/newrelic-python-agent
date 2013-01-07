import unittest

from newrelic.core.rules_engine import *

class TestRulesEngine(unittest.TestCase):

    def setUp(self):
        self.rule = dict(match_expression = u"[0-9]+", 
                         replacement = u"*", 
                         ignore = False, 
                         eval_order = 1, 
                         terminate_chain = True, 
                         each_segment = False, 
                         replace_all = True)

        self.test_url = "/wallabies/ArticleDetails/tabid/1515/ArticleID/3773/Default.aspx"
        

    def test_rules_engine_should_initialize_with_multiple_rules(self):
        rule0 = self.rule
        rule1 = dict(match_expression = u"/something else/", 
                     replacement = u"?", 
                     ignore = False, 
                     eval_order = 1, 
                     terminate_chain = True, 
                     each_segment = False, 
                     replace_all = False)

        rules_engine = RulesEngine([rule0, rule1])
        
        self.assertEqual([NormalizationRule(**rule0),
                          NormalizationRule(**rule1)], rules_engine.rules)

    def test_rules_engine_should_initialize_with_extra_attributes(self):
        rule0 = self.rule
        rule1 = dict(match_expression = u"/something else/", 
                     replacement = u"?", 
                     ignore = False, 
                     eval_order = 1, 
                     terminate_chain = True, 
                     each_segment = False, 
                     replace_all = False,
                     extra = None)

        rules_engine = RulesEngine([rule0, rule1])

        del rule1['extra']

        self.assertEqual([NormalizationRule(**rule0),
                          NormalizationRule(**rule1)], rules_engine.rules)

    def test_rule_with_replace_all_and_no_each_segment(self):
        rules_engine = RulesEngine([self.rule])
        result = rules_engine.normalize(self.test_url)
        self.assertEqual(
            ("/wallabies/ArticleDetails/tabid/*/ArticleID/*/Default.aspx",
            False), result)

    def test_rule_without_replace_all(self):
        rule = dict(match_expression = u"[0-9]+", 
                    replacement = u"*", 
                    ignore = False, 
                    eval_order = 1, 
                    terminate_chain = True, 
                    each_segment = False, 
                    replace_all = False)        

        rules_engine = RulesEngine([rule])
        result = rules_engine.normalize(self.test_url)
        self.assertEqual(
            ("/wallabies/ArticleDetails/tabid/*/ArticleID/3773/Default.aspx",
            False), result)


    def test_multiple_rules_are_applied_in_eval_order(self):
        rule0 = dict(match_expression = u"[0-9]+", 
                     replacement = u"foo", 
                     ignore = False, 
                     eval_order = 0,
                     terminate_chain = False, 
                     each_segment = False, 
                     replace_all = True)

        rule1 = dict(match_expression = u"foo", 
                     replacement = u"bar",
                     ignore = False, 
                     eval_order = 1,
                     terminate_chain = False, 
                     each_segment = False, 
                     replace_all = True)

        rules_engine = RulesEngine([rule1, rule0])
        result = rules_engine.normalize(self.test_url)
        self.assertEqual(
            ("/wallabies/ArticleDetails/tabid/bar/ArticleID/bar/Default.aspx",
            False), result)

    def test_rule_on_each_segment(self):
        rule = dict(match_expression = u".*",
                    replacement = u"X",
                    ignore = False, 
                    eval_order = 0,
                    terminate_chain = False, 
                    each_segment = True, 
                    replace_all = True)

        rules_engine = RulesEngine([rule])
        result = rules_engine.normalize(self.test_url)
        self.assertEqual(("/X/X/X/X/X/X/X", False), result)


    def test_rule_with_back_substition(self):
        rule = dict(match_expression = u"([0-9].*)",
                    replacement = u"\\1X",
                    ignore = False, 
                    eval_order = 0,
                    terminate_chain = False, 
                    each_segment = True, 
                    replace_all = True)

        rules_engine = RulesEngine([rule])
        result = rules_engine.normalize(self.test_url)
        self.assertEqual(
            ("/wallabies/ArticleDetails/tabid/1515X/ArticleID/3773X/Default.aspx", 
            False), result)

    def test_rules_with_terminate_chain_with_match_expression(self):
        rule0 = dict(match_expression = u"[0-9]+", 
                     replacement = u"foo", 
                     ignore = False, 
                     eval_order = 0,
                     terminate_chain = True, 
                     each_segment = False, 
                     replace_all = True)

        rule1 = dict(match_expression = u"foo", 
                     replacement = u"bar",
                     ignore = False, 
                     eval_order = 1,
                     terminate_chain = False, 
                     each_segment = False, 
                     replace_all = True)

        rules_engine = RulesEngine([rule1, rule0])
        result = rules_engine.normalize(self.test_url)
        self.assertEqual(
            ("/wallabies/ArticleDetails/tabid/foo/ArticleID/foo/Default.aspx",
            False), result)

    def test_rules_with_terminate_chain_without_match_expression(self):
        rule0 = dict(match_expression = u"python_is_seriously_awesome", 
                     replacement = u"foo", 
                     ignore = False, 
                     eval_order = 0,
                     terminate_chain = True, 
                     each_segment = False, 
                     replace_all = True)

        rule1 = dict(match_expression = u"1515", 
                     replacement = u"bar",
                     ignore = False, 
                     eval_order = 1,
                     terminate_chain = False, 
                     each_segment = False, 
                     replace_all = True)

        rules_engine = RulesEngine([rule1, rule0])
        result = rules_engine.normalize(self.test_url)
        self.assertEqual(
            ("/wallabies/ArticleDetails/tabid/bar/ArticleID/3773/Default.aspx",
            False), result)

    def test_normalizer_reports_if_ignore_rule_was_applied(self):
        rule = dict(match_expression = u"[0-9]+", 
                    replacement = u"foo", 
                    ignore = True, 
                    eval_order = 0,
                    terminate_chain = False, 
                    each_segment = False, 
                    replace_all = True)

        rules_engine = RulesEngine([rule])
        result = rules_engine.normalize(self.test_url)

        self.assertEqual(
            ("/wallabies/ArticleDetails/tabid/foo/ArticleID/foo/Default.aspx",
            True), result)

    def test_rule_with_unicode_and_non_ascii(self):
        rule = dict(match_expression = u"^(/xxx.*)", 
                         replacement = u"/yyy", 
                         ignore = False, 
                         eval_order = 1, 
                         terminate_chain = True, 
                         each_segment = False, 
                         replace_all = True)

        rules_engine = RulesEngine([rule])
        url = (u'/xxx' + unichr(0x0bf2)).encode('UTF-8')
        result = rules_engine.normalize(url)

        self.assertEqual(("/yyy", False), result)

    def test_rule_with_unicode_and_non_ascii_include_original(self):
        rule = dict(match_expression = u"^(/xxx.*)", 
                         replacement = u"/yyy\\1", 
                         ignore = False, 
                         eval_order = 1, 
                         terminate_chain = True, 
                         each_segment = False, 
                         replace_all = True)

        rules_engine = RulesEngine([rule])
        url = (u'/xxx' + unichr(0x0bf2)).encode('UTF-8')
        result = rules_engine.normalize(url)

        self.assertEqual((u"/yyy"+url.decode('Latin-1'), False), result)

    def test_negative_lookahead(self):
        rule = dict(match_expression = u"^(?!account|application).*", 
                         replacement = u"*", 
                         ignore = False, 
                         eval_order = 1, 
                         terminate_chain = True, 
                         each_segment = True, 
                         replace_all = True)

        rules_engine = RulesEngine([rule])

        self.assertEqual((u"/account/*/application/*", False),
                rules_engine.normalize(u'/account/myacc/application/test'))

        self.assertEqual((u"/*/*/account/*/application", False),
                rules_engine.normalize(u"/oh/dude/account/myacc/application"))

if __name__ == "__main__":
    unittest.main()
