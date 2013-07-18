def items(d):
    try:
        return d.iteritems()
    except AttributeError:
        return d.items()

def keys(d):
    try:
        return d.iterkeys()
    except AttributeError:
        return d.keys()

def values(d):
    try:
        return d.itervalues()
    except AttributeError:
        return d.values()

def listitems(d):
    if hasattr(d, 'iteritems'):  # Py 2.X
        return d.items()
    else:  # Py 3.X
        return list(d.items())

def listkeys(d):
    if hasattr(d, 'iterkeys'):  # Py 2.X
        return d.keys()
    else:  # Py 3.X
        return list(d.keys())

def listvalues(d):
    if hasattr(d, 'itervalues'):  # Py 2.X
        return d.values()
    else:  # Py 3.X
        return list(d.values())
