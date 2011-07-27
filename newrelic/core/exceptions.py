'''
Created on Jul 27, 2011

@author: sdaubin
'''

class InstructionException(Exception):
    def __init__(self, msg):
        super(InstructionException,self).__init__(msg)    

class ForceRestartException(InstructionException):
    def __init__(self, msg):
        super(ForceRestartException,self).__init__(msg)
        
        
def raise_newrelic_exception(ex_type, message):
    exceptions = {"ForceRestartException":ForceRestartException}
    if ex_type in exceptions:
        raise exceptions[ex_type](message)
    
    raise Exception("Unknown exception type " + ex_type + " with message \"" + message + "\"")