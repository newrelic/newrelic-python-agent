
'''
Created on Jul 26, 2011

@author: sdaubin
'''
import unittest
from newrelic.core.remote import JsonRemote

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
        print remote.invoke_remote(conn, "get_redirect_host", None)
        conn.close()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
