def platform_url(host='platform-api.newrelic.com', port=None, ssl=True):
    """Returns the URL for talking to the data collector when reporting
    platform metrics.

    """

    url = '%s://%s/platform/v1/metrics'

    scheme = ssl and 'https' or 'http'
    server = port and '%s:%d' % (host, port) or host

    return url % (scheme, server)

def proxy_details(proxy_host, proxy_port, proxy_user, proxy_pass, ssl):
    """Returns the dictionary of proxy server settings. This is returned
    in form as expected by the 'requests' library when making requests.

    """

    if not proxy_host or not proxy_port:
        return

    scheme = ssl and 'https' or 'http'
    proxy = '%s:%d' % (proxy_host, proxy_port)

    if proxy_user is not None and proxy_pass is not None:
        proxy = 'http://%s:%s@%s' % (proxy_user, proxy_pass, proxy)

    return { scheme: proxy }
