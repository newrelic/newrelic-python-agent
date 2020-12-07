import pytest
import webtest

from flask import Flask

application = Flask(__name__)

@application.errorhandler(404)
def page_not_found(error):
    return 'This page does not exist', 404

_test_application = webtest.TestApp(application)
