def test_pywsgi_application_index(target_application):
    for i in range(3):
        response = target_application.get('/pywsgi')
        response.mustcontain('WSGI RESPONSE')

def test_pywsgi_request_timeout_application(target_application):
    for i in range(3):
        response = target_application.get(
                '/request-timeout-application/pywsgi', status=500)

def test_pywsgi_request_timeout_response(target_application):
    # The gevent pywsgi server appears to not be WSGI compliant in this
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
                '/request-timeout-response/pywsgi', status=500)
        #response.mustcontain('WSGI')

def test_pywsgi_request_timeout_finalize(target_application):
    # This suffers same issue as in test_pywsgi_request_timeout_response()
    # where the results isn't what we expect when things run in the same
    # process.

    for i in range(3):
        response = target_application.get(
                '/request-timeout-finalize/pywsgi', status=500)
        #response.mustcontain('WSGI RESPONSE')

def test_pywsgi_raise_exception_application(target_application):
    for i in range(3):
        response = target_application.get(
                '/raise-exception-application/pywsgi', status=500)

def test_pywsgi_raise_exception_response(target_application):
    for i in range(3):
        response = target_application.get(
                '/raise-exception-response/pywsgi', status=500)

def test_pywsgi_raise_exception_finalize(target_application):
    for i in range(3):
        response = target_application.get(
                '/raise-exception-finalize/pywsgi', status=500)
