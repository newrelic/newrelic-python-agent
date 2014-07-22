import webtest

from bottle import __version__ as version
from bottle import route, error, default_app, HTTPError

version = [int(x) for x in version.split('-')[0].split('.')]

if len(version) == 2:
    version.append(0)

version = tuple(version)

@route('/index')
def index_page():
    return 'INDEX RESPONSE'

@route('/error')
def error_page():
    raise RuntimeError('RUNTIME ERROR')

@error(404)
def error404_page(error):
    return 'NOT FOUND'

if version >= (0, 9, 0):
    from bottle import auth_basic

    def auth_check(username, password):
        return username == 'user' and password == 'password'

    @route('/auth')
    @auth_basic(auth_check)
    def auth_basic_page():
        return 'AUTH OKAY'

    def plugin_error(callback):
        def wrapper(*args, **kwargs):
            raise HTTPError(403, 'Go Away')
        return wrapper

    @route('/plugin_error', apply=[plugin_error], skip=['json'])
    def plugin_error_page():
        return 'PLUGIN RESPONSE'

application = default_app()
target_application = webtest.TestApp(application)
