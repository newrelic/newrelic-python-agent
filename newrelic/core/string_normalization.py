import re
import collections

_NormalizationRule = collections.namedtuple('_NormalizationRule', 
                                            ['match', 'replacement', 'ignore',
                                             'order', 'terminate_chain',
                                             'each_segment', 'replace_all'])

class NormalizationRule(_NormalizationRule):
    def apply(self, string):
        max = 1
        if self.replace_all:
            max = 0
        result = re.sub(self.match, self.replacement, string, max)
        self.matched = (result != string)
        return result

DefaultNormalizationRule = NormalizationRule(match=None, replacement=None, 
                                             ignore=False, order=0, 
                                             terminate_chain=False, 
                                             each_segment=False,
                                             replace_all=True)

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

    def applied_ignore_rule(self):
        return reduce(lambda x,y: x.ignore or y.ignore, 
                      [rule for rule in self.rules if rule.matched])
