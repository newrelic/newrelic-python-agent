import pytest

import newrelic.api.application
from newrelic.api.web_transaction import _WSGIApplicationMiddleware

application = newrelic.api.application.application_instance()
html_response = ('<!DOCTYPE html><html><head>Some header</head>'
        '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
        '</body></html>').encode('utf-8')


@pytest.mark.parametrize('autorum_disabled', [True, False])
def test_content_length_not_inserted_when_autorum_disabled(autorum_disabled):
    # Content-Length headers should not be modified when HTML
    # insertion is enabled/disabled.
    environ = {
        'REQUEST_URI': '/browser_middleware',
        'newrelic.disable_browser_autorum': autorum_disabled,
    }
    transaction = newrelic.api.web_transaction.WebTransaction(
            application, environ)

    output = []
    status = []
    headers = []
    other_args = []

    def start_response(_status, _headers, *_other_args):
        status.append(_status)
        headers.append(_headers)
        other_args.append(_other_args)
        return output.append

    initial_headers = [
        ('Content-Type', 'text/html'),
    ]

    def simple_app(_environ, _start_response):
        _start_response(200, initial_headers)
        return [html_response]

    gen = _WSGIApplicationMiddleware(simple_app, environ,
            start_response, transaction)

    with transaction:

        for i, data in enumerate(gen):
            pass

    # i must == 0 at the end of iteration
    # since len([html_response]) is 1
    assert i == 0

    assert status == [200]
    assert headers == [initial_headers]


@pytest.mark.parametrize('autorum_disabled', [True, False])
def test_content_length_modified_when_autorum_disabled(autorum_disabled):
    # Content-Length headers should modified when autorum enabled
    environ = {
        'REQUEST_URI': '/browser_middleware',
        'newrelic.disable_browser_autorum': autorum_disabled,
    }
    transaction = newrelic.api.web_transaction.WebTransaction(
            application, environ)

    output = []
    status = []
    headers = []
    other_args = []

    def start_response(_status, _headers, *_other_args):
        status.append(_status)
        headers.append(sorted(_headers))
        other_args.append(_other_args)
        return output.append

    initial_headers = [
        ('Content-Length', str(len(html_response))),
        ('Content-Type', 'text/html'),
    ]

    def simple_app(_environ, _start_response):
        _start_response(200, initial_headers)
        return [html_response]

    gen = _WSGIApplicationMiddleware(simple_app, environ,
            start_response, transaction)

    with transaction:
        if not autorum_disabled:
            # Start response is not called yet since we now have to compute
            # the new Content-Length
            assert status == []
            assert headers == []

        for i, data in enumerate(gen):
            pass

    # i must == 0 at the end of iteration
    # since len([html_response]) is 1
    assert i == 0

    assert status == [200]

    if autorum_disabled:
        assert headers == [initial_headers]
    else:
        # Data is now modified for autorum insertion!
        assert data != html_response

        assert len(headers) == 1
        assert headers[0][1] == ('Content-Type', 'text/html')

        # Content-Length should now be modified!
        assert headers[0][0] == ('Content-Length', str(len(data)))
