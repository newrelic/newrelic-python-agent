import webtest

from flask import Flask
from flask_compress import Compress

application = Flask(__name__)

compress = Compress()
compress.init_app(application)

@application.route('/compress')
def index_page():
    return '<body>' + 500*'X' + '</body>'

_test_application = webtest.TestApp(application)
