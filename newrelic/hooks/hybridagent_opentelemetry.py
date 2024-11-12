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

from newrelic.api.transaction import current_transaction, record_custom_metric
from newrelic.common.object_wrapper import wrap_function_wrapper


# ----------------------------------------------
# Custom OTel Metrics
# ----------------------------------------------
class HistogramDict(dict):
    def __init__(self, value):
        self.value = value
        self.total = 0
        self.count = 0
        self.min = value
        self.max = value
        self.sum_of_squares = 0

        self.record_value()

    def __call__(self, value):
        self.value = value
        self.record_value()

    def set_total(self):
        self.total += self.value

    def set_count(self):
        self.count += 1

    def set_min(self):
        self.min = min(self.min, self.value)

    def set_max(self):
        self.max = max(self.max, self.value)

    def set_sum_of_squares(self):
        self.sum_of_squares += self.value**2

    def record_value(self):
        self.set_total()
        self.set_count()
        self.set_min()
        self.set_max()
        self.set_sum_of_squares()

        self["total"] = self.total
        self["count"] = self.count
        self["min"] = self.min
        self["max"] = self.max
        self["sum_of_squares"] = self.sum_of_squares

        return self


def wrap_meter(wrapped, instance, args, kwargs):
    def bind_meter(name, version=None, schema_url=None, *args, **kwargs):
        return name, version, schema_url  # attributes

    name, version, schema_url = bind_meter(*args, **kwargs)

    if schema_url:
        record_custom_metric(f"OtelMeter/{name}/SchemaURL/{schema_url}", 1)
    if version:
        record_custom_metric(f"OtelMeter/{name}/{version}", 1)
    else:
        record_custom_metric(f"OtelMeter/{name}", 1)

    return wrapped(*args, **kwargs)


def wrap_add(wrapped, instance, args, kwargs):
    def bind_add(amount, *args, **kwargs):
        return amount  # , attributes, context

    amount = bind_add(*args, **kwargs)
    meter_name = instance.instrumentation_scope.name
    counter_name = instance.name

    record_custom_metric(f"OtelMeter/{meter_name}/{counter_name}", {"count": amount})

    return wrapped(*args, **kwargs)


def wrap_record(wrapped, instance, args, kwargs):
    def bind_record(amount, *args, **kwargs):
        return amount  # attributes, context

    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    amount = bind_record(*args, **kwargs)
    meter_name = instance.instrumentation_scope.name
    histogram_name = instance.name

    meter_name = instance.instrumentation_scope.name
    histogram_name = instance.name
    histogram_reference = f"OtelMeter/{meter_name}/{histogram_name}"

    if transaction._histogram and histogram_reference in transaction._histogram:
        # We are adding to the existing histogram
        transaction._histogram[histogram_reference](amount)
    else:
        # Creating a new histogram instance
        transaction._histogram[histogram_reference] = HistogramDict(amount)

    return wrapped(*args, **kwargs)


def _instrument_observable_methods(module, method_name):
    def wrap_observable_method(wrapped, instance, args, kwargs):
        def bind_func(name, callbacks, unit=None, *args, **kwargs):
            return name, callbacks, unit

        method_name, callbacks, unit = bind_func(*args, **kwargs)
        meter_name = instance._instrumentation_scope.name

        for callback in callbacks:
            for observation in callback():
                metric_value = (
                    f"OtelMeter/{meter_name}/{method_name}"
                    if not unit
                    else f"OtelMeter/{meter_name}/{method_name}/{unit}"
                )
                if method_name.endswith("gauge"):
                    record_custom_metric(metric_value, observation.value)
                else:
                    record_custom_metric(metric_value, {"count": observation.value})

        return wrapped(*args, **kwargs)

    wrap_function_wrapper(module, f"Meter.{method_name}", wrap_observable_method)


def instrument_observable_methods(module, observable_method_functions):
    for method_name in observable_method_functions:
        _instrument_observable_methods(module, method_name)


def instrument_meter(module):
    if hasattr(module, "MeterProvider"):
        wrap_function_wrapper(module, "MeterProvider.get_meter", wrap_meter)

    if hasattr(module, "Counter"):
        wrap_function_wrapper(module, "Counter.add", wrap_add)
    if hasattr(module, "UpDownCounter"):
        wrap_function_wrapper(module, "UpDownCounter.add", wrap_add)

    if hasattr(module, "Histogram"):
        wrap_function_wrapper(module, "Histogram.record", wrap_record)

    if hasattr(module, "Meter"):
        observable_method_functions = (
            "create_observable_gauge",
            "create_observable_counter",
            "create_observable_up_down_counter",
        )
        instrument_observable_methods(module, observable_method_functions)
