import webtest

import flask
import flask.views

app = flask.Flask(__name__)

class TestView(flask.views.View):
    def dispatch_request(self):
        return 'VIEW RESPONSE'

class TestMethodView(flask.views.MethodView):
    def get(self):
        return 'METHODVIEW GET RESPONSE'

    def post(self):
        return 'METHODVIEW POST RESPONSE'

app.add_url_rule('/view',
        view_func=TestView.as_view('test_view'))
app.add_url_rule('/methodview',
        view_func=TestMethodView.as_view('test_methodview'))

_test_application = webtest.TestApp(app)
