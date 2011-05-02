from newrelic.agent import wrap_external_trace
from urlparse import urlparse

def format_path(url):
    parts = urlparse(url)
    return '%s/feedparser%s' % (parts[1], parts[2])
    
def instrument(module):
    wrap_external_trace(module, None, 'parse', format_path)
