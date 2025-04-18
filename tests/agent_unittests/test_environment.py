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

import sys

import pytest

from newrelic.core.config import global_settings
from newrelic.core.environment import environment_settings, plugins

settings = global_settings()


def module(version):
    class Module:
        pass

    if version:
        Module.__version__ = version

    return Module


def test_plugin_list():
    # Let's pretend we fired an import hook
    import pytest

    for name, version, _ in plugins():
        if name == "newrelic.hooks.newrelic":
            raise AssertionError("Bogus plugin found")
        if name == "pytest":
            # Check that plugin that should get reported has version info.
            assert version == pytest.__version__


class NoIteratorDict:
    def __init__(self, d):
        self.d = d

    def copy(self):
        return self.d.copy()

    def get(self, *args, **kwargs):
        return self.d.get(*args, **kwargs)

    def __getitem__(self, *args, **kwargs):
        return self.d.__getitem__(*args, **kwargs)

    def __contains__(self, *args, **kwargs):
        return self.d.__contains__(*args, **kwargs)


@pytest.mark.parametrize(
    "loaded_modules,dispatcher,dispatcher_version,worker_version",
    (
        ({"uvicorn": module("4.5.6")}, "uvicorn", "4.5.6", None),
        (
            {"gunicorn": module("1.2.3"), "uvicorn": module("4.5.6"), "uvicorn.workers": object()},
            "gunicorn (uvicorn)",
            "1.2.3",
            "4.5.6",
        ),
        # New replacement module uvicorn_worker should function the same
        (
            {"gunicorn": module("1.2.3"), "uvicorn": module("4.5.6"), "uvicorn_worker": object()},
            "gunicorn (uvicorn)",
            "1.2.3",
            "4.5.6",
        ),
        ({"uvicorn": object()}, "uvicorn", None, None),
        (
            {"gunicorn": object(), "uvicorn": module("4.5.6"), "uvicorn.workers": object()},
            "gunicorn (uvicorn)",
            None,
            "4.5.6",
        ),
        (
            {"gunicorn": module("1.2.3"), "uvicorn": None, "uvicorn.workers": object()},
            "gunicorn (uvicorn)",
            "1.2.3",
            None,
        ),
        ({"gunicorn": object(), "uvicorn": object(), "uvicorn.workers": object()}, "gunicorn (uvicorn)", None, None),
    ),
)
def test_uvicorn_dispatcher(monkeypatch, loaded_modules, dispatcher, dispatcher_version, worker_version):
    # Let's pretend we load some modules
    for name, module in loaded_modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    environment_info = environment_settings()

    actual_dispatcher = None
    actual_dispatcher_version = None
    actual_worker_version = None
    for key, value in environment_info:
        if key == "Dispatcher":
            assert actual_dispatcher is None
            actual_dispatcher = value
        elif key == "Dispatcher Version":
            assert actual_dispatcher_version is None
            actual_dispatcher_version = value
        elif key == "Worker Version":
            assert actual_worker_version is None
            actual_worker_version = value

    assert actual_dispatcher == dispatcher
    assert actual_dispatcher_version == dispatcher_version
    assert actual_worker_version == worker_version
