import unittest
from newrelic.core.string_normalization import *

class TestStringNormalization(unittest.TestCase):
    def setUp(self):
        self.rule = NormalizationRule(match = "[0-9]+", 
                                      replacement = "*", 
                                      ignore = False, 
                                      order = 1, 
                                      terminate_chain = True, 
                                      each_segment = False, 
                                      replace_all = True)
        self.test_url = "/wallabies/ArticleDetails/tabid/1515/ArticleID/3773/Default.aspx"
        

    def test_normalization_rule_should_initialize(self):
        self.assertEqual("[0-9]+", self.rule.match)
        self.assertEqual("*", self.rule.replacement)
        self.assertEqual(False, self.rule.ignore)
        self.assertEqual(1, self.rule.order)
        self.assertEqual(True, self.rule.terminate_chain)
        self.assertEqual(False, self.rule.each_segment)
        self.assertEqual(True, self.rule.replace_all)

    def test_normalizer_should_initialize_with_multiple_rules(self):
        rule0 = self.rule
        rule1 = NormalizationRule(match = "/something else/", 
                                  replacement = "?", 
                                  ignore = False, 
                                  order = 1, 
                                  terminate_chain = True, 
                                  each_segment = False, 
                                  replace_all = False)
        normalizer = Normalizer(rule0, rule1)
        
        self.assertEqual((rule0, rule1), normalizer.rules)

    def test_rule_with_replace_all_and_no_each_segment(self):
        normalizer = Normalizer(self.rule)
        result = normalizer.normalize(self.test_url)
        self.assertEqual("/wallabies/ArticleDetails/tabid/*/ArticleID/*/Default.aspx",
                         result)

    def test_rule_without_replace_all(self):
        rule = NormalizationRule(match = "[0-9]+", 
                                 replacement = "*", 
                                 ignore = False, 
                                 order = 1, 
                                 terminate_chain = True, 
                                 each_segment = False, 
                                 replace_all = False)        
        normalizer = Normalizer(rule)
        result = normalizer.normalize(self.test_url)
        self.assertEqual("/wallabies/ArticleDetails/tabid/*/ArticleID/3773/Default.aspx",
                         result)


    def test_multiple_rules_are_applied_in_order(self):
        rule0 = NormalizationRule(match = "[0-9]+", 
                                  replacement = "foo", 
                                  ignore = False, 
                                  order = 0,
                                  terminate_chain = False, 
                                  each_segment = False, 
                                  replace_all = True)
        rule1 = NormalizationRule(match = "foo", 
                                  replacement = "bar",
                                  ignore = False, 
                                  order = 1,
                                  terminate_chain = False, 
                                  each_segment = False, 
                                  replace_all = True)
        normalizer = Normalizer(rule1, rule0)
        result = normalizer.normalize(self.test_url)
        self.assertEqual("/wallabies/ArticleDetails/tabid/bar/ArticleID/bar/Default.aspx",
                         result)

    def test_rule_on_each_segment(self):
        rule = NormalizationRule(match = ".*",
                                 replacement = "X",
                                 ignore = False, 
                                 order = 0,
                                 terminate_chain = False, 
                                 each_segment = True, 
                                 replace_all = True)
        normalizer = Normalizer(rule)
        result = normalizer.normalize(self.test_url)
        self.assertEqual("/X/X/X/X/X/X/X", result)


    def test_rule_with_back_substition(self):
        rule = NormalizationRule(match = "([0-9].*)",
                                 replacement = "\\1X",
                                 ignore = False, 
                                 order = 0,
                                 terminate_chain = False, 
                                 each_segment = True, 
                                 replace_all = True)
        normalizer = Normalizer(rule)
        result = normalizer.normalize(self.test_url)
        self.assertEqual("/wallabies/ArticleDetails/tabid/1515X/ArticleID/3773X/Default.aspx", 
                         result)

    def test_rules_with_terminate_chain_with_match(self):
        rule0 = NormalizationRule(match = "[0-9]+", 
                                  replacement = "foo", 
                                  ignore = False, 
                                  order = 0,
                                  terminate_chain = True, 
                                  each_segment = False, 
                                  replace_all = True)
        rule1 = NormalizationRule(match = "foo", 
                                  replacement = "bar",
                                  ignore = False, 
                                  order = 1,
                                  terminate_chain = False, 
                                  each_segment = False, 
                                  replace_all = True)
        normalizer = Normalizer(rule1, rule0)
        result = normalizer.normalize(self.test_url)
        self.assertEqual("/wallabies/ArticleDetails/tabid/foo/ArticleID/foo/Default.aspx",
                         result)

    def test_rules_with_terminate_chain_without_match(self):
        rule0 = NormalizationRule(match = "python_is_seriously_awesome", 
                                  replacement = "foo", 
                                  ignore = False, 
                                  order = 0,
                                  terminate_chain = True, 
                                  each_segment = False, 
                                  replace_all = True)
        rule1 = NormalizationRule(match = "1515", 
                                  replacement = "bar",
                                  ignore = False, 
                                  order = 1,
                                  terminate_chain = False, 
                                  each_segment = False, 
                                  replace_all = True)
        normalizer = Normalizer(rule1, rule0)
        result = normalizer.normalize(self.test_url)
        self.assertEqual("/wallabies/ArticleDetails/tabid/bar/ArticleID/3773/Default.aspx",
                         result)

if __name__ == "__main__":
    unittest.main()
