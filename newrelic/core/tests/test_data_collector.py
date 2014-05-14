import unittest

import newrelic.core.config as config
import newrelic.core.data_collector as dc

class TestApplyHighSecurityMode(unittest.TestCase):

    def setUp(self):

        self.local = config.global_settings_dump()
        self.local['high_security'] = True

        # Use an abridged version of the server settings dict for testing.

        self.server = {
                u'agent_config':
                    {u'browser_monitoring.loader': u'xhr',
                     u'capture_params': True,
                     u'cross_application_tracer.enabled': True,
                     u'error_collector.enabled': True,
                     u'error_collector.ignore_errors': [u'[]'],
                     u'ignored_params': [u'[]'],
                     u'rum.load_episodes_file': True,
                     u'slow_sql.enabled': True,
                     u'thread_profiler.enabled': True,
                     u'transaction_name.naming_scheme': u'',
                     u'transaction_tracer.enabled': True,
                     u'transaction_tracer.explain_enabled': True,
                     u'transaction_tracer.explain_threshold': 0.0,
                     u'transaction_tracer.record_sql': u'obfuscated',
                     u'transaction_tracer.stack_trace_threshold': 0.0,
                     u'transaction_tracer.transaction_threshold': u'apdex_f'},
                u'high_security': True}

    def test_hsm_delete_high_security(self):
        settings = dc.apply_high_security_mode(self.local, self.server)
        self.assertFalse('high_security' in settings)

    def test_hsm_delete_missing_high_security(self):
        del self.server['high_security']
        settings = dc.apply_high_security_mode(self.local, self.server)
        self.assertFalse('high_security' in settings)

    def test_hsm_delete_ssl(self):
        settings = dc.apply_high_security_mode(self.local, self.server)
        self.assertFalse('ssl' in settings['agent_config'])

    def test_hsm_delete_capture_params(self):
        settings = dc.apply_high_security_mode(self.local, self.server)
        self.assertFalse('capture_params' in settings['agent_config'])

    def test_hsm_delete_record_sql(self):
        settings = dc.apply_high_security_mode(self.local, self.server)
        self.assertFalse(
                'transaction_tracer.record_sql' in settings['agent_config'])

if __name__ == "__main__":
    unittest.main()
