
'''
Created on Jul 26, 2011

@author: sdaubin
'''
import unittest
from newrelic.core.remote import JsonRemote,NewRelicService
from newrelic.core.exceptions import ForceRestartException

class NewRelicServiceTest(unittest.TestCase):
        
    def test_connect(self):
        remote = JsonRemote("d67afc830dab717fd163bfcb0b8b88423e9a1a3b", "staging-collector.newrelic.com", 80)
        service = NewRelicService(remote,app_names=["Python Unit Test1"])
        self.assertEqual(None, service.agent_run_id)
        service.connect()
        self.assertNotEqual(None, service.agent_run_id)
        self.assertTrue(service.connected())
        print service.configuration
        print service.configuration.server_settings
        self.assertEqual(0.777, service.configuration.transaction_tracer.transaction_threshold)
        service.shutdown()
        self.assertEqual(None, service.agent_run_id)
        
    def test_send_metric_data(self):
        remote = JsonRemote("d67afc830dab717fd163bfcb0b8b88423e9a1a3b", "staging-collector.newrelic.com", 80)
        service = NewRelicService(remote,app_names=["Python Unit Test1"])
        conn = remote.create_connection()
        service.connect(conn)
        metric_data = [[{"name":"foo"},[1,1,1,1,1,1]]]
        service.send_metric_data(conn, metric_data)
        conn.close()

class JsonRemoteTest(unittest.TestCase):
    
    def test_remote_method_uri(self):
        remote = JsonRemote("license", "staging", 80)
        self.assertEqual("/agent_listener/9/license/connect?marshal_format=json", remote.remote_method_uri("connect")) 

    def test_remote_method_uri_with_run_id(self):
        remote = JsonRemote("license", "staging", 80)
        self.assertEqual("/agent_listener/9/license/metric_data?marshal_format=json&run_id=12", remote.remote_method_uri("metric_data",12)) 

    def test_create_connection(self):
        remote = JsonRemote("license", "staging", 80)
        conn = remote.create_connection()
        conn.close() 

    def test_remote_invoke(self):
        remote = JsonRemote("d67afc830dab717fd163bfcb0b8b88423e9a1a3b", "staging-collector.newrelic.com", 80)
        conn = remote.create_connection()
        redirect_host = remote.invoke_remote(conn, "get_redirect_host", True, None)
        conn.close()
        self.assertEqual("staging-collector-1.newrelic.com", redirect_host)

    def test_parse_response_exception_invalid(self):
        remote = JsonRemote("license", "staging", 80)
        try:
            remote.parse_response("{\"exception\":{}}")
        except Exception as ex:
            self.assertTrue(str(ex).index("Unknown exception") == 0, ex)
            
    def test_parse_response_exception_restart(self):
        remote = JsonRemote("license", "staging", 80)
        try:
            remote.parse_response("{\"exception\":{\"error_type\":\"ForceRestartException\",\"message\":\"restart\"}}")
        except ForceRestartException as ex:
            self.assertEqual("restart", str(ex))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
