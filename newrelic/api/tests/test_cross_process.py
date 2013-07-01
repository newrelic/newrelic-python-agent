import unittest
import time

import newrelic.lib.simplejson as simplejson

from newrelic.api.application import application_instance
from newrelic.core.config import global_settings, create_settings_snapshot
from newrelic.api.web_transaction import (deobfuscate, obfuscate,
        WebTransaction)

class TestCase(unittest.TestCase):

    def _run_cross_process_process_response(self, enabled,
            client_cross_process_id, client_cross_process_id_fmt,
            trusted_account_ids, content_length, queue_start, start_time,
            end_time, transaction_name, expect_result):

        def test_args():
            return repr((enabled, client_cross_process_id,
                    client_cross_process_id_fmt, trusted_account_ids,
                    content_length, queue_start, start_time, end_time,
                    transaction_name, expect_result))

        cross_process_id = '1#1'
        encoding_key = '0123456789'

        class Application(object):
            def activate(self):
                pass
            def normalize_name(self, name, rule_type):
                return name, False

        application = Application()

        application.global_settings = create_settings_snapshot()
        application.global_settings.enabled = True

        settings = {}

        settings['cross_application_tracer.enabled'] = enabled

        settings['cross_process_id'] = cross_process_id
        settings['encoding_key'] = encoding_key
        settings['trusted_account_ids'] = trusted_account_ids

        application.settings = create_settings_snapshot(settings)

        application.active = True
        application.enabled = True

        environ = {}

        if client_cross_process_id is not None:
            environ['HTTP_X_NEWRELIC_ID'] = client_cross_process_id_fmt(
                    client_cross_process_id, encoding_key)

        if content_length >= 0:
            environ['CONTENT_LENGTH'] = str(content_length)

        transaction = WebTransaction(application, environ)

        self.assertTrue(transaction.enabled)

        transaction.name_transaction(transaction_name)

        transaction.queue_start = queue_start
        transaction.start_time = start_time
        transaction.end_time = end_time

        headers = dict(transaction.process_response('200 OK', []))

        # Check for whether header is present when expected.

        self.assertEqual('X-NewRelic-App-Data' in headers, expect_result,
                'Failed for %s and headers of %r.' % (test_args(), headers))

        # Check for whether metric is presented when expected.

        metric = 'ClientApplication/%s/all' % client_cross_process_id

        self.assertEqual(metric in transaction._custom_metrics, expect_result,
                'Failed for %s.' % test_args())

        # Check if web transaction name was frozen.

        self.assertEqual(transaction._frozen_path is not None, expect_result,
                 'Failed for %s.' % test_args())

        # Nothing else to check if no response header expected.

        if not expect_result:
            return

        # Check that decoded client details are what is expected.

        client_account_id, client_application_id = \
                map(int, client_cross_process_id.split('#'))

        self.assertEqual(transaction.client_cross_process_id,
                client_cross_process_id, 'Failed for %s.' % test_args())
        self.assertEqual(transaction.client_account_id,
                client_account_id, 'Failed for %s.' % test_args())
        self.assertEqual(transaction.client_application_id,
                client_application_id, 'Failed for %s.' % test_args())

        # Now check the content of the response header.

        header_value = headers['X-NewRelic-App-Data']
        deobfuscated_header = deobfuscate(header_value, encoding_key)
        decoded_data = simplejson.loads(deobfuscated_header)

        if queue_start:
            queue_time = start_time - queue_start
        else:
            queue_time = 0

        if end_time:
            duration = end_time = start_time
        else:
            duration = time.time() - start_time

        self.assertEqual(len(decoded_data), 7,
                'Failed for %s where decoded data was %s.' % (test_args(),
                decoded_data))

        self.assertEqual(decoded_data[0], cross_process_id,
                'Failed for %s.' % test_args())
        self.assertEqual(decoded_data[1], u'WebTransaction/Function/' + (
                transaction_name), 'Failed for %s.' % test_args())
        self.assertEqual(decoded_data[2], queue_time,
                'Failed for %s.' % test_args())

        # This one is dependent on time. If less than a second
        # difference then say is okay.

        self.assertTrue(abs(duration - decoded_data[3]) < 1.0,
                'Failed for %s.' % test_args())

        self.assertEqual(decoded_data[4], content_length,
                'Failed for %s.' % test_args())

    def test_cross_process_response(self):
        now = time.time()

        def _o(value, key):
            return obfuscate(value, key)

        def _p(value, key):
            return value

        tests = [
            # No incoming cross process header.

            (True, None, _p, [1], -1, 1, now, None, 'Name', False),

            # Empty incoming cross process header.

            (True, '', _p, [1], -1, 1, now, None, 'Name', False),

            # Incoming cross process header not obfuscated.

            (True, '1#2', _p, [1], -1, 1, now, None, 'Name', False),

            # No field separator in cross process ID.

            (True, u'1', _o, [1], -1, 1, now, None, 'Name', False),

            # Empty account field in cross process ID.

            (True, u'#2', _o, [1], -1, 1, now, None, 'Name', False),

            # Empty application field in cross process ID.

            (True, u'1#', _o, [1], -1, 1, now, None, 'Name', False),

            # Non integer account field in cross process ID.

            (True, u'A#2', _o, [1], -1, 1, now, None, 'Name', False),

            # Non integer application field in cross process ID.

            (True, u'1#B', _o, [1], -1, 1, now, None, 'Name', False),

            # No content length header.

            (True, u'1#2', _o, [1], -1, 0, now, None, 'Name', True),

            # Empty or zero for content length header.

            (True, u'1#2', _o, [1], 0, 0, now, None, 'Name', True),

            # Non zero content length header.

            (True, u'1#2', _o, [1], 1, 0, now, None, 'Name', True),

            # Non zero queueing time.

            (True, u'1#2', _o, [1], 1, 1, now, None, 'Name', True),

            # Transaction had been stopped.

            (True, u'1#2', _o, [1], 1, 1, now, now+2, 'Name', True),

            # Transaction with Latin-1 Unicode name.

            (True, u'1#2', _o, [1], 1, 1, now, now+2, u'Name', True),

            # Transaction with UTF-8 Unicode name.

            (True, u'1#2', _o, [1], 1, 1, now, now+2, unichr(0x0bf2), True),

            # Transaction with single quotes in name.

            (True, u'1#2', _o, [1], 1, 1, now, now+2, 'Name\'', True),

            # Transaction with double quotes in name.

            (True, u'1#2', _o, [1], 1, 1, now, now+2, 'Name\"', True),

            # List of trusted accounts is empty.

            (True, u'1#2', _o, [], 1, 1, now, now+2, 'Name', False),

            # Not in trusted list of accounts.

            (True, u'1#2', _o, [0], 1, 1, now, now+2, 'Name', False),

            # Disabled by agent configuration.

            (False, u'1#2', _o, [1], 1, 1, now, now+2, 'Name', False),
        ]

        for item in tests:
            self._run_cross_process_process_response(*item)

if __name__ == '__main__':
    unittest.main()
