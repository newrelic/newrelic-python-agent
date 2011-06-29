import sys
import string

def import_module(name):
    __import__(name)
    return sys.modules[name]

def import_object(name, object_path):
    module = import_module(name)
    segments = string.splitfields(object_path, '.', 1)

    object = module

    while True:
        if len(segments) == 1:
            return getattr(object, segments[0])
        else:
            object = getattr(object, segments[0])
            segments = string.splitfields(segments[1], '.', 1)
