import re

class NormalizationRule:
    def __init__(self, match, replacement, ignore=False, order=0, 
                 terminate_chain=False, each_segment=False, replace_all=True):
        self.match = match
        self.replacement = replacement
        self.ignore = ignore
        self.order = order
        self.terminate_chain = terminate_chain
        self.each_segment = each_segment
        self.replace_all = replace_all

class Normalizer:
    def __init__(self, *rules):
        self.rules = rules

    def normalize(self, string):
        result = string
        sorted_rules = sorted(self.rules, key=lambda rule: rule.order)
        for rule in sorted_rules:
            if rule.each_segment:
                result_list = [self.apply_rule(rule, segment) 
                               for segment in result.split('/')[1:]]
                result = '/' + ('/').join(result_list)
            else:
                result = self.apply_rule(rule, result)        
        return result

    def apply_rule(self, rule, string):
        max = 1
        if rule.replace_all:
            max = 0
        return re.sub(rule.match, rule.replacement, string, max)
