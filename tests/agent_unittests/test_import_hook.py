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

import newrelic.api.import_hook as import_hook
import newrelic.packages.six as six
import pytest

from newrelic.config import _module_function_glob

# a dummy hook just to be able to register hooks for modules
def hook(*args, **kwargs):
    pass


def test_import_hook_finder(monkeypatch):
    """
    This asserts the behavior of ImportHookFinder.find_module. It behaves
    differently depending on whether or not the module it is looking for
    exists, has been registered with an import hook, and across different
    python versions.
    """
    finder = import_hook.ImportHookFinder()

    # Override the registered import hooks for the scope of this test
    registered_hooks = {
        "registered_but_does_not_exist": hook,
        "newrelic.api": hook,
    }
    monkeypatch.setattr(import_hook, "_import_hooks", registered_hooks)

    # Finding a module that does not exist and is not registered returns None.
    module = finder.find_module("module_does_not_exist")
    assert module is None

    # Finding a module that does not exist and is registered behaves
    # differently on python 2 vs python 3.
    if six.PY2:
        with pytest.raises(ImportError):
            module = finder.find_module("registered_but_does_not_exist")
    else:
        module = finder.find_module("registered_but_does_not_exist")
        assert module is None

    # Finding a module that exists, but is not registered returns None.
    module = finder.find_module("newrelic")
    assert module is None

    # Finding a module that exists, and is registered, finds that module.
    module = finder.find_module("newrelic.api")
    assert module is not None


@pytest.mark.parametrize("input,expected", [
    ("*", {"run", "A.run", "B.run"}),
    ("NotFound.*", set()),
    ("r*", {"run"}),
    ("*.run", {"A.run", "B.run"}),
    ("A.*", {"A.run"}),
    ("[A,B].run", {"A.run", "B.run"}),
    ("B.r?n", {"B.run"}),
    ("*.RUN", set()),  # Check for case insensitivity issues
])
def test_module_function_globbing(input, expected):
    """This asserts the behavior of filename style globbing on modules."""
    import _test_import_hook as module
    
    result = set(_module_function_glob(module, input))
    assert result == expected, (result, expected)
