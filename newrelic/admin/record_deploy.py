from __future__ import print_function

import pwd
import os
import json

import newrelic.packages.requests.adapters as adapters

unpatched_request_url = adapters.HTTPAdapter.request_url

from newrelic.admin import command, usage

from newrelic.common import certs
from newrelic.config import initialize
from newrelic.core.config import global_settings
from newrelic.network.addresses import proxy_details

from newrelic.packages import requests

# Remove a patch to the request_url forcing the full URL to be sent in the
# request line. See _requests_request_url_workaround in data_collector.py
# This is currently unsupported by the API endpoint. The common
# case is to send only the relative URL.
adapters.HTTPAdapter.request_url = unpatched_request_url


@command(
    "record-deploy",
    "app_id config_file revision [description changelog user timestamp]",
    "Records a deployment for the monitored application.",
)
def local_config(args):
    import sys

    if len(args) < 2:
        usage("record-deploy")
        sys.exit(1)

    def _args(
        app_id,
        config_file,
        revision,
        description=None,
        changelog=None,
        user=None,
        timestamp=None,
        *args
    ):
        return (
            app_id,
            config_file,
            revision,
            description,
            changelog,
            user,
            timestamp,
        )

    app_id, config_file, revision, description, changelog, user, timestamp = _args(
        *args
    )

    settings = global_settings()

    settings.monitor_mode = False

    initialize(config_file)

    api_key = settings.api_key or "NO API KEY WAS SET IN AGENT CONFIGURATION"

    host = settings.host

    if host == "collector.newrelic.com":
        host = "api.newrelic.com"
    elif host.startswith("collector.eu"):
        host = "api.eu.newrelic.com"
    elif host == "staging-collector.newrelic.com":
        host = "staging-api.newrelic.com"

    port = settings.port

    url = "%s://%s/v2/applications/%s/deployments.json"

    scheme = "https"
    server = port and "%s:%d" % (host, port) or host

    url = url % (scheme, server, app_id)

    proxy_scheme = settings.proxy_scheme
    proxy_host = settings.proxy_host
    proxy_port = settings.proxy_port
    proxy_user = settings.proxy_user
    proxy_pass = settings.proxy_pass

    if proxy_scheme is None:
        proxy_scheme = "https"

    timeout = settings.agent_limits.data_collector_timeout

    proxies = proxy_details(
        proxy_scheme, proxy_host, proxy_port, proxy_user, proxy_pass
    )

    if user is None:
        user = pwd.getpwuid(os.getuid()).pw_gecos

    data = {}
    data["deployment"] = {}
    data["deployment"]["revision"] = revision

    if description is not None:
        data["deployment"]["description"] = description
    if changelog is not None:
        data["deployment"]["changelog"] = changelog
    if user is not None:
        data["deployment"]["user"] = user
    if timestamp is not None:
        data["deployment"]["timestamp"] = timestamp

    headers = {}
    headers["X-Api-Key"] = api_key
    headers["Content-Type"] = "application/json"

    cert_loc = settings.ca_bundle_path
    if cert_loc is None:
        cert_loc = certs.where()

    if settings.debug.disable_certificate_validation:
        cert_loc = False

    data = json.dumps(data)

    r = requests.post(
        url,
        proxies=proxies,
        headers=headers,
        timeout=timeout,
        data=data,
        verify=cert_loc,
    )

    if r.status_code != 201:
        raise RuntimeError(
            "An unexpected HTTP response of %r was received "
            "for request made to %r. The API key for the request was "
            "%r. The payload for the request was %r. The response "
            "payload for the request was %r. If this issue "
            "persists then please report this problem to New Relic "
            "support for further investigation."
            % (r.status_code, url, api_key, data, r.json())
        )
