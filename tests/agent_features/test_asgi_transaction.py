import pytest
import asyncio
from testing_support.sample_asgi_applications import simple_app_v2, simple_app_v3
from testing_support.fixtures import validate_transaction_metrics, override_application_settings


class AsgiRequest(object):
    scope = {
        'asgi': {'spec_version': '2.1', 'version': '3.0'},
        'client': ('127.0.0.1', 54768),
        'headers': [(b'host', b'localhost:8000')],
        'http_version': '1.1',
        'method': 'GET',
        'path': '/',
        'query_string': b'',
        'raw_path': b'/',
        'root_path': '',
        'scheme': 'http',
        'server': ('127.0.0.1', 8000),
        'type': 'http'
    }

    def __init__(self):
        self.sent = []

    async def receive(self):
        pass
        
    async def send(self, event):
        self.sent.append(event)


@pytest.mark.parametrize("naming_scheme", (None, "component", "framework"))
def test_simple_app(naming_scheme):
    request = AsgiRequest()

    async def _test():
        await simple_app_v3(request.scope, request.receive, request.send)
        assert request.sent[0]["type"] == "http.response.start"
        assert request.sent[0]["status"] == 200
        assert request.sent[1]["type"] == "http.response.body"

    if naming_scheme in ("component", "framework"):
        expected_name = "testing_support.sample_asgi_applications:simple_app_v3"
        expected_group = "Function"
    else:
        expected_name = ""
        expected_group = "Uri"

    @validate_transaction_metrics(name=expected_name, group=expected_group)
    @override_application_settings({"transaction_name.naming_scheme": naming_scheme})
    def run():
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_test())
    
    run()