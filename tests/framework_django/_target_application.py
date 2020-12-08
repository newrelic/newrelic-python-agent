import webtest

from wsgi import application


_target_application = webtest.TestApp(application)
