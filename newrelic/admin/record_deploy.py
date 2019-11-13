from __future__ import print_function

import pwd
import os

from newrelic.admin import command, usage

from newrelic.common import certs
from newrelic.config import initialize
from newrelic.core.config import global_settings
from newrelic.network.addresses import proxy_details

from newrelic.packages import requests

import newrelic.packages.requests.adapters as adapters

unpatched_request_url = adapters.HTTPAdapter.request_url

# Remove a patch to the request_url forcing the full URL to be sent in the
# request line. See _requests_request_url_workaround in data_collector.py
# This is currently unsupported by the API endpoint. The common
# case is to send only the relative URL.
adapters.HTTPAdapter.request_url = unpatched_request_url


def api_request_kwargs():
    settings = global_settings()
    api_key = settings.api_key or "NO API KEY WAS SET IN AGENT CONFIGURATION"

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

    cert_loc = settings.ca_bundle_path
    if cert_loc is None:
        cert_loc = certs.where()

    if settings.debug.disable_certificate_validation:
        cert_loc = False

    headers = {"X-Api-Key": api_key}

    return {
        'proxies': proxies,
        'headers': headers,
        'timeout': timeout,
        'verify': cert_loc,
    }


def fetch_app_id(app_name, server):
    url = "https://{}/v2/applications.json".format(server)
    r = requests.get(
        url,
        params={"filter[name]": app_name},
        **api_request_kwargs()
    )
    r.raise_for_status()

    response_json = r.json()
    if "applications" not in response_json:
        return

    for application in response_json["applications"]:
        if application["name"] == app_name:
            return application["id"]


@command(
    "record-deploy",
    "config_file description [revision changelog user]",
    "Records a deployment for the monitored application.",
)
def record_deploy(args):
    import sys

    if len(args) < 2:
        usage("record-deploy")
        sys.exit(1)

    def _args(config_file, description, revision="Unknown", changelog=None,
            user=None, *args):
        return config_file, description, revision, changelog, user

    config_file, description, revision, changelog, user = _args(*args)

    settings = global_settings()

    settings.monitor_mode = False

    initialize(config_file)

    host = settings.host

    if host == "collector.newrelic.com":
        host = "api.newrelic.com"
    elif host.startswith("collector.eu"):
        host = "api.eu.newrelic.com"
    elif host == "staging-collector.newrelic.com":
        host = "staging-api.newrelic.com"

    port = settings.port

    server = port and "%s:%d" % (host, port) or host

    app_id = fetch_app_id(settings.app_name, server=server)
    if app_id is None:
        raise RuntimeError(
            "The application named %r was not found in your account. Please "
            "try running the newrelic-admin server-config command to force "
            "the application to register with New Relic."
            % settings.app_name
        )

    url = "https://{}/v2/applications/{}/deployments.json".format(
            server, app_id)

    if user is None:
        user = pwd.getpwuid(os.getuid()).pw_gecos

    deployment = {}
    deployment["revision"] = revision

    if description:
        deployment["description"] = description
    if changelog:
        deployment["changelog"] = changelog
    if user:
        deployment["user"] = user

    data = {"deployment": deployment}

    r = requests.post(
        url,
        json=data,
        **api_request_kwargs()
    )

    if r.status_code != 201:
        raise RuntimeError(
            "An unexpected HTTP response of %r was received "
            "for request made to %r. The payload for the request was %r. "
            "The response payload for the request was %r. If this issue "
            "persists then please report this problem to New Relic "
            "support for further investigation."
            % (r.status_code, url, data, r.json())
        )
