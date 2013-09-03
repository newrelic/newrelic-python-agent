import newrelic.packages.six as six

import newrelic.api.external_trace

def instrument(module):

    def url_opener_open(opener, fullurl, *args, **kwargs):
        if isinstance(fullurl, six.string_types):
            return fullurl
        else:
            return fullurl.get_full_url()

    newrelic.api.external_trace.wrap_external_trace(
        module, 'OpenerDirector.open', 'urllib2',
        url_opener_open)
