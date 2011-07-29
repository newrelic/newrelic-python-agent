'''
Created on Jul 27, 2011

@author: sdaubin
'''
import collections
from newrelic.core.remote import JsonRemote
from newrelic.core.harvest import Harvester
from newrelic.core.application import Application

_newrelic_agent = None

def newrelic_agent():
    global _newrelic_agent
    
    if _newrelic_agent:
        return _newrelic_agent
    else:
        _newrelic_agent = Agent(_initialize_config())
        return _newrelic_agent

def _initialize_config():
    # FIXME implement
    Config = collections.namedtuple('Config', ['license_key', 'host','port'])
    return Config("license","host",80)

class Agent(object):
    def __init__(self,config):
        self._remote = JsonRemote(config.license_key, config.host, config.port)
        self._harvester = Harvester(self._remote,60)
        
        app = Application(self._remote, ["Python Test"])
        self._harvester.register_harvest_listener(app)

    def get_remote(self):
        return self._remote
    
    def shutdown(self):
        self._harvester.stop_harvest_thread()

    remote = property(get_remote, None, None, None)
    