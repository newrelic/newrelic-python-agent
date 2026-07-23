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

"""Unit tests for schema_diff.py.

The classify/recommend_bump/apply_bump/bump_version helpers were lifted
out of generate-schema.py so bump-schema-version.py can reuse them. This
file exercises that shared module directly.

Run from the repo root:

    python3 -m unittest discover .fleetControl/schemaGeneration/tests
"""

import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

# schema_diff.py is a regular Python module living next to generate-schema.py.
# Add the parent directory to sys.path so it imports cleanly without the
# importlib.util dance the hyphenated scripts need.
_SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPT_DIR))
import schema_diff  # noqa: E402


def _obj(props, required=None, additional=True):
    node = {"type": "object", "properties": props, "additionalProperties": additional}
    if required is not None:
        node["required"] = required
    return node


def _by_kind(changes):
    return {c["kind"]: c for c in changes}


class ClassifyChangesTests(unittest.TestCase):
    def test_no_changes(self):
        s = _obj({"foo": {"type": "string", "default": "x"}})
        self.assertEqual(schema_diff.classify_changes(s, s), [])

    def test_added_is_additive(self):
        ch = schema_diff.classify_changes(_obj({}), _obj({"foo": {"type": "string"}}))
        self.assertEqual(ch[0]["severity"], "additive")

    def test_removed_is_breaking(self):
        ch = schema_diff.classify_changes(_obj({"foo": {"type": "string"}}), _obj({}))
        self.assertEqual(ch[0]["severity"], "breaking")

    def test_type_change_is_breaking(self):
        ch = _by_kind(
            schema_diff.classify_changes(_obj({"foo": {"type": "string"}}), _obj({"foo": {"type": "integer"}}))
        )
        self.assertEqual(ch["type_changed"]["severity"], "breaking")

    def test_required_added_is_breaking(self):
        ch = _by_kind(
            schema_diff.classify_changes(
                _obj({"foo": {"type": "string"}}, []), _obj({"foo": {"type": "string"}}, ["foo"])
            )
        )
        self.assertEqual(ch["required_added"]["severity"], "breaking")

    def test_required_removed_is_additive(self):
        ch = _by_kind(
            schema_diff.classify_changes(
                _obj({"foo": {"type": "string"}}, ["foo"]), _obj({"foo": {"type": "string"}}, [])
            )
        )
        self.assertEqual(ch["required_removed"]["severity"], "additive")

    def test_additional_properties_tightened_is_breaking(self):
        ch = _by_kind(schema_diff.classify_changes(_obj({}, None, True), _obj({}, None, False)))
        self.assertEqual(ch["additional_properties_tightened"]["severity"], "breaking")

    def test_additional_properties_loosened_is_additive(self):
        ch = _by_kind(schema_diff.classify_changes(_obj({}, None, False), _obj({}, None, True)))
        self.assertEqual(ch["additional_properties_loosened"]["severity"], "additive")

    def test_enum_value_removed_is_breaking(self):
        ch = schema_diff.classify_changes(
            _obj({"x": {"type": "string", "enum": ["a", "b"]}}), _obj({"x": {"type": "string", "enum": ["a"]}})
        )
        self.assertEqual(next(c for c in ch if c["kind"] == "enum_value_removed")["severity"], "breaking")

    def test_enum_value_added_is_additive(self):
        ch = schema_diff.classify_changes(
            _obj({"x": {"type": "string", "enum": ["a"]}}), _obj({"x": {"type": "string", "enum": ["a", "b"]}})
        )
        self.assertEqual(next(c for c in ch if c["kind"] == "enum_value_added")["severity"], "additive")

    def test_enum_introduced_is_breaking(self):
        ch = _by_kind(
            schema_diff.classify_changes(
                _obj({"x": {"type": "string"}}), _obj({"x": {"type": "string", "enum": ["a"]}})
            )
        )
        self.assertEqual(ch["enum_introduced"]["severity"], "breaking")

    def test_default_changed_is_additive(self):
        ch = _by_kind(
            schema_diff.classify_changes(
                _obj({"x": {"type": "string", "default": "a"}}), _obj({"x": {"type": "string", "default": "b"}})
            )
        )
        self.assertEqual(ch["default_changed"]["severity"], "additive")

    def test_description_changed_is_cosmetic(self):
        ch = _by_kind(
            schema_diff.classify_changes(
                _obj({"x": {"type": "string", "description": "old"}}),
                _obj({"x": {"type": "string", "description": "new"}}),
            )
        )
        self.assertEqual(ch["description_changed"]["severity"], "cosmetic")


class RecommendBumpTests(unittest.TestCase):
    def test_breaking_is_major(self):
        self.assertEqual(schema_diff.recommend_bump([{"severity": "breaking"}]), "major")

    def test_additive_is_minor(self):
        self.assertEqual(schema_diff.recommend_bump([{"severity": "additive"}]), "minor")

    def test_cosmetic_is_patch(self):
        self.assertEqual(schema_diff.recommend_bump([{"severity": "cosmetic"}]), "patch")

    def test_empty_is_none(self):
        self.assertEqual(schema_diff.recommend_bump([]), "none")

    def test_breaking_wins_over_additive(self):
        self.assertEqual(schema_diff.recommend_bump([{"severity": "additive"}, {"severity": "breaking"}]), "major")


class ApplyBumpTests(unittest.TestCase):
    def test_apply_bumps(self):
        self.assertEqual(schema_diff.apply_bump("1.2.3", "major"), "2.0.0")
        self.assertEqual(schema_diff.apply_bump("1.2.3", "minor"), "1.3.0")
        self.assertEqual(schema_diff.apply_bump("1.2.3", "patch"), "1.2.4")
        self.assertEqual(schema_diff.apply_bump("1.2.3", "none"), "1.2.3")

    def test_apply_bump_invalid_semver(self):
        with self.assertRaises(ValueError):
            schema_diff.apply_bump("not-semver", "major")

    def test_apply_bump_unknown_kind(self):
        with self.assertRaises(ValueError):
            schema_diff.apply_bump("1.2.3", "weird")


FIXTURE_YAML = textwrap.dedent("""\
    configurationDefinitions:
      - platform: KUBERNETESCLUSTER
        description: Test agent configuration
        type: agent-config
        version: 1.2.3
        schema: ./schemas/config.json
        format: ini
    """)


class BumpVersionTests(unittest.TestCase):
    def _temp_yaml(self, content=FIXTURE_YAML):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return Path(f.name)

    def test_read_returns_old_new(self):
        path = self._temp_yaml()
        old_v, new_v = schema_diff.bump_version(path, "minor", False)
        self.assertEqual(old_v, "1.2.3")
        self.assertEqual(new_v, "1.3.0")

    def test_write_false_does_not_touch_file(self):
        path = self._temp_yaml()
        before = path.read_text()
        schema_diff.bump_version(path, "major", False)
        self.assertEqual(path.read_text(), before)

    def test_write_true_mutates(self):
        path = self._temp_yaml()
        schema_diff.bump_version(path, "major", True)
        self.assertIn("version: 2.0.0", path.read_text())

    def test_missing_version_raises(self):
        path = self._temp_yaml("configurationDefinitions:\n  - platform: foo\n")
        with self.assertRaises(RuntimeError):
            schema_diff.bump_version(path, "major", False)


class LoadExistingTests(unittest.TestCase):
    def test_missing_returns_empty(self):
        self.assertEqual(schema_diff.load_existing("/nonexistent/path/to/schema.json"), {})

    def test_malformed_json_returns_empty(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        f.write("{ this is not valid json")
        f.close()
        self.addCleanup(os.unlink, f.name)
        self.assertEqual(schema_diff.load_existing(f.name), {})

    def test_valid_json_round_trips(self):
        import json

        payload = {"type": "object", "properties": {"foo": {"type": "string"}}}
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(payload, f)
        f.close()
        self.addCleanup(os.unlink, f.name)
        self.assertEqual(schema_diff.load_existing(f.name), payload)


if __name__ == "__main__":
    unittest.main()
