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

import sys

def test_no_harm(caplog):
#     from newrelic.api.import_hook import _uninstrumented_modules
    # import importlib
    import logging
    # importlib.invalidate_caches()
    # importlib.reload(logging)

    _logger = logging.getLogger("my_app")
    _logger.addHandler(logging.StreamHandler(stream=sys.stdout))

    # assert not _uninstrumented_modules

    with caplog.at_level(logging.INFO):
        _logger.info("hi")

    assert len(caplog.records) == 1
    assert caplog.messages == ["hi"]
    caplog.clear()

    breakpoint()

    return


import logging
import sys

#Creating and Configuring Logger

Log_Format = "%(levelname)s %(asctime)s - %(message)s"

logging.basicConfig(filename = "logfile.log",
                    stream = sys.stdout, 
                    filemode = "w",
                    format = Log_Format, 
                    level = logging.ERROR)

logger = logging.getLogger()

#Testing our Logger

logger.error("Our First Error Message")
