import re
import collections

_NormalizationRule = collections.namedtuple('_NormalizationRule',
        ['match_expression', 'replacement', 'ignore', 'eval_order',
        'terminate_chain', 'each_segment', 'replace_all'])

class NormalizationRule(_NormalizationRule):

    def __init__(self, *args, **kwargs):
        self.match_expression_re = re.compile(self.match_expression)

    def match(self, string):
        max = 1
        if self.replace_all:
            max = 0

        result = self.match_expression_re.sub(self.replacement, string, max)

        return (result != string, result)

class RulesEngine(object):

    def __init__(self, rules):
        self.__rules = []

        for rule in rules:
            kwargs = {}
            for name in map(str, rule.keys()):
                kwargs[name] = str(rule[name])
            self.__rules.append(NormalizationRule(**kwargs))

        self.__rules = sorted(self.__rules, key=lambda rule: rule.eval_order)

    @property
    def rules(self):
        return self.__rules

    def normalize(self, string):
        final_string = string
        for rule in self.__rules:
            if rule.each_segment:
                matched = False

                segments = final_string.split('/')

		# FIXME This fiddle is to skip leading segment
		# when splitting on '/' where it is empty.
		# Should the rule just be to skip any empty
		# segment when matching keeping it as empty
                # but not matched. Wouldn't then have to treat
                # this as special.

                if segments and not segments[0]:
                    rule_segments = ['']
                    segments = segments[1:]
                else:
                    rule_segments = []

                for segment in segments:
                    rule_matched, rule_segment = rule.match(segment)
                    matched = matched or rule_matched
                    rule_segments.append(rule_segment)

                if matched:
                    final_string = '/'.join(rule_segments)
            else:
                matched, final_string = rule.apply(final_string)

            if matched and rule.terminate_chain:
                break

        return final_string
