import re

from collections import namedtuple

_NormalizationRule = namedtuple('_NormalizationRule',
        ['match_expression', 'replacement', 'ignore', 'eval_order',
        'terminate_chain', 'each_segment', 'replace_all'])

class NormalizationRule(_NormalizationRule):

    def __init__(self, *args, **kwargs):
        self.match_expression_re = re.compile(self.match_expression)

    def apply(self, string):
        count = 1
        if self.replace_all:
            count = 0

        return self.match_expression_re.sub(self.replacement, string, count)

class RulesEngine(object):

    def __init__(self, rules):
        self.__rules = []

        for rule in rules:
            kwargs = {}
            for name in map(str, rule.keys()):
                if name in NormalizationRule._fields:
                    kwargs[name] = rule[name]
            self.__rules.append(NormalizationRule(**kwargs))

        self.__rules = sorted(self.__rules, key=lambda rule: rule.eval_order)

    @property
    def rules(self):
        return self.__rules

    def normalize(self, string):
        # URLs are supposed to be ASCII but can get a
        # URL with illegal non ASCII characters. As the
        # rule patterns and replacements are Unicode
        # then can get Unicode conversion warnings or
        # errors when URL is converted to Unicode and
        # default encoding is ASCII. Thus need to
        # convert URL to Unicode as Latin-1 explicitly
        # to avoid problems with illegal characters.

        if isinstance(string, bytes):
            string = string.decode('Latin-1')

        final_string = string
        ignore = False
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
                    rule_segment = rule.apply(segment)
                    matched = matched or (rule_segment != segment)
                    rule_segments.append(rule_segment)

                if matched:
                    final_string = '/'.join(rule_segments)
            else:
                rule_string = rule.apply(final_string)
                matched = rule_string != final_string
                final_string = rule_string

            if matched:
                ignore = ignore or rule.ignore

            if matched and rule.terminate_chain:
                break

        return (final_string, ignore)
