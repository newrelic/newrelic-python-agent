'''
Created on Aug 1, 2011

@author: sdaubin
'''
import platform

def environment_settings():
    """ Returns an array of arrays of environment settings
    """
    env = []
    
    append_setting(env, "OS",platform.system())
    append_setting(env, "OS version", platform.release())
    
    return env

def append_setting(env,key,value):
    env.append([key,value])