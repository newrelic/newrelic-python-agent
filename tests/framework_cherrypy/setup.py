from __future__ import print_function

from setuptools import setup

def entry_point(module, function=None):
    function = function or 'instrument_%s' % module.replace('.', '_')
    return '%s = newrelic_hooks.framework_cherrypy:%s' % (module, function)

ENTRY_POINTS = [
    entry_point('cherrypy._cpreqbody'),
    entry_point('cherrypy._cprequest'),
    entry_point('cherrypy._cpdispatch'),
    entry_point('cherrypy._cpwsgi'),
    entry_point('cherrypy._cptree'),
]

setup_kwargs = dict(
    name = 'newrelic_hooks.framework_cherrypy',
    version = '0.0.0',
    packages = ['newrelic_hooks'],
    package_dir = {'newrelic_hooks': 'src'},
    entry_points = { 'newrelic.hooks': ENTRY_POINTS },
)

setup(**setup_kwargs)
