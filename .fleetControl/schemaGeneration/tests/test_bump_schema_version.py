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

"""Unit tests for bump-schema-version.py.

Covers the historical-ref reading helpers (parse_schema_path,
historical_schema_path_in_repo) and the main flow's bootstrap branches
(via mocked git_show). End-to-end git invocation is left untested because
mocking subprocess at that level provides no additional confidence and
the real workflow exercises it.
"""

import importlib.util
import io
import json
import sys
import textwrap
import unittest
from pathlib import Path
from unittest import mock

# bump-schema-version.py uses a hyphenated filename so we load it via importlib.
_SCRIPT = Path(__file__).resolve().parent.parent / "bump-schema-version.py"
_spec = importlib.util.spec_from_file_location("bump_schema_version", _SCRIPT)
bump_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bump_mod)


# ---------------------------------------------------------------------------
# parse_schema_path
# ---------------------------------------------------------------------------


class ParseSchemaPathTests(unittest.TestCase):
    def test_finds_schema_line(self):
        text = textwrap.dedent("""\
            configurationDefinitions:
              - platform: KUBERNETESCLUSTER
                schema: ./schemas/config.json
                format: ini
            """)
        self.assertEqual(bump_mod.parse_schema_path(text), "./schemas/config.json")

    def test_no_schema_line_returns_none(self):
        text = "configurationDefinitions:\n  - platform: foo\n"
        self.assertIsNone(bump_mod.parse_schema_path(text))

    def test_handles_indentation(self):
        # The regex must be tolerant of varying leading whitespace.
        text = "    schema: my/schema.json\n"
        self.assertEqual(bump_mod.parse_schema_path(text), "my/schema.json")


# ---------------------------------------------------------------------------
# historical_schema_path_in_repo
# ---------------------------------------------------------------------------


class HistoricalSchemaPathInRepoTests(unittest.TestCase):
    def test_strips_leading_dot_slash(self):
        self.assertEqual(
            bump_mod.historical_schema_path_in_repo("./schemas/config.json"), ".fleetControl/schemas/config.json"
        )

    def test_no_dot_slash(self):
        self.assertEqual(
            bump_mod.historical_schema_path_in_repo("schemas/config.json"), ".fleetControl/schemas/config.json"
        )


# ---------------------------------------------------------------------------
# main() bootstrap and happy-path branches.
#
# We mock git_show rather than running real git so the test is hermetic.
# ---------------------------------------------------------------------------


@mock.patch.object(bump_mod, "git_show")
class MainBootstrapTests(unittest.TestCase):
    def _capture_stdout(self):
        buf = io.StringIO()
        self.addCleanup(setattr, sys, "stdout", sys.stdout)
        sys.stdout = buf
        return buf

    def test_bootstrap_when_config_def_absent(self, git_show):
        git_show.return_value = None  # configurationDefinitions.yml not at ref
        buf = self._capture_stdout()
        rc = bump_mod.main(["--since=v0.0.0"])
        self.assertEqual(rc, 0)
        self.assertIn("Bootstrap", buf.getvalue())

    def test_bootstrap_when_schema_field_missing(self, git_show):
        git_show.return_value = "configurationDefinitions:\n  - platform: foo\n"
        buf = self._capture_stdout()
        rc = bump_mod.main(["--since=v0.0.0"])
        self.assertEqual(rc, 0)
        self.assertIn("`schema:` field", buf.getvalue())

    def test_bootstrap_when_historical_schema_absent(self, git_show):
        # First call returns the configurationDefinitions text; second
        # call (for the schema file) returns None.
        git_show.side_effect = ["schema: ./schemas/config.json\n", None]
        buf = self._capture_stdout()
        rc = bump_mod.main(["--since=v0.0.0"])
        self.assertEqual(rc, 0)
        self.assertIn("Bootstrap", buf.getvalue())

    def test_invalid_historical_json_exits_2(self, git_show):
        git_show.side_effect = ["schema: ./schemas/config.json\n", "this is not valid json"]
        # Stub stderr to silence; capture stdout for any messages.
        self._capture_stdout()
        with mock.patch.object(sys, "stderr", io.StringIO()):
            rc = bump_mod.main(["--since=v0.0.0"])
        self.assertEqual(rc, 2)


# ---------------------------------------------------------------------------
# Happy-path: historical schema exists and differs from current; --ci writes.
# ---------------------------------------------------------------------------


class MainHappyPathTests(unittest.TestCase):
    def setUp(self):
        # Point the script at temp paths so we don't write into the real repo.
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        tmp_path = Path(self.tmp.name)

        self.schema_path = tmp_path / "config.json"
        self.config_def_path = tmp_path / "configurationDefinitions.yml"

        # Write a current schema with one extra property -- adds make the
        # diff additive, so a 'minor' bump.
        current = {"type": "object", "properties": {"old_key": {"type": "string"}, "new_key": {"type": "string"}}}
        self.schema_path.write_text(json.dumps(current), encoding="utf-8")

        self.config_def_path.write_text(
            textwrap.dedent("""\
            configurationDefinitions:
              - platform: KUBERNETESCLUSTER
                schema: ./schemas/config.json
                version: 1.2.3
                format: ini
            """),
            encoding="utf-8",
        )

        # Re-point the module's path constants at our temp files.
        self._patch_paths = mock.patch.multiple(
            bump_mod, SCHEMA_PATH=self.schema_path, CONFIG_DEF_PATH=self.config_def_path
        )
        self._patch_paths.start()
        self.addCleanup(self._patch_paths.stop)

    @mock.patch.object(bump_mod, "git_show")
    def test_dry_run_recommends_bump_does_not_write(self, git_show):
        git_show.side_effect = [
            "schema: ./schemas/config.json\nversion: 1.2.3\n",
            json.dumps({"type": "object", "properties": {"old_key": {"type": "string"}}}),
        ]
        before = self.config_def_path.read_text()
        rc = bump_mod.main(["--since=v0.0.0"])
        self.assertEqual(rc, 1)
        self.assertEqual(self.config_def_path.read_text(), before)

    @mock.patch.object(bump_mod, "git_show")
    def test_ci_applies_bump(self, git_show):
        git_show.side_effect = [
            "schema: ./schemas/config.json\nversion: 1.2.3\n",
            json.dumps({"type": "object", "properties": {"old_key": {"type": "string"}}}),
        ]
        rc = bump_mod.main(["--since=v0.0.0", "--ci"])
        self.assertEqual(rc, 1)
        # New key is additive -> minor bump 1.2.3 -> 1.3.0.
        self.assertIn("version: 1.3.0", self.config_def_path.read_text())

    @mock.patch.object(bump_mod, "git_show")
    def test_no_diff_returns_0(self, git_show):
        # Historical schema matches current -> no bump.
        current = json.loads(self.schema_path.read_text())
        git_show.side_effect = ["schema: ./schemas/config.json\nversion: 1.2.3\n", json.dumps(current)]
        rc = bump_mod.main(["--since=v0.0.0"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
