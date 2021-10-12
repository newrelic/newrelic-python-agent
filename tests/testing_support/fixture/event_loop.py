import pytest

from newrelic.packages import six

# Guard against Python 2 crashes
if six.PY2:
    event_loop = None
else:

    @pytest.fixture(scope="session")
    def event_loop():
        from asyncio import new_event_loop, set_event_loop

        loop = new_event_loop()
        set_event_loop(loop)
        yield loop
