import copy
import unittest

import newrelic.core.config


class TestSettings(unittest.TestCase):

    def test_category_creation(self):
        d = {'a1': 1, 'a2.b2': 2, 'a3.b3.c3': 3}
        c = newrelic.core.config.apply_server_side_settings(d)
        self.assertEqual(1, c.a1)
        self.assertEqual(2, c.a2.b2)
        self.assertEqual(3, c.a3.b3.c3)


class TestTransactionTracerConfig(unittest.TestCase):

    def test_defaults(self):
        c = newrelic.core.config.apply_server_side_settings()
        tt = c.transaction_tracer
        self.assertTrue(tt.enabled)
        self.assertEqual(None, tt.transaction_threshold)

    def test_enabled(self):
        d = {'transaction_tracer.enabled': False}
        c = newrelic.core.config.apply_server_side_settings(d)
        tt = c.transaction_tracer
        self.assertFalse(tt.enabled)

    def test_transaction_threshold(self):
        d = {'transaction_tracer.transaction_threshold': 0.666}
        c = newrelic.core.config.apply_server_side_settings(d)
        tt = c.transaction_tracer
        self.assertEqual(0.666, tt.transaction_threshold)


class TestUtilizationConfig(unittest.TestCase):

    def test_defaults(self):
        c = newrelic.core.config.apply_server_side_settings()
        self.assertTrue(c.utilization.detect_aws)
        self.assertTrue(c.utilization.detect_docker)

    def test_detect_aws_false(self):
        d = {'utilization.detect_aws': False}
        c = newrelic.core.config.apply_server_side_settings(d)
        self.assertFalse(c.utilization.detect_aws)
        self.assertTrue(c.utilization.detect_docker)

    def test_docker_false(self):
        d = {'utilization.detect_docker': False}
        c = newrelic.core.config.apply_server_side_settings(d)
        self.assertTrue(c.utilization.detect_aws)
        self.assertFalse(c.utilization.detect_docker)

    def test_detect_utilization_false(self):
        d = {'utilization.detect_aws': False,
             'utilization.detect_docker': False}
        c = newrelic.core.config.apply_server_side_settings(d)
        self.assertFalse(c.utilization.detect_aws)
        self.assertFalse(c.utilization.detect_docker)


class TestIgnoreStatusCodes(unittest.TestCase):

    def test_add_single(self):
        values = set()
        newrelic.core.config._parse_ignore_status_codes('100', values)
        self.assertEqual(values, set([100]))

    def test_add_single_many(self):
        values = set()
        newrelic.core.config._parse_ignore_status_codes('100 200', values)
        self.assertEqual(values, set([100, 200]))

    def test_add_range(self):
        values = set()
        newrelic.core.config._parse_ignore_status_codes('100-101', values)
        self.assertEqual(values, set([100, 101]))

    def test_add_range_many(self):
        values = set()
        newrelic.core.config._parse_ignore_status_codes('100-101 200-201',
                values)
        self.assertEqual(values, set([100, 101, 200, 201]))

    def test_add_range_length_one(self):
        values = set()
        newrelic.core.config._parse_ignore_status_codes('100-100', values)
        self.assertEqual(values, set([100]))

    def test_remove_single(self):
        values = set([100, 101, 102])
        newrelic.core.config._parse_ignore_status_codes('!101', values)
        self.assertEqual(values, set([100, 102]))

    def test_remove_single_not_already_in_set(self):
        values = set([100, 101, 102])
        newrelic.core.config._parse_ignore_status_codes('!404', values)
        self.assertEqual(values, set([100, 101, 102]))

    def test_remove_single_many(self):
        values = set([100, 101, 102])
        newrelic.core.config._parse_ignore_status_codes('!101 !102', values)
        self.assertEqual(values, set([100]))

    def test_remove_single_many_not_already_in_set(self):
        values = set([100, 101, 102])
        newrelic.core.config._parse_ignore_status_codes(
                '!101 !102 !404 !503', values)
        self.assertEqual(values, set([100]))

    def test_remove_range(self):
        values = set(range(100, 106))
        newrelic.core.config._parse_ignore_status_codes('!101-104', values)
        self.assertEqual(values, set([100, 105]))

    def test_remove_range_not_already_in_set(self):
        values = set(range(100, 106))
        newrelic.core.config._parse_ignore_status_codes('!102-108', values)
        self.assertEqual(values, set([100, 101]))

    def test_remove_range_many(self):
        values = set(range(100, 106))
        newrelic.core.config._parse_ignore_status_codes('!101-102 !103-104',
                values)
        self.assertEqual(values, set([100, 105]))

    def test_remove_range_many_not_already_in_set(self):
        values = set(range(100, 106))
        newrelic.core.config._parse_ignore_status_codes(
                '!101-102 !103-104 !500-503', values)
        self.assertEqual(values, set([100, 105]))

    def test_remove_range_length_one(self):
        values = set([100, 101, 102])
        newrelic.core.config._parse_ignore_status_codes('!101-101', values)
        self.assertEqual(values, set([100, 102]))

    def test_remove_range_length_one_not_already_in_set(self):
        values = set([100, 101, 102])
        newrelic.core.config._parse_ignore_status_codes('!403-404', values)
        self.assertEqual(values, set([100, 101, 102]))

    def test_add_and_remove(self):
        values = set()
        newrelic.core.config._parse_ignore_status_codes(
                '100-110 200 201 202 !201 !101-109', values)
        self.assertEqual(values, set([100, 110, 200, 202]))

    def test_add_and_remove_not_already_in_set(self):
        values = set()
        newrelic.core.config._parse_ignore_status_codes(
                '100-110 200 201 202 !201 !101-109 !403-404', values)
        self.assertEqual(values, set([100, 110, 200, 202]))


class TestCreateSettingsSnapshot(unittest.TestCase):

    def setUp(self):
        self.local = copy.deepcopy(newrelic.core.config.global_settings())

    def test_high_security_off_override_capture_params(self):
        server = {'capture_params': False}
        self.local.high_security = False
        self.local.capture_params = True
        c = newrelic.core.config.apply_server_side_settings(server, self.local)
        self.assertFalse(c.capture_params)

    def test_high_security_off_override_record_sql(self):
        server = {'transaction_tracer.record_sql': 'off'}
        self.local.high_security = False
        self.local.transaction_tracer.record_sql = 'raw'
        c = newrelic.core.config.apply_server_side_settings(server, self.local)
        self.assertEqual(c.transaction_tracer.record_sql, 'off')

    def test_high_security_on_keep_local_capture_params(self):
        server = {}
        self.local.high_security = True
        self.local.capture_params = False
        c = newrelic.core.config.apply_server_side_settings(server, self.local)
        self.assertFalse(c.capture_params)

    def test_high_security_on_keep_local_record_sql(self):
        server = {}
        self.local.high_security = True
        self.local.transaction_tracer.record_sql = 'obfuscated'
        c = newrelic.core.config.apply_server_side_settings(server, self.local)
        self.assertEqual(c.transaction_tracer.record_sql, 'obfuscated')


class TestAgentAttributesValid(unittest.TestCase):
    def test_valid_wildcards(self):
        result = newrelic.core.config._parse_attributes('a.b* b* c.* AB* *')
        self.assertEqual(result, ['a.b*', 'b*', 'c.*', 'AB*', '*'])

    def test_invalid_wildcards(self):
        result = newrelic.core.config._parse_attributes('a b.*.c d *e')
        self.assertEqual(result, ['a', 'd'])

    def test_empty_list(self):
        result = newrelic.core.config._parse_attributes('')
        self.assertEqual(result, [])

    def test_valid_no_wildcard(self):
        result = newrelic.core.config._parse_attributes('aa Ab c a_b')
        self.assertEqual(result, ['aa', 'Ab', 'c', 'a_b'])

    def test_validate_attribute_size(self):
        result = newrelic.core.config._parse_attributes('a' * 255 + ' abc')
        self.assertEqual(result, ['a' * 255, 'abc'])
        result = newrelic.core.config._parse_attributes('a' * 256 + ' abc')
        self.assertEqual(result, ['abc'])

    def test_unicode_strings_length(self):
        result = newrelic.core.config._parse_attributes(u'\u00F6' * 127 +
                u' \U0001F6B2')
        self.assertEqual(result, [u'\u00F6' * 127, u'\U0001F6B2'])
        result = newrelic.core.config._parse_attributes(u"\u00F6" * 128 +
                u' \U0001F6B2')
        self.assertEqual(result, [u'\U0001F6B2'])


class TestCrossProcessIdParsing(unittest.TestCase):
    def test_parse_from_cross_process_id_success(self):
        config = {
            'cross_process_id': '800#900',
        }
        settings = newrelic.core.config.apply_server_side_settings(config)
        assert settings.account_id == '800'
        assert settings.application_id == '900'

    def test_parse_account_id_success(self):
        config = {
            'cross_process_id': '1#1',
            'account_id': '800',
        }
        settings = newrelic.core.config.apply_server_side_settings(config)
        assert settings.account_id == '800'

    def test_parse_application_id_success(self):
        config = {
            'cross_process_id': '1#1',
            'application_id': '800',
        }
        settings = newrelic.core.config.apply_server_side_settings(config)
        assert settings.application_id == '800'

    def test_parse_invalid_cross_process_id(self):
        config = {
            'cross_process_id': '700#800#900',
        }
        settings = newrelic.core.config.apply_server_side_settings(config)
        assert not settings.account_id
        assert not settings.application_id


if __name__ == '__main__':
    unittest.main()
