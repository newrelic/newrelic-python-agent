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
from pathlib import Path

import pytest

from newrelic.core import agent


@pytest.mark.parametrize("content", [{}, {"opt": [1, 2, 3]}])
def test_check_environment_failing(tmp_path, content):
    tmp_path = Path(tmp_path)

    try:
        uwsgi_dir = tmp_path / "uwsgi"
        init_file = uwsgi_dir / "__init__.py"
        uwsgi_dir.mkdir(parents=True)
        with init_file.open("w") as f:
            f.writelines(f"{key} = {value}" for key, value in content.items())

        sys.path.insert(0, str(tmp_path))
        import uwsgi

        for key, value in content.items():
            assert getattr(uwsgi, key) == value

        agent.check_environment()
    finally:
        sys.path.remove(str(tmp_path))
        del sys.modules["uwsgi"]