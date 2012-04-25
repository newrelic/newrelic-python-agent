'''
Created on Jul 26, 2011

@author: sdaubin
'''

import sys
import os
import httplib
import socket
import string
import time
import logging

try:
    import json
except:
    try:
        import simplejson as json
    except:
        import newrelic.lib.simplejson as json

import newrelic
import newrelic.core.config

from newrelic.core.exceptions import raise_newrelic_exception,ForceRestartException,ForceShutdownException
from newrelic.core import environment

_logger = logging.getLogger(__name__)

class NewRelicService(object):
    def __init__(self, remote,app_names=["FIXME Python test"]):
        self._remote = remote
        self._agent_run_id = None
        self._app_names = app_names
        self._configuration = None
        self._metric_data_time = time.time()

    @property
    def configuration(self):
        return self._configuration

    def get_agent_run_id(self):
        return self._agent_run_id


    def agent_version(self):
        return newrelic.version

    def shutdown(self):
        if self.agent_run_id is not None:
            try:
                conn = self._remote.create_connection()
                try:
                    self.invoke_remote(conn, "shutdown", True, self._agent_run_id)
                finally:
                    conn.close()

            except Exception, ex:
                #FIXME log
                _logger.error('Error on agent shutdown.')
                _logger.exception('Exception Details.')
                pass

            # FIXME Need to resolve app naming issue.
            name = self._app_names[0]
            self._configuration = None

            self._agent_run_id = None

    def connected(self):
        return self._agent_run_id is not None

    def connect(self,conn=None):
        _logger.debug("Service connection.")
        create_conn = conn is None
        _logger.debug("Connection required %s." % create_conn)
        try:
            if create_conn:
                _logger.debug("Creating new connection.")
                conn = self._remote.create_connection()
                _logger.debug("Got new connection.")
            redirect_host = self.invoke_remote(conn, "get_redirect_host", True, None)

            if redirect_host is not None:
                self._remote.host = redirect_host
                _logger.debug("Collector redirection to %s" % redirect_host)

            _logger.info('New Relic Data Collector (%s:%s)' % (
                    self._remote.host, self._remote._port))

            self.parse_connect_response(self.invoke_remote(conn, "connect", True, None, self.get_start_options()))
        except:
            _logger.exception('Failed to connect to core application.')
        finally:
            if create_conn:
                conn.close()

        return self.connected()

    def send_error_data(self,conn,error_data):
        if not self.connected():
            raise "Not connected"
        res = self.invoke_remote(conn,"error_data",True,self._agent_run_id,self._agent_run_id,error_data)
        return res

    def send_trace_data(self,conn,trace_data):
        if not self.connected():
            raise "Not connected"
        res = self.invoke_remote(conn,"transaction_sample_data",True,self._agent_run_id,self._agent_run_id,trace_data)
        return res

    def send_sql_data(self,conn,sql_data):
        if not self.connected():
            raise "Not connected"
        res = self.invoke_remote(conn,"sql_trace_data",True,self._agent_run_id,self._agent_run_id,sql_data)
        return res

    def send_metric_data(self,conn,metric_data):
        if not self.connected():
            raise "Not connected"
        now = time.time()
        res = self.invoke_remote(conn,"metric_data",True,self._agent_run_id,self._agent_run_id,self._metric_data_time,now,metric_data)
        self._metric_data_time = now
        return res

    def get_app_names(self):
        return self._app_names

    def get_identifier(self):
        return string.join(self.get_app_names(),',')

    def get_start_options(self):
        options = {"pid":os.getpid(),"language":"python","host":socket.gethostname(),"app_name":self.get_app_names(),"identifier":self.get_identifier(),"agent_version":self.agent_version(),"environment":environment.environment_settings(),"settings":newrelic.core.config.global_settings_dump() }
        return options

    def parse_connect_response(self, response):
        if "agent_run_id" in response:
            self._agent_run_id = response.pop("agent_run_id")
        else:
            raise Exception("The connect response did not include an agent run id: %s", str(response))

        # we're hardcoded to a 1 minute harvest
        response.pop("data_report_period")

        _logger.debug('Server side settings %s' % response)

        # FIXME Need to resolve app naming issue.
        name = self._app_names[0]
        settings = newrelic.core.config.create_settings_snapshot(response)
        self._configuration = settings

        _logger.debug('Application settings %s' % settings)

    def invoke_remote(self, connection, method, compress = True, agent_run_id = None, *args):
        try:
            return self._remote.invoke_remote(connection, method, compress, agent_run_id, *args)
        except ForceShutdownException, ex:
            self._agent_run_id = None
            raise ex
        except ForceRestartException, ex:
            self._agent_run_id = None
            raise ex

    agent_run_id = property(get_agent_run_id, None, None, "The agent run id")

class NRJSONEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            iterable = iter(o)
        except TypeError:
            pass
        else:
            return list(iterable)
        return json.JSONEncoder.default(self, o)

'''
    def iterencode(self, obj, _one_shot=False):
        if hasattr(obj, '_asdict'):
            gen = json.JSONEncoder.iterencode(self, obj._asdict(), _one_shot=False)
        else:
            gen = json.JSONEncoder.iterencode(self, obj, _one_shot)
        for chunk in gen:
            yield chunk
'''

class JSONRemote(object):
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
        self._encoder = NRJSONEncoder(encoding='Latin-1')

    def get_host(self):
        return self._host


    def set_host(self, value):
        self._host = value


    def create_connection(self):
        # FIXME add ssl support
        _logger.debug("Attempt connection to %s:%d" %(self._host, self._port))
        try:
            conn = httplib.HTTPConnection(self._host, self._port)
            _logger.debug("Created object.")
            conn.connect()
            _logger.debug("Connected to %s:%d" %(self._host, self._port))
        except:
            _logger.exception('Connection failed')
        return conn

    def raise_exception(self, ex):
        # REVIEW
        if "error_type" in ex and "message" in ex:
            raise_newrelic_exception(ex["error_type"], ex["message"])

        raise Exception("Unknown exception: %s" % str(ex))

    def parse_response(self, str):
        try:
            res = json.loads(str)
        except Exception, ex:
            # FIXME log json
            raise Exception("Json load failed error:", ex.message, ex)

        if "exception" in res:
            self.raise_exception(res["exception"])
        if "return_value" in res:
            return res["return_value"]

        raise Exception("Unexpected response format: %s" % str)


    def invoke_remote(self, connection, method, compress = True, agent_run_id = None, *args):
        # FIXME BIG HACK
        if method == 'sql_trace_data':
            json_data = self._encoder.encode(args[1:])
        else:
            json_data = self._encoder.encode(args)
        url = self.remote_method_uri(method, agent_run_id)

        headers = {}

        headers["Content-Encoding"] = "identity" # FIXME deflate

        user_agent = 'NewRelic-PythonAgent/%s (Python %s)' % (
                newrelic.version, sys.version.split()[0])

        headers['User-Agent'] = user_agent

        connection.request("POST", url, json_data, headers)
        response = connection.getresponse()

        encoding = response.getheader("Content-Encoding")

        if response.status is httplib.OK:
            reply = response.read()
            try:
                return self.parse_response(reply)
            except Exception, ex:
                _logger.error('Error parsing JSON response.')
                _logger.exception('Exception Details.')
                _logger.debug('JSON Response')
                _logger.debug(json_data)
                raise ex
        else:
            raise Exception("%s failed: status code %i" % (method, response.status))


    def remote_method_uri(self, method, agent_run_id = None):
        uri = "/agent_listener/%i/%s/%s?marshal_format=json" % (self.PROTOCOL_VERSION,self._license_key,method)
        if agent_run_id is not None:
            uri += "&run_id=%i" % agent_run_id
        return uri

    host = property(get_host, set_host, None, "The New Relic service host")


