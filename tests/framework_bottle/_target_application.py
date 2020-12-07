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

@route('/html_insertion')
def index_page():
    return ('<!DOCTYPE html><html><head>Some header</head>'
            '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
            '</body></html>')

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
            raise HTTPError(403, 'Forbidden')
        return wrapper

    @route('/plugin_error', apply=[plugin_error], skip=['json'])
    def plugin_error_page():
        return 'PLUGIN RESPONSE'

application = default_app()
target_application = webtest.TestApp(application)
