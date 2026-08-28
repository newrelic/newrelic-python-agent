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

from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args
from newrelic.api.time_trace import current_trace
from newrelic.core.config import global_settings

_logger = logging.getLogger(__name__)
OBSERVABILITY_PLUGIN_REGISTERED = False

def _create_NewRelicHook():
    from ldclient.hook import Hook, Metadata

    class NewRelicHook(Hook):
        @property
        def metadata(self) -> Metadata:
            return Metadata(name="newrelic-hook")

        def before_evaluation(self, series_context, data):
            return data

        def after_evaluation(self, series_context, data, detail):
            try:
                attrs = {
                  'feature_flag.key': series_context.key,
                  'feature_flag.provider.name': 'LaunchDarkly',
                  'feature_flag.context.id': series_context.context.key,
                }
                if isinstance(detail.variation_index, int):
                    attrs['feature_flag.result.variationIndex'] = detail.variation_index
                if hasattr(detail, "reason") and detail.reason.get("kind"):
                    attrs['feature_flag.result.reason.kind'] = detail.reason["kind"]
                if hasattr(detail, "reason") and detail.reason.get("in_experiment"):
                    attrs['feature_flag.result.reason.inExperiment'] = True
                if getattr(detail, "value", None):
                    attrs['feature_flag.result.value'] = detail.value
                trace = current_trace()
                if not trace:
                    raise Exception("No active trace. Unable to attach Darkly data to span.")
                for key, value in attrs.items():
                    trace.add_custom_attribute(key, value)
            except Exception as e:
                _logger.exception("[newrelic-hook] failed to enrich span")
            return data
    return NewRelicHook()


def _nr_wrapper_Config___init__(wrapped, instance, args, kwargs):
    settings = global_settings()
    # Only add the hook if the integration setting is enabled.
    if settings.launch_darkly_integration.enabled:
        try:
            bound_args = bind_args(wrapped, args, kwargs)

            nr_hook = _create_NewRelicHook()
            if bound_args["hooks"] is None:
                bound_args["hooks"] = [nr_hook]
            else:
                bound_args["hooks"].append(nr_hook)
            return wrapped(**bound_args)
        except Exception:
            _logger.exception("Failed to add New Relic hook to Launch Darkly hooks list. Please report this issue to New Relic Support.")
    return wrapped(instance, *args, **kwargs)


def _nr_wrapper_LDClient___init__(wrapped, instance, args, kwargs):
    return_val =  wrapped(*args, **kwargs)

    global OBSERVABILITY_PLUGIN_REGISTERED
    if not OBSERVABILITY_PLUGIN_REGISTERED:
        _logger.warning("ObservabilityPlugin must be registered with Launch Darkly ldclient in order to successfully initialize the Launch Darkly-New Relic integration.")
    return return_val


def _nr_wrapper_ObservabilityPlugin_register(wrapped, instance, args, kwargs):
    global OBSERVABILITY_PLUGIN_REGISTERED
    OBSERVABILITY_PLUGIN_REGISTERED = True

    return wrapped(*args, **kwargs)


def instrument_ldclient_config(module):
    if hasattr(module, "Config"):
        wrap_function_wrapper(module, "Config.__init__", _nr_wrapper_Config___init__)


def instrument_ldclient_client(module):
    if hasattr(module, "LDClient"):
        wrap_function_wrapper(module, "LDClient.__init__", _nr_wrapper_LDClient___init__)


def instrument_ldobserve___init__(module):
    if hasattr(module, "ObservabilityPlugin"):
        wrap_function_wrapper(module, "ObservabilityPlugin.register", _nr_wrapper_ObservabilityPlugin_register)
