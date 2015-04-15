from .config import fetch_config_setting, flatten_settings, global_settings


DST_NONE = 0x0
DST_ALL  = 0xF

DST_TRANSACTION_EVENTS = 1 << 0
DST_TRANSACTION_TRACER = 1 << 1
DST_ERROR_COLLECTOR    = 1 << 2
DST_BROWSER_MONITORING = 1 << 3

_default_settings = {
        'attributes.enabled': True,
        'transaction_events.attributes.enabled': True,
        'transaction_tracer.attributes.enabled': True,
        'error_collector.attributes.enabled': True,
        'browser_monitoring.attributes.enabled': False,
        'attributes.include': [],
        'attributes.exclude': [],
        'transaction_events.attributes.include': [],
        'transaction_events.attributes.exclude': [],
        'transaction_tracer.attributes.include': [],
        'transaction_tracer.attributes.exclude': [],
        'error_collector.attributes.include': [],
        'error_collector.attributes.exclude': [],
        'browser_monitoring.attributes.include': [],
        'browser_monitoring.attributes.exclude': [],
}

_enable_attribute_settings = [
        ('attributes.enabled', DST_ALL),
        ('transaction_events.attributes.enabled', DST_TRANSACTION_EVENTS),
        ('transaction_tracer.attributes.enabled', DST_TRANSACTION_TRACER),
        ('error_collector.attributes.enabled', DST_ERROR_COLLECTOR),
        ('browser_monitoring.attributes.enabled', DST_BROWSER_MONITORING),
]

_include_exclude_settings = [
        ('attributes.include',DST_ALL, True),
        ('attributes.exclude', DST_ALL, False),
        ('transaction_events.attributes.include', DST_TRANSACTION_EVENTS, True),
        ('transaction_events.attributes.exclude', DST_TRANSACTION_EVENTS, False),
        ('transaction_tracer.attributes.include', DST_TRANSACTION_TRACER, True),
        ('transaction_tracer.attributes.exclude', DST_TRANSACTION_TRACER, False),
        ('error_collector.attributes.include', DST_ERROR_COLLECTOR, True),
        ('error_collector.attributes.exclude', DST_ERROR_COLLECTOR, False),
        ('browser_monitoring.attributes.include', DST_BROWSER_MONITORING, True),
        ('browser_monitoring.attributes.exclude', DST_BROWSER_MONITORING, False),
]

_deprecated_attribute_settings = []

def bin(s):
    return str(s) if s<=1 else bin(s>>1) + str(s&1)

class AttributeFilterRule(object):

    def __init__(self, name, destinations, is_include):
        self.name = name.rstrip('*')
        self.destinations = destinations
        self.is_include = is_include
        self.is_wildcard = name.endswith('*')

    def __repr__(self):
        return '(%s, %s, %s, %s)' % (self.name, bin(self.destinations),
                self.is_wildcard, self.is_include)

    def __eq__(self, other):
        return self._as_tuple() == other._as_tuple()

    def __ne__(self, other):
        return self._as_tuple() != other._as_tuple()

    def __lt__(self, other):
        return self._as_tuple() < other._as_tuple()

    def __le__(self, other):
        return self._as_tuple() <= other._as_tuple()

    def __gt__(self, other):
        return self._as_tuple() > other._as_tuple()

    def __ge__(self, other):
        return self._as_tuple() >= other._as_tuple()

    def _as_tuple(self):
        # Non-wildcards sort after wildcards
        # Excludes sort after includes
        return tuple([self.name, not self.is_wildcard, not self.is_include])

    def name_match(self, name):
        if self.is_wildcard:
            return name.startswith(self.name)
        else:
            return self.name == name

class AttributeFilter(object):

    def __init__(self, settings=None):

        if settings is None:
            self.settings = flatten_settings(global_settings())
        else:
            self.settings = settings

        self.enabled_destinations = self._set_enabled_destinations()

        self.rules = []
        for setting in _include_exclude_settings:
            rules = self._build_rules(*setting)
            self.rules.extend(rules)

        # self.rules += self._build_rules(*_deprecated_attribute_settings)

        self.rules.sort()

    def __repr__(self):
        return "%s: %s" % (bin(self.enabled_destinations), self.rules)

    def _fetch(self, setting):
        return self.settings.get(setting, tuple())

    def _set_enabled_destinations(self):
        enabled_destinations = DST_NONE

        if self._fetch('transaction_tracer.attributes.enabled'):
            enabled_destinations |= DST_TRANSACTION_TRACER

        if self._fetch('transaction_events.attributes.enabled'):
            enabled_destinations |= DST_TRANSACTION_EVENTS

        if self._fetch('error_collector.attributes.enabled'):
            enabled_destinations |= DST_ERROR_COLLECTOR

        if self._fetch('browser_monitoring.attributes.enabled'):
            enabled_destinations |= DST_BROWSER_MONITORING

        if not self._fetch('attributes.enabled'):
            enabled_destinations = DST_NONE

        return enabled_destinations

    def _build_rules(self, setting_name, destinations, is_include):
        rules = []
        for name in self._fetch(setting_name):
            rules.append(AttributeFilterRule(name, destinations, is_include))
        return rules

    def apply(self, name, default_destinations):
        if self.enabled_destinations == DST_NONE:
            return DST_NONE

        destinations = self.enabled_destinations & default_destinations

        for rule in self.rules:
            if rule.name_match(name):
                if rule.is_include:
                    inc_dest = rule.destinations & self.enabled_destinations
                    destinations |= inc_dest
                else:
                    destinations &= ~rule.destinations

        return destinations
