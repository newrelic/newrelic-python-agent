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

import json

from newrelic.common.encoding_utils import deobfuscate, json_decode
from newrelic.common.object_wrapper import transient_function_wrapper


def validate_browser_attributes(required_params=None, forgone_params=None):
    required_params = required_params or {}
    forgone_params = forgone_params or {}

    @transient_function_wrapper("newrelic.api.web_transaction", "WSGIWebTransaction.browser_timing_footer")
    def _validate_browser_attributes(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise

        # pick out attributes from footer string_types

        footer_data = result.split("NREUM.info=")[1]
        footer_data = footer_data.split("</script>")[0]
        footer_data = json.loads(footer_data)

        if "intrinsic" in required_params:
            for attr in required_params["intrinsic"]:
                assert attr in footer_data

        if "atts" in footer_data:
            obfuscation_key = instance._settings.license_key[:13]
            attributes = json_decode(deobfuscate(footer_data["atts"], obfuscation_key))
        else:

            # if there are no user or agent attributes, there will be no dict
            # for them in the browser data

            attributes = None

        if "user" in required_params:
            for attr in required_params["user"]:
                assert attr in attributes["u"]

        if "agent" in required_params:
            for attr in required_params["agent"]:
                assert attr in attributes["a"]

        if "user" in forgone_params:
            if attributes:
                if "u" in attributes:
                    for attr in forgone_params["user"]:
                        assert attr not in attributes["u"]

        if "agent" in forgone_params:
            if attributes:
                if "a" in attributes:
                    for attr in forgone_params["agent"]:
                        assert attr not in attributes["a"]

        return result

    return _validate_browser_attributes
