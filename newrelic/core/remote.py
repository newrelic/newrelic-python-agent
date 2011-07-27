'''
Created on Jul 26, 2011

@author: sdaubin
'''
import json
import httplib

class JsonRemote(object):
    '''
    classdocs
    '''

    PROTOCOL_VERSION = 9

    def __init__(self, license_key, host, port):
        '''
        Constructor
        '''
        self._host = host
        self._port = port
        self._protocol = "http://"
        self._license_key = license_key

    def get_host(self):
        return self.__host


    def set_host(self, value):
        self.__host = value

        
    def create_connection(self):
        # FIXME add ssl support
        conn = httplib.HTTPConnection(self._host, self._port)        
        conn.connect()
        return conn
    
    def parse_response(self, str):
        res = json.loads(str)
        
        print str
        print res
        ex = res["exception"]
        if ex is not None:
            raise "" # FIXME
        
        return res["return_value"]
        
        
    def invoke_remote(self, connection, method, agent_run_id = None, *args):
        json_data = json.dumps(args)
        url = self.remote_method_uri(method, agent_run_id)
        
        headers = {"Content-Encoding" : "identity" } # FIXME deflate
        connection.request("POST", url, json_data, headers)
        response = connection.getresponse()
        
        encoding = response.getheader("Content-Encoding")
        
        if response.status is httplib.OK:
            reply = response.read()
            try:
                return parse_response(reply)
            except:
                pass
        
    
    def remote_method_uri(self, method, agent_run_id = None):
        uri = "/agent_listener/" + str(self.PROTOCOL_VERSION) + "/" + self._license_key + "/" + method + "?marshal_format=json"
        if agent_run_id is not None:
            uri += "&run_id=" + str(agent_run_id)
        return uri
    
    host = property(get_host, set_host, None, "The New Relic service host")
        
    