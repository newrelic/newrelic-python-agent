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

class SegmentCollapseEngine(object):
    """Segment names in transaction name are collapsed using the rules from the
    collector. The collector sends a prefix and list of whitelist terms
    associated with that prefix. If a transaction name matches the prefix then
    we replace all segments of the name with a '*' except for the segments in
    the whitelist terms.

    """

    COLLAPSE_STAR_RE = re.compile('((?:^|/)\*)(?:/\*)*')

    def __init__(self, rules):
        self.rules = {}
        for rule in rules:
            # Prefix must have exactly 2 valid segments. We remove any empty
            # strings that may result from splitting a prefix that might have a
            # trailing slash. eg: 'WebTransaction/Foo/' will result in
            # ['WebTransaction', 'Foo', ''].

            prefix_segments = [x for x in rule['prefix'].split('/') if x]
            if len(prefix_segments) == 2:
                prefix = '/'.join(prefix_segments)
                self.rules[prefix] = rule['terms']

    def normalize(self, txn_name):
        """Takes a transaction name and collapses the segments into a '*'
        except for the segments in the whitelist_terms.

        """

        # Only the first two segments of the transaction name can be a prefix.
        prefix = '/'.join(txn_name.split('/')[:2])
        whitelist_terms = self.rules.get(prefix)
        if whitelist_terms is None:
            return txn_name

        # Remove the prefix. and split by '/' to extract the segments.

        txn_name_no_prefix = txn_name[len(prefix):]

        # If the remaining portion has a preceding '/' we strip it out and
        # add them back when joining the segments after the collapsing.

        add_slash = txn_name_no_prefix.startswith('/')
        segments = txn_name_no_prefix.lstrip('/').split('/')

        # Replace non-whitelist terms with '*'.

        result = [x if x in whitelist_terms else '*' for x in segments]

        # Collapse adjacent '*' segments to a single '*'.
        result_string = '/'.join(result)

        collapsed_result = self.COLLAPSE_STAR_RE.sub('\\1', result_string)

        # Set the txn_name to the new value after applying the rule.

        if add_slash:
            txn_name = prefix + '/' + collapsed_result
        else:
            txn_name = prefix + collapsed_result

        return txn_name
