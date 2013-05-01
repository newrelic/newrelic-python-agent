import unittest
import zlib
import base64
import time

import newrelic.packages.simplejson as simplejson

from newrelic.core.profile_sessions import (
        ProfileSessionManager, ProfileSession, CallTree,
        SessionState, SessionType, profile_session_manager)

def _(method_tuple):
    filename, func_name, func_line, exec_line = method_tuple
    if func_line == exec_line:
        return (filename, '@%s#%s' % (func_name, func_line), exec_line)
    else:
        return (filename, '%s#%s' % (func_name, func_line), exec_line)

class TestCallTree(unittest.TestCase):

    def setUp(self):
        self.method_a = ('file_a', 'method_a', 10, 10)
        self.method_b = ('file_b', 'method_b', 20, 20)
        self.method_c = ('file_c', 'method_c', 25, 25)
        self.method_d = ('file_d', 'method_d', 15, 15)
        self.call_tree = CallTree(self.method_a)

    def test_flatten(self):
        expected = [_(self.method_a), 0, 0, []]
        self.assertEqual(self.call_tree.flatten(), expected)

class TestProfileSession(unittest.TestCase):
    def setUp(self):
        self.method_a = ('file_a', 'method_a', 10, 10)
        self.method_b = ('file_b', 'method_b', 20, 20)
        self.method_c = ('file_c', 'method_c', 25, 25)
        self.method_d = ('file_d', 'method_d', 15, 15)

        self.stack_trace1 = [self.method_a, self.method_b, self.method_c]
        self.stack_trace2 = [self.method_a, self.method_d, self.method_c]
        self.stack_trace3 = [self.method_b, self.method_d, self.method_c]

        self.g_profile_session = ProfileSession(-1, time.time()+2)
        self.x_profile_session = ProfileSession(-1, time.time()+2, xray_id=7)


    def test_update_call_tree(self):
        self.assertFalse(self.g_profile_session.update_call_tree('ABCD',
            self.stack_trace2), msg="Invalid call bucket.")

        self.assertTrue(self.g_profile_session.update_call_tree('REQUEST',
            self.stack_trace1))

        bucket = self.g_profile_session.call_buckets['REQUEST']
        tree = bucket.get(self.stack_trace1[0])

        self.assertEqual(len(self.g_profile_session.call_buckets['REQUEST']), 1)

        st1_expected = [_(self.method_a), 1, 0, [ [_(self.method_b), 1, 0,
            [[_(self.method_c), 1, 0, []]]] ] ]
        self.assertEqual(st1_expected, tree.flatten())

        self.assertTrue(self.g_profile_session.update_call_tree('REQUEST',
            self.stack_trace2))

        self.assertEqual(len(self.g_profile_session.call_buckets['REQUEST']), 1)

        st2_expected = [_(self.method_a), 2, 0,
                [
                    [_(self.method_b), 1, 0, [[_(self.method_c), 1, 0, []]]],
                    [_(self.method_d), 1, 0, [[_(self.method_c), 1, 0, []]]]
                ]
            ]
        self.assertEqual(st2_expected, tree.flatten())

        self.assertTrue(self.g_profile_session.update_call_tree('REQUEST',
            self.stack_trace3))

        self.assertEqual(len(self.g_profile_session.call_buckets['REQUEST']), 2)
        self.assertEqual(st2_expected, tree.flatten())

        tree = bucket.get(self.stack_trace3[0])

        st3_expected = [_(self.method_b), 1, 0, [ [_(self.method_d), 1, 0,
            [[_(self.method_c), 1, 0, []]]] ] ]
        self.assertEqual(st3_expected, tree.flatten())

    def test_generic_profiler_profile_data(self):

        def unscramble(data):
            if data:
                return zlib.decompress(base64.standard_b64decode(data))

        self.assertEqual(self.g_profile_session.profiler_type,
                SessionType.GENERIC)

        self.assertEqual(self.g_profile_session.state,
                SessionState.RUNNING)

        # Try to get profile_data before the session is finished.

        prof_data = self.g_profile_session.profile_data()
        self.assertTrue(prof_data is None,
                'Profiling has not finished. Data should be None.')

        # Finish the session and then get the profile_data

        self.g_profile_session.state = SessionState.FINISHED
        prof_data = self.g_profile_session.profile_data()
        self.assertTrue(prof_data is None, 'Expected None. Instead got %s' %
                prof_data)

        self.g_profile_session.update_call_tree('REQUEST', self.stack_trace1)
        p = self.g_profile_session.profile_data()[0]

        # profile_id
        self.assertEqual(p[0], -1)
        # start_time < stop_time
        self.assertTrue(p[1]<p[2])
        # sample_count
        self.assertEqual(p[3], 0)
        # thread_count
        self.assertEqual(p[5], 1)
        # Non-runnable thread count - always zero
        self.assertEqual(p[6], 0)
        # xray_id
        self.assertEqual(p[7], None)

        expected = '{"REQUEST": [[["file_a", "@method_a#10", 10],'\
                ' 1, 0, [[["file_b", "@method_b#20", 20], 1, 0, [[["file_c", '\
                '"@method_c#25", 25], 1, 0, []]]]]]]}'
        self.assertEqual(unscramble(p[4]), expected)


    def test_xray_profiler_profile_data(self):

        def unscramble(data):
            if data:
                return zlib.decompress(base64.standard_b64decode(data))

        self.assertEqual(self.x_profile_session.profiler_type,
                SessionType.XRAY)

        self.assertEqual(self.x_profile_session.state,
                SessionState.RUNNING)

        self.x_profile_session.update_call_tree('REQUEST', self.stack_trace1)
        self.x_profile_session.update_call_tree('REQUEST', self.stack_trace2)
        p = self.x_profile_session.profile_data()[0]

        # profile_id
        self.assertEqual(p[0], -1)
        # start_time < stop_time
        self.assertTrue(p[1]<p[2])
        # sample_count
        self.assertEqual(p[3], 0)
        # thread_count
        self.assertEqual(p[5], 1)
        # Non-runnable thread count - always zero
        self.assertEqual(p[6], 0)
        # xray_id
        self.assertEqual(p[7], 7)
        expected = '{"REQUEST": [[["file_a", "@method_a#10", 10], 2,'\
                ' 0, [[["file_b", "@method_b#20", 20], 1, 0, [[["file_c",'\
                ' "@method_c#25", 25], 1, 0, []]]], [["file_d", "@method_d#15", 15],'\
                ' 1, 0, [[["file_c", "@method_c#25", 25], 1, 0, []]]]]]]}'
        self.assertEqual(unscramble(p[4]), expected)


class TestProfileSessionManager(unittest.TestCase):

    def test_profile_session_manager_singleton(self):
        a = profile_session_manager()
        self.assertNotEqual(a, None)

        b = profile_session_manager()
        self.assertEqual(a, b)

    def test_start_full_profile_session(self):
        manager = ProfileSessionManager()

        # Create a full profile session
        self.assertTrue(manager.start_profile_session('app', -1, time.time()+1))

        fps = manager.full_profile_session
        # Check if this is created correctly.
        self.assertTrue(isinstance(fps, ProfileSession))

        # Session type must be GENERIC
        self.assertEqual(fps.profiler_type, SessionType.GENERIC)

        # Full Profile Session must be running.
        self.assertEqual(fps.state, SessionState.RUNNING)

        # Create another full profile session while the first one is running.
        self.assertFalse(manager.start_profile_session('app', -1, time.time()+1),
                msg='Full profile session already running. This should have '
                'returned False.')

    def test_start_xray_profile_session(self):
        manager = ProfileSessionManager()

        key_txn1 = 'WebTransaction/abc'
        key_txn2 = 'WebTransaction/def'
        # Create a xray profile session
        self.assertTrue(manager.start_profile_session('app', -1, time.time()+1,
                key_txn=key_txn1, xray_id=7))

        xps = manager.application_xrays['app'].get(key_txn1)
        # Check if this is added to the dictionary.
        self.assertFalse(xps is None)

        # Check if profile session obj was created correctly.
        self.assertTrue(isinstance(xps, ProfileSession))

        # Session type must be XRAY
        self.assertEqual(xps.profiler_type, SessionType.XRAY)

        # Profile Session must be running.
        self.assertEqual(xps.state, SessionState.RUNNING)

        # Create another xray profile session with exact same key txn, while
        # the first one is running.
        self.assertFalse(manager.start_profile_session('app', -1, time.time()+1,
            key_txn=key_txn1, xray_id=7),
            msg='Xray profile session with the same name is already '
            'running. This should have returned False.')

        # Create an xray profile session with a different key txn.
        self.assertTrue(manager.start_profile_session('app', -1, time.time()+1,
            key_txn=key_txn2, xray_id=8))

        # Make sure none of the sessions have finished.
        self.assertEqual(manager.finished_sessions, {})

    def test_stop_profile_session(self):
        manager = ProfileSessionManager()
        key_txn1 = 'WebTransaction/abc'
        key_txn2 = 'WebTransaction/def'

        manager.start_profile_session('app', -1, time.time() + 2)
        manager.start_profile_session('app', -1, time.time() + 2, key_txn=key_txn1)
        manager.start_profile_session('app', -1, time.time() + 2, key_txn=key_txn2)

        fps = manager.full_profile_session
        xps1 = manager.application_xrays['app'].get(key_txn1)
        xps2 = manager.application_xrays['app'].get(key_txn2)

        # Make sure none of the sessions have finished.
        self.assertEqual(manager.finished_sessions, {})

        manager.stop_profile_session('app')
        self.assertTrue(manager.full_profile_session is None)
        self.assertEqual(manager.finished_sessions['app'], [fps], msg='Only full'\
                'profile session has finished.')

        manager.stop_profile_session('app', key_txn1)
        self.assertTrue(manager.application_xrays['app'].get(key_txn1) is None)
        self.assertEqual(manager.finished_sessions['app'], [fps, xps1])

        manager.stop_profile_session('app', key_txn2)
        self.assertEqual(manager.application_xrays['app'], {})
        self.assertEqual(manager.finished_sessions['app'], [fps, xps1, xps2])

    def test_profile_data(self):
        def unscramble(data):
            return base64.standard_b64decode(data)

        manager = ProfileSessionManager()
        key_txn1 = 'abc'
        key_txn2 = 'def'

        manager.start_profile_session('app', -1, time.time() + 2)
        manager.start_profile_session('app', -1, time.time() + 2, key_txn=key_txn1)
        manager.start_profile_session('app', -1, time.time() + 2, key_txn=key_txn2)

        fps = manager.full_profile_session
        xps1 = manager.application_xrays['app'].get(key_txn1)
        xps2 = manager.application_xrays['app'].get(key_txn2)

        prof_data = manager.profile_data('app')
        # Get the data.
        self.assertEqual(len(list(prof_data)), 2)

        manager.stop_profile_session('app')
        manager.stop_profile_session('app', key_txn1)
        prof_data = manager.profile_data('app')

        self.assertEqual(len(list(prof_data)), 3)

        prof_data = manager.profile_data('app')

        self.assertEqual(len(list(prof_data)), 1)

        manager.stop_profile_session('app', key_txn2)
        prof_data = manager.profile_data('app')
        self.assertEqual(len(list(prof_data)), 1)

        prof_data = manager.profile_data('app')
        self.assertEqual(len(list(prof_data)), 0)

if __name__ == '__main__':
    unittest.main()
