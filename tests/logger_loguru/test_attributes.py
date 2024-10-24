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

from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_events import validate_log_events

from newrelic.api.background_task import background_task


@validate_log_events(
    [
        {  # Fixed attributes
            "message": "context_attrs: arg1",
            "context.file": f"(name='test_attributes.py', path='{str(__file__)}')",
            "context.function": "test_loguru_default_context_attributes",
            "context.extra.bound_attr": 1,
            "context.extra.contextual_attr": 2,
            "context.extra.global_extra": 3,
            "context.extra.kwarg_attr": 4,
            "context.patched_attr": 5,
            "context.module": "test_attributes",
            "context.name": "test_attributes",
        }
    ],
    required_attrs=[  # Variable attributes
        "context.elapsed",
        "context.line",
        "context.process",
        "context.thread",
    ],
)
@validate_log_event_count(1)
@background_task()
def test_loguru_default_context_attributes(logger):
    def _patcher(d):
        d["patched_attr"] = 5
        return d

    bound_logger = logger.bind(bound_attr=1)
    bound_logger = bound_logger.patch(_patcher)
    with bound_logger.contextualize(contextual_attr=2):
        bound_logger.error("context_attrs: {}", "arg1", kwarg_attr=4)


@validate_log_events([{"message": "exc_info"}], required_attrs=["context.exception"])
@validate_log_event_count(1)
@background_task()
def test_loguru_exception_context_attributes(logger):
    try:
        raise RuntimeError("Oops")
    except Exception:
        logger.opt(exception=True).error("exc_info")


@validate_log_events([{"context.extra.attr": 1}])
@validate_log_event_count(1)
@background_task()
def test_loguru_attributes_only(logger):
    logger.error("", attr=1)
