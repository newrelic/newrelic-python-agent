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

from threading import Thread
from time import sleep

from testing_support.sample_applications import (
    raise_exception_application,
    raise_exception_finalize,
    raise_exception_response,
    simple_app_raw,
)
from testing_support.util import get_open_port


def sample_application(environ, start_response):
    path_info = environ.get("PATH_INFO")

    if path_info.startswith("/raise-exception-application"):
        return raise_exception_application(environ, start_response)
    elif path_info.startswith("/raise-exception-response"):
        return raise_exception_response(environ, start_response)
    elif path_info.startswith("/raise-exception-finalize"):
        return raise_exception_finalize(environ, start_response)

    return simple_app_raw(environ, start_response)


def setup_application():
    port = get_open_port()

    def run_wsgi():
        from waitress import serve

        serve(sample_application, host="127.0.0.1", port=port)

    wsgi_thread = Thread(target=run_wsgi)
    wsgi_thread.daemon = True
    wsgi_thread.start()

    sleep(1)

    return port
