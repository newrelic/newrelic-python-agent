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
        final_string = string
        sorted_rules = sorted(self.rules, key=lambda rule: rule.order)
        for rule in sorted_rules:

            string_before_rule = final_string
            
            if rule.each_segment:
                result_list = [self.apply_rule(rule, segment) 
                               for segment in final_string.split('/')[1:]]
                final_string = '/' + ('/').join(result_list)
            else:
                final_string = self.apply_rule(rule, final_string)

            if self._rule_was_applied(string_before_rule, final_string) and rule.terminate_chain:
                break
        return final_string

    def apply_rule(self, rule, string):
        max = 1
        if rule.replace_all:
            max = 0
        return re.sub(rule.match, rule.replacement, string, max)

    def _rule_was_applied(self, string_before_rule, final_string):
        return (string_before_rule != final_string) 

        
