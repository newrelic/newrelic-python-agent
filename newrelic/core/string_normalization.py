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
        self.matched = False

    def apply(self, string):
        max = 1
        if self.replace_all:
            max = 0
        result = re.sub(self.match, self.replacement, string, max)
        self.matched = (result != string)
        return result

class Normalizer:
    def __init__(self, *rules):
        self.rules = rules

    def normalize(self, string):
        final_string = string
        for rule in sorted(self.rules, key=lambda rule: rule.order):
            if rule.each_segment:
                result_list = [rule.apply(segment)
                               for segment in final_string.split('/')[1:]]
                final_string = '/' + ('/').join(result_list)
            else:
                final_string = rule.apply(final_string)

            if rule.matched and rule.terminate_chain: break
        return final_string
