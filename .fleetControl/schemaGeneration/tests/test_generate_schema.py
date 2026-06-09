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

    python3 -m unittest discover .fleetControl/schemaGeneration/tests

The generator script lives one level up; we load it via importlib.util
because the filename has a hyphen and is not importable as a module.

Diff/bump tests (classify_changes, recommend_bump, apply_bump,
bump_version) live in test_schema_diff.py since those helpers were
extracted to schema_diff.py.
"""

import importlib.util
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
# Fake Settings classes -- mimic the real `class FooSettings` convention
# from newrelic.core.config so walk_settings recognizes them.
# ---------------------------------------------------------------------------


class FakeRootSettings:
    """Stands in for newrelic.core.config.TopLevelSettings."""


class FakeChildSettings:
    """Stands in for any nested settings object (e.g. TransactionTracerSettings)."""


class NotASettingsObject:
    """Plain object, intentionally NOT ending in 'Settings'. walk_settings
    must NOT recurse into instances of this class -- it should treat them
    as opaque leaves so AttributeFilter etc. don't get walked.
    """


def make_fake_settings():
    """Build a small Settings tree exercising every supported leaf type."""
    s = FakeRootSettings()
    s.license_key = None
    s.app_name = "Python Application"
    s.monitor_mode = True
    s.log_level = 20  # INFO -- must be translated to 'info' string in schema
    s.log_file = None
    s.proxy_port = None
    s.transaction_tracer = FakeChildSettings()
    s.transaction_tracer.enabled = True
    s.transaction_tracer.transaction_threshold = None
    s.transaction_tracer.record_sql = "obfuscated"
    s.transaction_tracer.stack_trace_threshold = 0.5
    s.transaction_tracer.function_trace = []
    s.attributes = FakeChildSettings()
    s.attributes.enabled = True
    s.attributes.include = set()
    s.attributes.exclude = set()
    # Server-set / runtime -- should be excluded.
    s.agent_run_id = None
    s.beacon = None
    # Subtree exclusion target.
    s.cross_application_tracer = FakeChildSettings()
    s.cross_application_tracer.enabled = False
    # Non-Settings attribute (mimics AttributeFilter on the real settings).
    s.attribute_filter = NotASettingsObject()
    # Private/internal attribute -- should be skipped.
    s._internal = "do not walk me"
    return s


TEST_ENUMS = {
    "log_level": ["critical", "error", "warning", "info", "debug"],
    "transaction_tracer.record_sql": ["off", "raw", "obfuscated"],
}
# Test fixture mirrors the real TYPE_OVERRIDES -- list-typed leaves use the
# new anyOf helper, everything else stays as before.
TEST_TYPES = {
    "transaction_tracer.transaction_threshold": {"type": "string"},
    "transaction_tracer.function_trace": gen.string_array_or_delimited(default=[]),
    "attributes.include": gen.string_array_or_delimited(default=[]),
    "attributes.exclude": gen.string_array_or_delimited(default=[]),
    "log_file": {"type": "string"},
    "proxy_port": {"type": "integer"},
}
TEST_EXCLUDES = {"agent_run_id", "beacon", "cross_application_tracer.*"}


# ---------------------------------------------------------------------------
# infer_type
# ---------------------------------------------------------------------------


class InferTypeTests(unittest.TestCase):
    def test_bool_before_int(self):
        # CRITICAL: bool is a subclass of int. infer_type MUST check bool
        # before int so True/False don't end up as 'integer'.
        self.assertEqual(gen.infer_type(True), "boolean")
        self.assertEqual(gen.infer_type(False), "boolean")

    def test_integer(self):
        self.assertEqual(gen.infer_type(0), "integer")
        self.assertEqual(gen.infer_type(42), "integer")
        self.assertEqual(gen.infer_type(-1), "integer")

    def test_number(self):
        self.assertEqual(gen.infer_type(0.5), "number")
        self.assertEqual(gen.infer_type(-1.25), "number")

    def test_string(self):
        self.assertEqual(gen.infer_type("hello"), "string")
        self.assertEqual(gen.infer_type(""), "string")

    def test_array_types(self):
        self.assertEqual(gen.infer_type([]), "array")
        self.assertEqual(gen.infer_type(set()), "array")
        self.assertEqual(gen.infer_type(()), "array")

    def test_dict_is_object(self):
        self.assertEqual(gen.infer_type({}), "object")

    def test_none_returns_none(self):
        self.assertIsNone(gen.infer_type(None))


# ---------------------------------------------------------------------------
# default_for
# ---------------------------------------------------------------------------


class DefaultForTests(unittest.TestCase):
    def test_set_becomes_sorted_list(self):
        self.assertEqual(gen.default_for({"b", "a", "c"}, "array"), ["a", "b", "c"])

    def test_tuple_becomes_list(self):
        self.assertEqual(gen.default_for((1, 2, 3), "array"), [1, 2, 3])

    def test_other_passthrough(self):
        self.assertEqual(gen.default_for(42, "integer"), 42)
        self.assertEqual(gen.default_for("x", "string"), "x")
        self.assertIs(gen.default_for(True, "boolean"), True)


# ---------------------------------------------------------------------------
# walk_settings
# ---------------------------------------------------------------------------


class WalkSettingsTests(unittest.TestCase):
    def test_yields_top_level_leaves(self):
        s = make_fake_settings()
        leaves = dict(gen.walk_settings(s))
        self.assertIn("license_key", leaves)
        self.assertIn("app_name", leaves)
        self.assertEqual(leaves["app_name"], "Python Application")

    def test_recurses_into_settings_classes(self):
        s = make_fake_settings()
        leaves = dict(gen.walk_settings(s))
        self.assertIn("transaction_tracer.enabled", leaves)
        self.assertIs(leaves["transaction_tracer.enabled"], True)
        self.assertIn("attributes.include", leaves)

    def test_does_not_recurse_into_non_settings_objects(self):
        # NotASettingsObject does not end in 'Settings'. walk must yield
        # it as an opaque leaf rather than descending into it.
        s = make_fake_settings()
        leaves = dict(gen.walk_settings(s))
        self.assertIn("attribute_filter", leaves)
        self.assertIsInstance(leaves["attribute_filter"], NotASettingsObject)

    def test_skips_private_attrs(self):
        s = make_fake_settings()
        leaves = dict(gen.walk_settings(s))
        self.assertNotIn("_internal", leaves)


# ---------------------------------------------------------------------------
# is_excluded
# ---------------------------------------------------------------------------


class IsExcludedTests(unittest.TestCase):
    def test_exact_match(self):
        self.assertTrue(gen.is_excluded("agent_run_id", {"agent_run_id"}))

    def test_no_match(self):
        self.assertFalse(gen.is_excluded("app_name", {"agent_run_id"}))

    def test_wildcard_matches_descendant(self):
        excludes = {"cross_application_tracer.*"}
        self.assertTrue(gen.is_excluded("cross_application_tracer.enabled", excludes))
        self.assertTrue(gen.is_excluded("cross_application_tracer.deep.nested.key", excludes))

    def test_wildcard_matches_root(self):
        # The 'foo.*' entry should also match the bare 'foo' path so a
        # subtree exclude can drop the top-level node too.
        self.assertTrue(gen.is_excluded("cross_application_tracer", {"cross_application_tracer.*"}))

    def test_wildcard_does_not_match_unrelated_key(self):
        excludes = {"cross_application_tracer.*"}
        self.assertFalse(gen.is_excluded("cross_app", excludes))
        self.assertFalse(gen.is_excluded("transaction_tracer.enabled", excludes))


# ---------------------------------------------------------------------------
# anyOf helpers
# ---------------------------------------------------------------------------


class StringArrayOrDelimitedTests(unittest.TestCase):
    def test_shape_no_default(self):
        s = gen.string_array_or_delimited()
        self.assertEqual(s, {"anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "string"}]})

    def test_shape_with_empty_default(self):
        s = gen.string_array_or_delimited(default=[])
        self.assertEqual(s["default"], [])
        self.assertIn("anyOf", s)

    def test_shape_with_populated_default(self):
        s = gen.string_array_or_delimited(default=["a", "b"])
        self.assertEqual(s["default"], ["a", "b"])

    def test_custom_item_type(self):
        s = gen.string_array_or_delimited(item_type="integer")
        self.assertEqual(s["anyOf"][0]["items"], {"type": "integer"})


class StatusCodeArrayOrRangeTests(unittest.TestCase):
    def test_shape_three_options(self):
        s = gen.status_code_array_or_range()
        types = [opt.get("type") for opt in s["anyOf"]]
        self.assertEqual(types, ["integer", "array", "string"])
        # Range string carries a description so consumers know the format.
        self.assertIn("range", s["anyOf"][2]["description"].lower())
        self.assertEqual(s["anyOf"][1]["items"], {"type": "integer"})

    def test_shape_with_default(self):
        s = gen.status_code_array_or_range(default=[404])
        self.assertEqual(s["default"], [404])


# ---------------------------------------------------------------------------
# make_property
# ---------------------------------------------------------------------------


class MakePropertyTests(unittest.TestCase):
    def test_boolean_with_default(self):
        p = gen.make_property("enabled", True, "Enable the thing", TEST_ENUMS, TEST_TYPES)
        self.assertEqual(p["type"], "boolean")
        self.assertIs(p["default"], True)
        self.assertEqual(p["description"], "Enable the thing")

    def test_integer(self):
        p = gen.make_property("count", 42, "", TEST_ENUMS, TEST_TYPES)
        self.assertEqual(p["type"], "integer")
        self.assertEqual(p["default"], 42)
        self.assertNotIn("description", p)

    def test_float_is_number(self):
        p = gen.make_property("threshold", 0.5, "", TEST_ENUMS, TEST_TYPES)
        self.assertEqual(p["type"], "number")
        self.assertEqual(p["default"], 0.5)

    def test_empty_set_auto_anyof(self):
        # Set-typed live values (regardless of population) get auto-anyOf
        # because the underlying agent setting is INI-string-parseable.
        p = gen.make_property("some.set", set(), "", {}, {})
        self.assertNotIn("type", p)
        self.assertIn("anyOf", p)
        self.assertEqual(p["anyOf"][0], {"type": "array", "items": {"type": "string"}})
        self.assertEqual(p["anyOf"][1], {"type": "string"})
        self.assertEqual(p["default"], [])

    def test_set_with_values_anyof_sorted_default(self):
        p = gen.make_property("some.set", {"b", "a"}, "", {}, {})
        self.assertIn("anyOf", p)
        self.assertEqual(p["default"], ["a", "b"])

    def test_set_of_ints_auto_anyof_int_items(self):
        # Auto-anyOf should pick up the inner item type from the first
        # element of a non-empty set.
        p = gen.make_property("status_codes", {404, 500}, "", {}, {})
        self.assertEqual(p["anyOf"][0]["items"], {"type": "integer"})
        self.assertEqual(p["default"], [404, 500])

    def test_empty_list_pins_items_to_string(self):
        # Plain lists (not sets) still emit a regular array. Only set-typed
        # live values trigger the auto-anyOf path.
        p = gen.make_property("some.list", [], "", {}, {})
        self.assertEqual(p["type"], "array")
        self.assertEqual(p["items"], {"type": "string"})
        self.assertEqual(p["default"], [])

    def test_dict_is_object_with_additional_properties_true(self):
        p = gen.make_property("some.dict", {}, "", {}, {})
        self.assertEqual(p["type"], "object")
        self.assertTrue(p["additionalProperties"])

    def test_log_level_int_translated_to_string(self):
        p = gen.make_property("log_level", 20, "", TEST_ENUMS, TEST_TYPES)
        self.assertEqual(p["type"], "string")
        self.assertEqual(p["enum"], TEST_ENUMS["log_level"])
        self.assertEqual(p["default"], "info")  # 20 -> 'info', not 20

    def test_log_level_unknown_int_no_default(self):
        p = gen.make_property("log_level", 99, "", TEST_ENUMS, TEST_TYPES)
        self.assertEqual(p["enum"], TEST_ENUMS["log_level"])
        self.assertNotIn("default", p)

    def test_enum_with_matching_string_default(self):
        p = gen.make_property("transaction_tracer.record_sql", "obfuscated", "", TEST_ENUMS, TEST_TYPES)
        self.assertEqual(p["enum"], TEST_ENUMS["transaction_tracer.record_sql"])
        self.assertEqual(p["default"], "obfuscated")

    def test_enum_with_non_matching_default_no_default(self):
        p = gen.make_property("transaction_tracer.record_sql", "weird", "", TEST_ENUMS, TEST_TYPES)
        self.assertEqual(p["enum"], TEST_ENUMS["transaction_tracer.record_sql"])
        self.assertNotIn("default", p)

    def test_type_override_takes_precedence(self):
        p = gen.make_property("transaction_tracer.transaction_threshold", None, "", TEST_ENUMS, TEST_TYPES)
        self.assertEqual(p["type"], "string")
        self.assertNotIn("default", p)

    def test_type_override_anyof_for_array(self):
        # The TEST_TYPES override for attributes.include uses the
        # string_array_or_delimited helper; the override should win over
        # auto-anyOf and just be applied verbatim.
        p = gen.make_property("attributes.include", set(), "doc", TEST_ENUMS, TEST_TYPES)
        self.assertIn("anyOf", p)
        self.assertEqual(p["anyOf"][0], {"type": "array", "items": {"type": "string"}})
        self.assertEqual(p["anyOf"][1], {"type": "string"})
        self.assertEqual(p["default"], [])
        self.assertEqual(p["description"], "doc")

    def test_none_with_no_override_returns_none(self):
        # license_key has no override in TEST_TYPES; make_property should
        # signal "skip me" to the caller.
        result = gen.make_property("license_key", None, "", {}, {})
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# build_properties
# ---------------------------------------------------------------------------


class BuildPropertiesTests(unittest.TestCase):
    def test_excludes_applied(self):
        s = make_fake_settings()
        props = gen.build_properties(s, {}, TEST_EXCLUDES, TEST_ENUMS, TEST_TYPES)
        self.assertNotIn("agent_run_id", props)
        self.assertNotIn("beacon", props)
        # Subtree exclude drops the descendant.
        self.assertNotIn("cross_application_tracer.enabled", props)

    def test_descriptions_attached_when_present(self):
        s = make_fake_settings()
        descs = {"app_name": "the application name"}
        props = gen.build_properties(s, descs, set(), TEST_ENUMS, TEST_TYPES)
        self.assertEqual(props["app_name"]["description"], "the application name")

    def test_skipped_none_settings_do_not_appear(self):
        s = make_fake_settings()
        # log_file has no TYPE_OVERRIDE in this fixture (we deliberately
        # omit it from TEST_TYPES below) -> should be skipped.
        types = dict(TEST_TYPES)
        types.pop("log_file")
        props = gen.build_properties(s, {}, set(), TEST_ENUMS, types)
        self.assertNotIn("log_file", props)


# ---------------------------------------------------------------------------
# generate_schema -- end-to-end integration against the fake tree
# ---------------------------------------------------------------------------


class GenerateSchemaIntegrationTests(unittest.TestCase):
    def setUp(self):
        s = make_fake_settings()
        descriptions = {
            "app_name": "The application name.",
            "monitor_mode": "Enable monitoring.",
            "transaction_tracer.enabled": "Capture slow transactions.",
        }
        self.schema = gen.generate_schema(
            s, descriptions, exclude_keys=TEST_EXCLUDES, enum_overrides=TEST_ENUMS, type_overrides=TEST_TYPES
        )
        self.props = self.schema["properties"]

    def test_top_level_required(self):
        self.assertEqual(self.schema["required"], ["license_key", "app_name"])

    def test_additional_properties_true(self):
        self.assertTrue(self.schema["additionalProperties"])

    def test_license_key_overridden(self):
        lk = self.props["license_key"]
        self.assertEqual(lk["type"], "string")
        self.assertEqual(lk["minLength"], 1)
        self.assertNotIn("default", lk)
        self.assertIn("license key", lk["description"].lower())

    def test_app_name_string_with_default(self):
        an = self.props["app_name"]
        self.assertEqual(an["type"], "string")
        self.assertEqual(an["default"], "Python Application")
        self.assertEqual(an["description"], "The application name.")

    def test_log_level_uses_enum_with_string_default(self):
        ll = self.props["log_level"]
        self.assertEqual(ll["type"], "string")
        self.assertEqual(ll["enum"], TEST_ENUMS["log_level"])
        self.assertEqual(ll["default"], "info")

    def test_monitor_mode_boolean_default_true(self):
        mm = self.props["monitor_mode"]
        self.assertEqual(mm["type"], "boolean")
        self.assertIs(mm["default"], True)

    def test_transaction_tracer_enabled_boolean(self):
        tt = self.props["transaction_tracer.enabled"]
        self.assertEqual(tt["type"], "boolean")
        self.assertIs(tt["default"], True)

    def test_transaction_threshold_string_via_override(self):
        tt = self.props["transaction_tracer.transaction_threshold"]
        self.assertEqual(tt["type"], "string")
        self.assertNotIn("default", tt)

    def test_attributes_include_anyof_via_override(self):
        ai = self.props["attributes.include"]
        self.assertIn("anyOf", ai)
        self.assertEqual(ai["anyOf"][0], {"type": "array", "items": {"type": "string"}})
        self.assertEqual(ai["anyOf"][1], {"type": "string"})
        self.assertEqual(ai["default"], [])

    def test_excluded_keys_absent(self):
        self.assertNotIn("agent_run_id", self.props)
        self.assertNotIn("beacon", self.props)
        self.assertNotIn("cross_application_tracer.enabled", self.props)


# ---------------------------------------------------------------------------
# parse_ini_descriptions -- INI is now description-only
# ---------------------------------------------------------------------------


class ParseIniDescriptionsTests(unittest.TestCase):
    def test_single_comment_attached(self):
        text = "[newrelic]\n# my comment\nfoo = 1\n"
        self.assertEqual(gen.parse_ini_descriptions(text)["foo"], "my comment")

    def test_multi_line_comment_joined(self):
        text = "[newrelic]\n# line one\n# line two\nfoo = 1\n"
        self.assertEqual(gen.parse_ini_descriptions(text)["foo"], "line one line two")

    def test_blank_line_resets_pending(self):
        text = "[newrelic]\n# stale\n\nfoo = 1\n"
        self.assertNotIn("foo", gen.parse_ini_descriptions(text))

    def test_commented_out_example_does_not_bleed(self):
        text = textwrap.dedent("""\
            [newrelic]
            # proxy_host = hostname

            # real description
            transaction_tracer.enabled = true
            """)
        comments = gen.parse_ini_descriptions(text)
        self.assertEqual(comments["transaction_tracer.enabled"], "real description")

    def test_other_section_ignored(self):
        text = textwrap.dedent("""\
            [newrelic]
            # in newrelic
            foo = 1
            [newrelic:production]
            # in production
            bar = 2
            """)
        comments = gen.parse_ini_descriptions(text)
        self.assertIn("foo", comments)
        self.assertNotIn("bar", comments)


# ---------------------------------------------------------------------------
# merge_schemas -- still lives in generate-schema.py
# ---------------------------------------------------------------------------


class MergeSchemasTests(unittest.TestCase):
    def test_empty_old_returns_new(self):
        new = {"type": "object", "properties": {"foo": {"type": "string"}}}
        self.assertEqual(gen.merge_schemas({}, new), new)

    def test_keys_only_in_old_preserved(self):
        old = {"type": "object", "properties": {"legacy": {"type": "string", "default": "x"}}}
        new = {"type": "object", "properties": {"fresh": {"type": "integer"}}}
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


if __name__ == "__main__":
    unittest.main()
