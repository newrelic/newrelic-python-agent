import webtest

target_application = webtest.TestApp('http://localhost:8001')

def test_wsgi_application_index():
    for i in range(3):
        response = target_application.get('/wsgi')
        response.mustcontain('WSGI RESPONSE')

def test_wsgi_request_timeout_application():
    for i in range(3):
        response = target_application.get(
                '/request-timeout-application/wsgi', status=500)

def test_wsgi_request_timeout_response():
    # The gevent wsgi server appears to not be WSGI compliant in this
    # test. The expectation in yielding a string and then causing a
    # timeout would be that the HTTP 200 OK response and initial text
    # would have already been sent. As such we should always see a HTTP
    # 200 OK response and partial content. For some reason when the test
    # client is in the same process as the server this doesn't happen.
    # If one uses an extenal browser against the pywsgi server it works
    # as expected. It may all be done to some issue with how coroutines
    # are schedule when done within the one process.

    for i in range(3):
        response = target_application.get(
                '/request-timeout-response/wsgi', status=500)
        #response.mustcontain('WSGI')

def test_wsgi_request_timeout_finalize():
    # This suffers same issue as in test_wsgi_request_timeout_response()
    # where the results isn't what we expect when things run in the same
    # process.

    for i in range(3):
        response = target_application.get(
                '/request-timeout-finalize/wsgi', status=500)
        #response.mustcontain('WSGI RESPONSE')

def test_wsgi_raise_exception_application():
    for i in range(3):
        response = target_application.get(
                '/raise-exception-application/wsgi', status=500)

def test_wsgi_raise_exception_response():
    for i in range(3):
        response = target_application.get(
                '/raise-exception-response/wsgi', status=500)

def test_wsgi_raise_exception_finalize():
    for i in range(3):
        response = target_application.get(
                '/raise-exception-finalize/wsgi', status=500)
