import webtest

import tornado.web
import tornado.wsgi

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("MAIN RESPONSE")

application = tornado.wsgi.WSGIApplication([
    (r"/main", MainHandler),
])

# TODO This shouldn't be required and should be wrapped automatically.
import newrelic.agent
application = newrelic.agent.WSGIApplicationWrapper(application)

test_application = webtest.TestApp(application)

def test_wsgi_application_main():
    response = test_application.get('/main')
    response.mustcontain('MAIN RESPONSE')
