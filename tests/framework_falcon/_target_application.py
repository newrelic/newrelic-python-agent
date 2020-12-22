# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import falcon
import webtest


try:
    from falcon import HTTPRouteNotFound
    NOT_FOUND_ERROR_NAME = 'falcon.errors:HTTPRouteNotFound'
except ImportError:
    NOT_FOUND_ERROR_NAME = 'falcon.errors:HTTPNotFound'


def _bind_response(*args, **kwargs):
    args = list(args)
    args.extend(kwargs.values())
    for arg in args:
        if hasattr(arg, 'status'):
            return arg


class BadGetRequest(ValueError):
    pass


class BadPutRequest(ValueError):
    pass


class Index(object):
    def on_get(self, req, resp):
        """Handles GET requests"""
        resp.content_type = 'application/json'
        resp.data = b'{"status": "ok"}'


class BadResponse(object):
    def on_get(self, req, resp):
        raise BadGetRequest()

    def on_put(self, req, resp):
        raise BadPutRequest()


try:
    application = falcon.App()
    name_prefix = 'falcon.app:App'
except AttributeError:
    application = falcon.API()
    name_prefix = 'falcon.api:API'


def bad_error_handler(*args, **kwargs):
    resp = _bind_response(*args, **kwargs)

    # This endpoint is explicitly not doing the correct thing. Status is
    # expected to be a type str with a status code + explanation. The intent
    # here is to test what happens if we don't parse the response code
    # correctly.
    resp.status = 200


application.add_route('/', Index())
application.add_route('/bad_response', BadResponse())
application.add_error_handler(BadGetRequest, bad_error_handler)

_target_application = webtest.TestApp(application)

# Put exception class here for convenience
_target_application.BadPutRequest = BadPutRequest

# Put names here for convenience
_target_application.name_prefix = name_prefix
_target_application.not_found_error = NOT_FOUND_ERROR_NAME
