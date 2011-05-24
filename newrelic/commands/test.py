def run(args):
    import time, os
    import newrelic.agent

    settings = newrelic.agent.settings()
    settings.app_name = 'Python Agent Test'
    settings.log_file = '/tmp/python-agent-test.log'
    settings.log_level = newrelic.agent.LOG_VERBOSEDEBUG
    settings.transaction_tracer.transaction_threshold = 0

    try:
        os.unlink(settings.log_file)
    except:
        pass

    @newrelic.agent.function_trace()
    def _function1():
        time.sleep(0.1)

    @newrelic.agent.function_trace()
    def _function2():
        for i in range(10):
            _function1()

    @newrelic.agent.error_trace()
    @newrelic.agent.function_trace()
    def _function3():
        raise RuntimeError('error')
     
    @newrelic.agent.wsgi_application()
    def _application(environ, start_response):
        status = '200 OK'
        output = 'Hello World!'

        response_headers = [('Content-type', 'text/plain'),
                            ('Content-Length', str(len(output)))]
        start_response(status, response_headers)

        for i in range(10):
            _function1()

        _function2()

        try:
            _function3()
        except:
            pass

        return [output]

    @newrelic.agent.background_task()
    def _background_task():
        for i in range(10):
            _function1()

        _function2()

        try:
            _function3()
        except:
            pass

    def _start_response(*args):
        pass


    print
    print 'Running Python agent test.'
    print
    print 'Look for data in the New Relic UI under the application:'
    print
    print '  %s' % settings.app_name
    print
    print 'If data is not getting through to the UI after 5 minutes'
    print 'then check the log file:'
    print
    print '  %s' % settings.log_file
    print
    print 'for debugging information. Supply the log file to New Relic'
    print 'support if requesting help with resolving any issues with'
    print 'the test not reporting data to the New Relic UI.'
    print

    _environ = { 'SCRIPT_NAME': '', 'PATH_INFO': '/test' }

    iterable = _application(_environ, _start_response)
    iterable.close()

    _background_task()
