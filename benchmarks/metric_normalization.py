from benchmarks.util import MockApplication

from newrelic.api.transaction import Transaction
from newrelic.core.rules_engine import RulesEngine, SegmentCollapseEngine


class TimeTransactionFreezePath(object):
    def setup(self):
        application = MockApplication()
        self.transaction = Transaction(application)

    def time_freeze_path(self, *args):
        self.transaction._frozen_path = None
        self.transaction._group = 'Uri'
        self.transaction._freeze_path()


class TimeRulesEngineNormalizeNoRules(object):
    rules = []
    rule_type = RulesEngine

    def setup(self):
        self.rule = self.rule_type(self.rules)

    def time_normalize(self):
        self.rule.normalize('WebTransaction/Uri/time_normalize')


class TimeRulesEngineNormalize(TimeRulesEngineNormalizeNoRules):
    rules = [{
        'ignore': False,
        'eval_order': 0,
        'replace_all': False,
        'match_expression': 'time_normalize',
        'terminate_chain': False,
        'each_segment': False,
        'replacement': 'time_differentize',
    }]


class TimeRulesEngineNormalizeEachSegment(TimeRulesEngineNormalizeNoRules):
    rules = [{
        'ignore': False,
        'eval_order': 0,
        'replace_all': False,
        'match_expression': 'time_normalize',
        'terminate_chain': False,
        'each_segment': True,
        'replacement': 'time_differentize',
    }]


class TimeSegmentCollapseEngineNoRules(TimeRulesEngineNormalizeNoRules):
    rule_type = SegmentCollapseEngine


class TimeSegmentCollapseEngine(TimeSegmentCollapseEngineNoRules):
    rules = [{
        'prefix': 'WebTransaction/Uri',
        'terms': ['time_normalize'],
    }]
