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

"""Unit tests for generate-schema.py.

Run from the repo root:

    python -m unittest discover .fleetControl/schemaGeneration/tests

The generator script lives one level up; we load it via importlib.util
because the filename has a hyphen and is not importable as a module.
"""

import importlib.util
import os
import tempfile
import textwrap
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Load generate-schema.py as a module under the alias `gen`
# ---------------------------------------------------------------------------
_SCRIPT = Path(__file__).resolve().parent.parent / "generate-schema.py"
_spec = importlib.util.spec_from_file_location("gen", _SCRIPT)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


# ---------------------------------------------------------------------------
# Test-local override fixtures (mirror Java's pattern of passing override
# maps as parameters so production constants don't leak in)
# ---------------------------------------------------------------------------
TEST_ENUMS = {"log_level": ["off", "info", "debug"]}
TEST_TYPES = {
    "error_collector.ignore_classes": {
        "type": "array", "items": {"type": "string"}, "default": [],
    },
}
TEST_EXCLUDES = {"some_excluded_key"}


class InferTypeTests(unittest.TestCase):
    def test_boolean(self):
        self.assertEqual(gen.infer_type("true"), "boolean")
        self.assertEqual(gen.infer_type("false"), "boolean")
        self.assertEqual(gen.infer_type("True"), "boolean")
        self.assertEqual(gen.infer_type("FALSE"), "boolean")

    def test_integer(self):
        self.assertEqual(gen.infer_type("0"), "integer")
        self.assertEqual(gen.infer_type("42"), "integer")
        self.assertEqual(gen.infer_type("-1"), "integer")

    def test_number(self):
        self.assertEqual(gen.infer_type("0.5"), "number")
        self.assertEqual(gen.infer_type("-1.25"), "number")

    def test_string_default(self):
        self.assertEqual(gen.infer_type("hello"), "string")
        self.assertEqual(gen.infer_type("apdex_f"), "string")

    def test_empty_and_none(self):
        self.assertEqual(gen.infer_type(""), "string")
        self.assertEqual(gen.infer_type(None), "string")


class CoerceDefaultTests(unittest.TestCase):
    def test_boolean(self):
        self.assertIs(gen.coerce_default("true", "boolean"), True)
        self.assertIs(gen.coerce_default("False", "boolean"), False)

    def test_integer(self):
        self.assertEqual(gen.coerce_default("42", "integer"), 42)

    def test_number(self):
        self.assertEqual(gen.coerce_default("0.5", "number"), 0.5)

    def test_string_preserves_input(self):
        # No strip -- the caller passes the value as-is so spacing is preserved.
        self.assertEqual(gen.coerce_default("Python Application", "string"),
                         "Python Application")


class ParseIniTests(unittest.TestCase):
    def test_single_comment_attached_to_key(self):
        text = "[newrelic]\n# my comment\nfoo = 1\n"
        keys, comments = gen.parse_ini(text)
        self.assertEqual(keys, {"foo": "1"})
        self.assertEqual(comments["foo"], "my comment")

    def test_multi_line_comment_joined(self):
        text = "[newrelic]\n# line one\n# line two\nfoo = 1\n"
        _, comments = gen.parse_ini(text)
        self.assertEqual(comments["foo"], "line one line two")

    def test_blank_line_resets_pending(self):
        text = "[newrelic]\n# stale comment\n\nfoo = 1\n"
        _, comments = gen.parse_ini(text)
        self.assertNotIn("foo", comments)

    def test_commented_out_example_does_not_bleed(self):
        # Mirrors the proxy_host example block in newrelic.ini: a commented-out
        # `# proxy_host = hostname` followed by a blank, then a real key with
        # its own description must NOT inherit the proxy_host comment text.
        text = textwrap.dedent("""\
            [newrelic]
            # proxy_host = hostname

            # real description
            transaction_tracer.enabled = true
            """)
        _, comments = gen.parse_ini(text)
        self.assertEqual(comments["transaction_tracer.enabled"], "real description")

    def test_section_header_resets_pending(self):
        text = textwrap.dedent("""\
            # stale top-of-file comment
            [newrelic]
            foo = 1
            """)
        _, comments = gen.parse_ini(text)
        self.assertNotIn("foo", comments)

    def test_only_named_section_is_parsed(self):
        text = textwrap.dedent("""\
            [newrelic]
            foo = 1
            [newrelic:production]
            bar = 2
            """)
        keys, _ = gen.parse_ini(text, section="newrelic")
        self.assertIn("foo", keys)
        self.assertNotIn("bar", keys)

    def test_dotted_keys_preserved(self):
        text = "[newrelic]\ntransaction_tracer.enabled = true\n"
        keys, _ = gen.parse_ini(text)
        self.assertIn("transaction_tracer.enabled", keys)


class MakePropertyTests(unittest.TestCase):
    def test_boolean_with_default(self):
        p = gen.make_property("enabled", "true", "Enable the thing",
                              TEST_ENUMS, TEST_TYPES)
        self.assertEqual(p["type"], "boolean")
        self.assertIs(p["default"], True)
        self.assertEqual(p["description"], "Enable the thing")

    def test_integer_no_description(self):
        p = gen.make_property("count", "42", "", TEST_ENUMS, TEST_TYPES)
        self.assertEqual(p["type"], "integer")
        self.assertEqual(p["default"], 42)
        self.assertNotIn("description", p)

    def test_empty_string_omits_default(self):
        p = gen.make_property("ignore", "", "", TEST_ENUMS, TEST_TYPES)
        self.assertEqual(p["type"], "string")
        self.assertNotIn("default", p)

    def test_enum_override_with_matching_default(self):
        p = gen.make_property("log_level", "info", "", TEST_ENUMS, TEST_TYPES)
        self.assertEqual(p["type"], "string")
        self.assertEqual(p["enum"], ["off", "info", "debug"])
        self.assertEqual(p["default"], "info")

    def test_enum_override_without_matching_default(self):
        # Default not in enum -> no default emitted (avoid invalid schema).
        p = gen.make_property("log_level", "verbose", "", TEST_ENUMS, TEST_TYPES)
        self.assertEqual(p["enum"], ["off", "info", "debug"])
        self.assertNotIn("default", p)

    def test_type_override_takes_precedence(self):
        p = gen.make_property("error_collector.ignore_classes", "FooException",
                              "doc", TEST_ENUMS, TEST_TYPES)
        self.assertEqual(p["type"], "array")
        self.assertEqual(p["items"], {"type": "string"})
        self.assertEqual(p["default"], [])
        self.assertEqual(p["description"], "doc")


class BuildPropertiesTests(unittest.TestCase):
    def test_excludes_keys(self):
        keys = {"some_excluded_key": "true", "agent_enabled": "true"}
        comments = {}
        props = gen.build_properties(keys, comments, TEST_EXCLUDES,
                                     TEST_ENUMS, TEST_TYPES)
        self.assertNotIn("some_excluded_key", props)
        self.assertIn("agent_enabled", props)

    def test_descriptions_attach(self):
        keys = {"foo": "true"}
        comments = {"foo": "foo description"}
        props = gen.build_properties(keys, comments, TEST_EXCLUDES,
                                     TEST_ENUMS, TEST_TYPES)
        self.assertEqual(props["foo"]["description"], "foo description")


class GenerateSchemaIntegrationTests(unittest.TestCase):
    """Exercise the full pipeline against an inline INI fixture."""

    FIXTURE = textwrap.dedent("""\
        # Top-of-file comment that should NOT bleed into license_key.

        [newrelic]
        # The license key.
        license_key = *** REPLACE ME ***

        # The application name.
        app_name = My App

        # Logging configuration.
        log_level = info

        # Stale comment that should NOT bleed into the next key.

        # Real description for transaction_tracer.enabled.
        transaction_tracer.enabled = true

        # Threshold for SQL stack trace.
        transaction_tracer.stack_trace_threshold = 0.5

        # Ignore list (override forces array).
        error_collector.ignore_classes =

        [newrelic:production]
        # This should never be parsed.
        ignored_key = should_not_appear
        """)

    def setUp(self):
        self.fixture_enums = {"log_level": ["off", "info", "debug"]}
        self.fixture_types = {
            "error_collector.ignore_classes": {
                "type": "array", "items": {"type": "string"}, "default": [],
            },
        }
        self.schema = gen.generate_schema(
            self.FIXTURE,
            exclude_keys=set(),
            enum_overrides=self.fixture_enums,
            type_overrides=self.fixture_types,
        )

    def test_top_level_required(self):
        self.assertEqual(self.schema["required"], ["license_key", "app_name"])

    def test_additional_properties_true(self):
        self.assertTrue(self.schema["additionalProperties"])

    def test_license_key_overridden(self):
        lk = self.schema["properties"]["license_key"]
        self.assertEqual(lk["type"], "string")
        self.assertEqual(lk["minLength"], 1)
        self.assertNotIn("default", lk)
        self.assertIn("license key", lk["description"].lower())

    def test_app_name_string_with_default(self):
        an = self.schema["properties"]["app_name"]
        self.assertEqual(an["type"], "string")
        self.assertEqual(an["default"], "My App")
        self.assertIn("application name", an["description"].lower())

    def test_log_level_enum_with_default(self):
        ll = self.schema["properties"]["log_level"]
        self.assertEqual(ll["enum"], ["off", "info", "debug"])
        self.assertEqual(ll["default"], "info")

    def test_transaction_tracer_enabled_no_stale_comment(self):
        prop = self.schema["properties"]["transaction_tracer.enabled"]
        self.assertEqual(prop["type"], "boolean")
        self.assertIs(prop["default"], True)
        self.assertIn("Real description", prop["description"])
        self.assertNotIn("Stale comment", prop["description"])

    def test_float_inferred_as_number(self):
        prop = self.schema["properties"]["transaction_tracer.stack_trace_threshold"]
        self.assertEqual(prop["type"], "number")
        self.assertEqual(prop["default"], 0.5)

    def test_type_override_applied(self):
        prop = self.schema["properties"]["error_collector.ignore_classes"]
        self.assertEqual(prop["type"], "array")
        self.assertEqual(prop["items"], {"type": "string"})
        self.assertEqual(prop["default"], [])

    def test_environment_section_ignored(self):
        self.assertNotIn("ignored_key", self.schema["properties"])


class MergeSchemasTests(unittest.TestCase):
    def test_empty_old_returns_new(self):
        new = {"type": "object", "properties": {"foo": {"type": "string"}}}
        self.assertEqual(gen.merge_schemas({}, new), new)

    def test_keys_only_in_old_preserved(self):
        old = {"type": "object", "properties": {"legacy": {"type": "string", "default": "x"}}}
        new = {"type": "object", "properties": {"fresh":  {"type": "integer"}}}
        merged = gen.merge_schemas(old, new)
        self.assertIn("legacy", merged["properties"])
        self.assertIn("fresh", merged["properties"])
        self.assertEqual(merged["properties"]["legacy"]["default"], "x")

    def test_keys_in_both_new_wins(self):
        old = {"type": "object", "properties": {"foo": {"type": "string", "default": "old"}}}
        new = {"type": "object", "properties": {"foo": {"type": "string", "default": "new"}}}
        merged = gen.merge_schemas(old, new)
        self.assertEqual(merged["properties"]["foo"]["default"], "new")

    def test_top_level_required_uses_new(self):
        old = {"type": "object", "properties": {"foo": {"type": "string"}}, "required": ["foo"]}
        new = {"type": "object", "properties": {"foo": {"type": "string"}}, "required": []}
        merged = gen.merge_schemas(old, new)
        self.assertEqual(merged["required"], [])

    def test_type_change_clears_stale_constraints(self):
        old = {"type": "object", "properties": {"x": {"type": "string", "enum": ["a", "b"]}}}
        new = {"type": "object", "properties": {"x": {"type": "integer", "default": 5}}}
        merged = gen.merge_schemas(old, new)
        x = merged["properties"]["x"]
        self.assertEqual(x["type"], "integer")
        self.assertEqual(x["default"], 5)
        self.assertNotIn("enum", x)

    def test_top_level_title_takes_new(self):
        old = {"type": "object", "properties": {}, "title": "old", "description": "old"}
        new = {"type": "object", "properties": {}, "title": "new", "description": "new"}
        merged = gen.merge_schemas(old, new)
        self.assertEqual(merged["title"], "new")
        self.assertEqual(merged["description"], "new")


def _obj(props, required=None, additional=True):
    node = {"type": "object", "properties": props,
            "additionalProperties": additional}
    if required is not None:
        node["required"] = required
    return node


def _by_kind(changes):
    return {c["kind"]: c for c in changes}


class ClassifyChangesTests(unittest.TestCase):
    def test_no_changes(self):
        s = _obj({"foo": {"type": "string", "default": "x"}})
        self.assertEqual(gen.classify_changes(s, s), [])

    def test_added_is_additive(self):
        ch = gen.classify_changes(_obj({}), _obj({"foo": {"type": "string"}}))
        self.assertEqual(len(ch), 1)
        self.assertEqual(ch[0]["path"], "foo")
        self.assertEqual(ch[0]["severity"], "additive")

    def test_removed_is_breaking(self):
        ch = gen.classify_changes(_obj({"foo": {"type": "string"}}), _obj({}))
        self.assertEqual(ch[0]["kind"], "removed")
        self.assertEqual(ch[0]["severity"], "breaking")

    def test_type_change_is_breaking(self):
        ch = _by_kind(gen.classify_changes(
            _obj({"foo": {"type": "string"}}),
            _obj({"foo": {"type": "integer"}}),
        ))
        self.assertEqual(ch["type_changed"]["severity"], "breaking")
        self.assertIn("string", ch["type_changed"]["detail"])
        self.assertIn("integer", ch["type_changed"]["detail"])

    def test_required_added_is_breaking(self):
        ch = _by_kind(gen.classify_changes(
            _obj({"foo": {"type": "string"}}, []),
            _obj({"foo": {"type": "string"}}, ["foo"]),
        ))
        self.assertEqual(ch["required_added"]["severity"], "breaking")

    def test_required_removed_is_additive(self):
        ch = _by_kind(gen.classify_changes(
            _obj({"foo": {"type": "string"}}, ["foo"]),
            _obj({"foo": {"type": "string"}}, []),
        ))
        self.assertEqual(ch["required_removed"]["severity"], "additive")

    def test_additional_properties_tightened_is_breaking(self):
        ch = _by_kind(gen.classify_changes(
            _obj({}, None, True), _obj({}, None, False),
        ))
        self.assertEqual(ch["additional_properties_tightened"]["severity"], "breaking")

    def test_additional_properties_implicit_true_matches_explicit(self):
        old = {"type": "object", "properties": {}}
        new = {"type": "object", "properties": {}, "additionalProperties": True}
        self.assertEqual(gen.classify_changes(old, new), [])

    def test_enum_value_removed_is_breaking(self):
        ch = gen.classify_changes(
            _obj({"x": {"type": "string", "enum": ["a", "b", "c"]}}),
            _obj({"x": {"type": "string", "enum": ["a", "c"]}}),
        )
        removed = next(c for c in ch if c["kind"] == "enum_value_removed")
        self.assertEqual(removed["severity"], "breaking")
        self.assertIn("'b'", removed["detail"])

    def test_enum_value_added_is_additive(self):
        ch = gen.classify_changes(
            _obj({"x": {"type": "string", "enum": ["a"]}}),
            _obj({"x": {"type": "string", "enum": ["a", "b"]}}),
        )
        added = next(c for c in ch if c["kind"] == "enum_value_added")
        self.assertEqual(added["severity"], "additive")

    def test_enum_introduced_is_breaking(self):
        ch = _by_kind(gen.classify_changes(
            _obj({"x": {"type": "string"}}),
            _obj({"x": {"type": "string", "enum": ["a", "b"]}}),
        ))
        self.assertEqual(ch["enum_introduced"]["severity"], "breaking")

    def test_default_changed_is_additive(self):
        ch = _by_kind(gen.classify_changes(
            _obj({"x": {"type": "string", "default": "a"}}),
            _obj({"x": {"type": "string", "default": "b"}}),
        ))
        self.assertEqual(ch["default_changed"]["severity"], "additive")

    def test_description_changed_is_cosmetic(self):
        ch = _by_kind(gen.classify_changes(
            _obj({"x": {"type": "string", "description": "old"}}),
            _obj({"x": {"type": "string", "description": "new"}}),
        ))
        self.assertEqual(ch["description_changed"]["severity"], "cosmetic")


class RenderChangeTests(unittest.TestCase):
    def test_added(self):
        self.assertEqual(
            gen.render_change({"path": "foo.bar", "kind": "added",
                               "severity": "additive", "detail": "new property"}),
            "+ foo.bar: new property",
        )

    def test_removed_no_detail(self):
        self.assertEqual(
            gen.render_change({"path": "foo", "kind": "removed",
                               "severity": "breaking", "detail": ""}),
            "- foo",
        )

    def test_type_changed(self):
        self.assertEqual(
            gen.render_change({"path": "foo", "kind": "type_changed",
                               "severity": "breaking", "detail": "type x -> y"}),
            "~ foo: type x -> y",
        )


class RecommendBumpTests(unittest.TestCase):
    def test_any_breaking_is_major(self):
        ch = [{"severity": "cosmetic"}, {"severity": "additive"}, {"severity": "breaking"}]
        self.assertEqual(gen.recommend_bump(ch), "major")

    def test_additive_without_breaking_is_minor(self):
        self.assertEqual(gen.recommend_bump(
            [{"severity": "cosmetic"}, {"severity": "additive"}]), "minor")

    def test_cosmetic_only_is_patch(self):
        self.assertEqual(gen.recommend_bump([{"severity": "cosmetic"}]), "patch")

    def test_empty_is_none(self):
        self.assertEqual(gen.recommend_bump([]), "none")


class ApplyBumpTests(unittest.TestCase):
    def test_major(self):
        self.assertEqual(gen.apply_bump("1.2.3", "major"), "2.0.0")

    def test_minor(self):
        self.assertEqual(gen.apply_bump("1.2.3", "minor"), "1.3.0")

    def test_patch(self):
        self.assertEqual(gen.apply_bump("1.2.3", "patch"), "1.2.4")

    def test_none_passthrough(self):
        self.assertEqual(gen.apply_bump("1.2.3", "none"), "1.2.3")

    def test_non_semver_raises(self):
        with self.assertRaises(ValueError):
            gen.apply_bump("not-semver", "major")


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
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False, encoding="utf-8"
        )
        f.write(content)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return Path(f.name)

    def test_read_returns_old_new(self):
        path = self._temp_yaml()
        old_v, new_v = gen.bump_version(path, "minor", False)
        self.assertEqual(old_v, "1.2.3")
        self.assertEqual(new_v, "1.3.0")

    def test_write_false_does_not_touch_file(self):
        path = self._temp_yaml()
        before = path.read_text()
        gen.bump_version(path, "major", False)
        self.assertEqual(path.read_text(), before)

    def test_write_true_mutates(self):
        path = self._temp_yaml()
        gen.bump_version(path, "major", True)
        self.assertIn("version: 2.0.0", path.read_text())
        # And nothing else should change.
        self.assertIn("description: Test agent configuration", path.read_text())
        self.assertIn("schema: ./schemas/config.json", path.read_text())

    def test_none_bump_no_op_even_with_write(self):
        path = self._temp_yaml()
        before = path.read_text()
        old_v, new_v = gen.bump_version(path, "none", True)
        self.assertEqual(old_v, new_v)
        self.assertEqual(path.read_text(), before)

    def test_missing_version_raises(self):
        path = self._temp_yaml("configurationDefinitions:\n  - platform: foo\n")
        with self.assertRaises(RuntimeError):
            gen.bump_version(path, "major", False)


if __name__ == "__main__":
    unittest.main()
