import sys

import newrelic.api.import_hook as import_hook
import newrelic.packages.six as six
import pytest

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
