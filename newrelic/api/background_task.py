import os

import _newrelic

import newrelic.api.object_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

BackgroundTask = _newrelic.BackgroundTask
BackgroundTaskWrapper = _newrelic.BackgroundTaskWrapper

# TODO BackgroundTaskWrapper will be like FunctionTraceWrapper
# with exception that needs to flag an outer web transaction as
# a background task. Need to consider nesting in general.

def background_task(application=None, name=None, scope=None):
    def decorator(wrapped):
        return BackgroundTaskWrapper(wrapped, application, name, scope)
    return decorator

def wrap_background_task(module, object_path, application=None, name=None,
                         scope=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            BackgroundTaskWrapper, (application, name, scope))

if not _agent_mode in ('ungud', 'julunggul'):
    background_task = _newrelic.background_task
    wrap_background_task = _newrelic.wrap_background_task
