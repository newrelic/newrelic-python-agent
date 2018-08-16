from newrelic.api.transaction import Sentinel
from newrelic.api.web_transaction import WebTransaction
from newrelic.common.encoding_utils import json_encode, obfuscate
from newrelic.core.config import finalize_application_settings


def make_cross_agent_headers(payload, encoding_key, cat_id):
    value = obfuscate(json_encode(payload), encoding_key)
    id_value = obfuscate(cat_id, encoding_key)
    return {'X-NewRelic-Transaction': value, 'X-NewRelic-ID': id_value}


def make_synthetics_header(account_id, resource_id, job_id, monitor_id,
            encoding_key, version=1):
    value = [version, account_id, resource_id, job_id, monitor_id]
    value = obfuscate(json_encode(value), encoding_key)
    return {'X-NewRelic-Synthetics': value}


class MockApplication(object):
    def __init__(self, name='Python Application', settings=None):
        settings = settings or {}
        final_settings = finalize_application_settings(settings)
        self.global_settings = final_settings
        self.global_settings.enabled = True
        self.settings = final_settings
        self.name = name
        self.active = True
        self.enabled = True
        self.thread_utilization = None
        self.attribute_filter = None
        self.nodes = []

    def activate(self):
        pass

    def normalize_name(self, name, rule_type):
        return name, False

    def record_transaction(self, data, *args):
        self.nodes.append(data)
        return None

    def compute_sampled(self, priority):
        return True


class MockTrace(object):
    def __init__(*args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        pass


class MockTransaction(WebTransaction):
    def __init__(self, application, *args, **kwargs):
        self._state = WebTransaction.STATE_STOPPED
        self.stopped = False
        self.enabled = True
        self.current_node = None
        self.client_cross_process_id = None
        self._frameworks = set()
        self._name_priority = 0
        self._settings = application.settings
        self._trace_node_count = 0
        self.current_node = Sentinel()

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        pass

    def _push_current(self, *args, **kwargs):
        pass

    def _pop_current(self, *args, **kwargs):
        pass


class MockTransactionCAT(MockTransaction):
    def __init__(self, *args, **kwargs):
        super(MockTransactionCAT, self).__init__(*args, **kwargs)
        self.client_cross_process_id = '1#1'
        self.queue_start = 0.0
        self.start_time = 0.0
        self.end_time = 0.0
        self._frozen_path = 'foobar'
        self._read_length = None
        self.guid = 'GUID'
        self.record_tt = False
