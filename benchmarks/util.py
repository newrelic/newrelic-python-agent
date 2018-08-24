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


def make_incoming_headers(transaction):
    settings = transaction.settings
    encoding_key = settings.encoding_key

    headers = []

    cross_process_id = '1#2'
    path = 'test'
    queue_time = 1.0
    duration = 2.0
    read_length = 1024
    guid = '0123456789012345'
    record_tt = False

    payload = (cross_process_id, path, queue_time, duration, read_length,
            guid, record_tt)
    app_data = json_encode(payload)

    value = obfuscate(app_data, encoding_key)

    headers.append(('X-NewRelic-App-Data', value))

    return headers


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
        self._string_cache = {}
        self._stack_trace_count = 0
        self._explain_plan_count = 0

        self.autorum_disabled = False
        self.rum_header_generated = False

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
