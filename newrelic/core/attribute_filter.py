from .config import fetch_config_setting, flatten_settings, global_settings


DST_NONE = 0x0
DST_ALL  = 0xF

DST_TRANSACTION_EVENTS = 1 << 0
DST_TRANSACTION_TRACER = 1 << 1
DST_ERROR_COLLECTOR    = 1 << 2
DST_BROWSER_MONITORING = 1 << 3

def int2binary(i):
    """Represent int as binary string."""
    return str(i) if i<=1 else int2binary(i>>1) + str(i&1)

class AttributeFilterRule(object):

    def __init__(self, name, destinations, is_include):
        self.name = name.rstrip('*')
        self.destinations = destinations
        self.is_include = is_include
        self.is_wildcard = name.endswith('*')

    def __repr__(self):
        return '(%s, %s, %s, %s)' % (self.name, int2binary(self.destinations),
                self.is_wildcard, self.is_include)

    def __eq__(self, other):
        return self._as_sortable() == other._as_sortable()

    def __ne__(self, other):
        return self._as_sortable() != other._as_sortable()

    def __lt__(self, other):
        return self._as_sortable() < other._as_sortable()

    def __le__(self, other):
        return self._as_sortable() <= other._as_sortable()

    def __gt__(self, other):
        return self._as_sortable() > other._as_sortable()

    def __ge__(self, other):
        return self._as_sortable() >= other._as_sortable()

    def _as_sortable(self):
        # Non-wildcards sort after wildcards
        # Excludes sort after includes
        return tuple([self.name, not self.is_wildcard, not self.is_include])

    def name_match(self, name):
        if self.is_wildcard:
            return name.startswith(self.name)
        else:
            return self.name == name

class AttributeFilter(object):

    INCLUDE_EXCLUDE_SETTINGS = (
        ('attributes.include', DST_ALL, True),
        ('attributes.exclude', DST_ALL, False),
        ('transaction_events.attributes.include', DST_TRANSACTION_EVENTS, True),
        ('transaction_events.attributes.exclude', DST_TRANSACTION_EVENTS, False),
        ('transaction_tracer.attributes.include', DST_TRANSACTION_TRACER, True),
        ('transaction_tracer.attributes.exclude', DST_TRANSACTION_TRACER, False),
        ('error_collector.attributes.include', DST_ERROR_COLLECTOR, True),
        ('error_collector.attributes.exclude', DST_ERROR_COLLECTOR, False),
        ('browser_monitoring.attributes.include', DST_BROWSER_MONITORING, True),
        ('browser_monitoring.attributes.exclude', DST_BROWSER_MONITORING, False),
    )

    def __init__(self, settings=None):

        if settings is None:
            self.settings = flatten_settings(global_settings())
        else:
            self.settings = settings

        self.enabled_destinations = self._set_enabled_destinations()
        self.rules = self._build_rules(self.INCLUDE_EXCLUDE_SETTINGS)

        self.rules.sort()

    def __repr__(self):
        return "<AttributeFilter: destinations: %s, rules: %s>" % (
                int2binary(self.enabled_destinations), self.rules)

    def _set_enabled_destinations(self):
        enabled_destinations = DST_NONE

        if self.settings.get('transaction_tracer.attributes.enabled', None):
            enabled_destinations |= DST_TRANSACTION_TRACER

        if self.settings.get('transaction_events.attributes.enabled', None):
            enabled_destinations |= DST_TRANSACTION_EVENTS

        if self.settings.get('error_collector.attributes.enabled', None):
            enabled_destinations |= DST_ERROR_COLLECTOR

        if self.settings.get('browser_monitoring.attributes.enabled', None):
            enabled_destinations |= DST_BROWSER_MONITORING

        if not self.settings.get('attributes.enabled', None):
            enabled_destinations = DST_NONE

        return enabled_destinations

    def _build_rules(self, rule_templates):
        rules = []

        for (setting_name, destination, is_include) in rule_templates:

            for setting in self.settings.get(setting_name) or ():
                rule = AttributeFilterRule(setting, destination, is_include)
                rules.append(rule)

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
