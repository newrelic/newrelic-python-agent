from newrelic.core.environment import environment_settings


def test_plugin_list():
    # Let's pretend we fired an import hook
    import newrelic.hooks.adapter_gunicorn

    environment_info = environment_settings()

    for key, plugin_list in environment_info:
        if key == 'Plugin List':
            break
    else:
        assert False, "'Plugin List' not found"

    # Check that bogus plugins don't get reported
    assert 'newrelic.hooks.newrelic' not in plugin_list
