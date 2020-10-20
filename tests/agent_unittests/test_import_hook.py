from pytest import raises


def test_import_hook_finder():
    """
    This asserts the behavior of ImportHookFinder.find_module. It behaves
    differently depending on whether or not the module it is looking for
    exists, has been registered with an import hook, and across different
    python versions.
    """
    from newrelic.api.import_hook import ImportHookFinder, register_import_hook
    import sys

    PY2 = sys.version_info[0] == 2

    finder = ImportHookFinder()

    # a dummy hook just to be able to register hooks for modules
    def hook(*args, **kwargs):
        pass

    # Finding a module that does not exist and is not registered returns None.
    module = finder.find_module('some_module_that_does_not_exist')
    assert module is None

    # Finding a module that does not exist and is registered behaves
    # differently on python 2 vs python 3.
    register_import_hook('some_module_that_does_not_exist', hook)
    if PY2:
        with raises(ImportError):
            module = finder.find_module('some_module_that_does_not_exist')
    else:
        module = finder.find_module('some_module_that_does_not_exist')
        assert module is None

    # Finding a module that exists, but is not registered returns None.
    module = finder.find_module('newrelic')
    assert module is None

    # Finding a module that exists, and is registered, finds that module.
    register_import_hook('newrelic', hook)
    module = finder.find_module('newrelic')
    assert module is not None
