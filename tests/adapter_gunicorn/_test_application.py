from __future__ import unicode_literals

import gunicorn.app.base

from gunicorn.six import iteritems


def handler_app(environ, start_response):
    response_body = b'Hello WOrld'
    status = '200 OK'

    response_headers = [
        ('Content-Type', 'text/plain'),
    ]

    start_response(status, response_headers)

    return [response_body]


class StandaloneApplication(gunicorn.app.base.BaseApplication):

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super(StandaloneApplication, self).__init__()

    def load_config(self):
        config = dict([(key, value) for key, value in iteritems(self.options)
                if key in self.cfg.settings and value is not None])
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def get_application():
    options = {'bind': '%s:%s' % ('127.0.0.1', '8080'),
            'workers': 1}
    return StandaloneApplication(handler_app, options)

