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
import logging
from functools import lru_cache
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

from newrelic.api.time_trace import current_trace
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args
from newrelic.core.config import global_settings

_logger = logging.getLogger(__name__)
OBSERVABILITY_PLUGIN_REGISTERED = False
OBSERVABILITY_PLUGIN_WARNING = "ObservabilityPlugin must be registered with Launch Darkly ldclient in order to successfully initialize the Launch Darkly-New Relic integration."


NewRelicHook = None


def _NewRelicHook(*args, **kwargs):
    """
    Create and return a new instance of NewRelicHook.
    The first time this function is called, the NewRelicHook class is defined.
    On subsequent runs, the class is just instantiated.
    """
    global NewRelicHook
    if NewRelicHook is not None:
        return NewRelicHook(*args, **kwargs)

    from ldclient.config import DEFAULT_BASE_URI
    from ldclient.hook import Hook, Metadata

    class NewRelicHook(Hook):
        def __init__(self, *args, base_uri=DEFAULT_BASE_URI, **kwargs):
            self._base_uri = (base_uri or DEFAULT_BASE_URI).rstrip("/")
            super().__init__(*args, **kwargs)

        @staticmethod
        @lru_cache(maxsize=1024)
        def _flag_url(base_uri, flag_key, environment_id):
            """Build a Launch Darkly flag deep link with every component percent-encoded."""
            base = urlsplit(base_uri)
            path = f"{base.path}/goto/flags/{quote(flag_key, safe='')}"
            query = urlencode({"envId": environment_id})
            return urlunsplit((base.scheme, base.netloc, path, query, ""))

        @property
        def metadata(self) -> Metadata:
            return Metadata(name="newrelic-hook")

        def before_evaluation(self, series_context, data):
            return data

        def after_evaluation(self, series_context, data, detail):
            trace = current_trace()
            if not trace:
                return data

            try:
                attrs = {
                    "feature_flag.key": series_context.key,
                    "feature_flag.provider.name": "LaunchDarkly",
                    "feature_flag.context.id": series_context.context.key,
                }
                if isinstance(detail.variation_index, int):
                    attrs["feature_flag.result.variationIndex"] = detail.variation_index
                reason = getattr(detail, "reason", None) or {}
                if reason.get("kind"):
                    attrs["feature_flag.result.reason.kind"] = reason["kind"]
                if reason.get("inExperiment"):
                    attrs["feature_flag.result.reason.inExperiment"] = True
                # Falsy values such as False or 0 are valid flag results.
                if getattr(detail, "value", None) is not None:
                    attrs["feature_flag.result.value"] = detail.value

                environment_id = getattr(series_context, "environment_id", None)
                if environment_id and isinstance(environment_id, str):  # if non-empty string
                    attrs["feature_flag.set.id"] = environment_id
                    # Direct linking is only possible if we have the environment_id attribute available
                    attrs["feature_flag.url.full"] = self._flag_url(self._base_uri, series_context.key, environment_id)

                for key, value in attrs.items():
                    trace.add_custom_attribute(key, value)
            except Exception:
                _logger.exception("[newrelic-hook] failed to enrich span")
            return data

    return NewRelicHook(*args, **kwargs)


def wrap_Config_init(wrapped, instance, args, kwargs):
    settings = global_settings()
    # Only add the hook if the integration setting is enabled.
    if not settings.launch_darkly_integration.enabled:
        return wrapped(*args, **kwargs)

    try:
        bound_args = bind_args(wrapped, args, kwargs)
    except Exception:
        # Invalid arguments, let the original function raise the error to the user.
        return wrapped(*args, **kwargs)

    try:
        nr_hook = _NewRelicHook(base_uri=bound_args.get("base_uri", None))
        hooks = bound_args["hooks"] or []
        # Filter out any existing NR hooks that may be out of date.
        # Ensure supplied iterable is a list, which LD will coerce to anyway.
        hooks = [hook for hook in hooks if not isinstance(hook, NewRelicHook)]
        hooks.append(nr_hook)
    except Exception:
        _logger.exception(
            "Failed to add New Relic hook to Launch Darkly hooks list. Please report this issue to New Relic Support."
        )
        return wrapped(*args, **kwargs)

    # Call outside of the try block so errors raised by Config are not mistaken for instrumentation errors.
    bound_args["hooks"] = hooks
    return wrapped(**bound_args)


def wrap_LDClient_init(wrapped, instance, args, kwargs):
    return_val = wrapped(*args, **kwargs)
    settings = global_settings()

    # Only emit a warning if the integration setting is enabled.
    if not OBSERVABILITY_PLUGIN_REGISTERED and settings.launch_darkly_integration.enabled:
        _logger.warning(OBSERVABILITY_PLUGIN_WARNING)
    return return_val


def wrap_ObservabilityPlugin_register(wrapped, instance, args, kwargs):
    global OBSERVABILITY_PLUGIN_REGISTERED
    OBSERVABILITY_PLUGIN_REGISTERED = True

    return wrapped(*args, **kwargs)


def instrument_ldclient_config(module):
    if hasattr(module, "Config"):
        wrap_function_wrapper(module, "Config.__init__", wrap_Config_init)


def instrument_ldclient_client(module):
    if hasattr(module, "LDClient"):
        wrap_function_wrapper(module, "LDClient.__init__", wrap_LDClient_init)


def instrument_ldobserve(module):
    if hasattr(module, "ObservabilityPlugin"):
        wrap_function_wrapper(module, "ObservabilityPlugin.register", wrap_ObservabilityPlugin_register)
