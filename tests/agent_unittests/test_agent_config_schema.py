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

"""Unit tests for the Fleet Control config schema tooling in
.fleetControl/schemaGeneration/ (generate-schema.py, schema_diff.py,
bump-schema-version.py).
"""

import importlib.util
import json
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load the hyphenated scripts via importlib (not importable as modules by
# name) and the shared schema_diff module they both depend on.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_DIR = _REPO_ROOT / ".fleetControl" / "schemaGeneration"

_gen_spec = importlib.util.spec_from_file_location("gen", _SCRIPT_DIR / "generate-schema.py")
gen = importlib.util.module_from_spec(_gen_spec)
_gen_spec.loader.exec_module(gen)  # also inserts SCRIPT_DIR onto sys.path as a side effect

_bump_spec = importlib.util.spec_from_file_location("bump_schema_version", _SCRIPT_DIR / "bump-schema-version.py")
bump_mod = importlib.util.module_from_spec(_bump_spec)
_bump_spec.loader.exec_module(bump_mod)

import schema_diff  # noqa: E402  (already on sys.path via gen's exec_module above)
from schema_diff import ADDITIVE, BREAKING, COSMETIC, MAJOR, MINOR, NO_BUMP, PATCH  # noqa: E402

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


TEST_ENUMS = {"transaction_tracer.record_sql": ["off", "raw", "obfuscated"]}
# Test fixture mirrors the real TYPE_OVERRIDES -- list-typed leaves use the
# anyOf helper, everything else stays as before.
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


def test_infer_type_bool_before_int():
    # CRITICAL: bool is a subclass of int. infer_type MUST check bool
    # before int so True/False don't end up as 'integer'.
    assert gen.infer_type(True) == "boolean"
    assert gen.infer_type(False) == "boolean"


def test_infer_type_integer():
    assert gen.infer_type(0) == "integer"
    assert gen.infer_type(42) == "integer"
    assert gen.infer_type(-1) == "integer"


def test_infer_type_number():
    assert gen.infer_type(0.5) == "number"
    assert gen.infer_type(-1.25) == "number"


def test_infer_type_string():
    assert gen.infer_type("hello") == "string"
    assert gen.infer_type("") == "string"


def test_infer_type_array_types():
    assert gen.infer_type([]) == "array"
    assert gen.infer_type(set()) == "array"
    assert gen.infer_type(()) == "array"


def test_infer_type_dict_is_object():
    assert gen.infer_type({}) == "object"


def test_infer_type_none_returns_none():
    assert gen.infer_type(None) is None


# ---------------------------------------------------------------------------
# default_for
# ---------------------------------------------------------------------------


def test_default_for_set_becomes_sorted_list():
    assert gen.default_for({"b", "a", "c"}, "array") == ["a", "b", "c"]


def test_default_for_tuple_becomes_list():
    assert gen.default_for((1, 2, 3), "array") == [1, 2, 3]


def test_default_for_other_passthrough():
    assert gen.default_for(42, "integer") == 42
    assert gen.default_for("x", "string") == "x"
    assert gen.default_for(True, "boolean") is True


# ---------------------------------------------------------------------------
# walk_settings
# ---------------------------------------------------------------------------


def test_walk_settings_yields_top_level_leaves():
    s = make_fake_settings()
    leaves = dict(gen.walk_settings(s))
    assert "license_key" in leaves
    assert "app_name" in leaves
    assert leaves["app_name"] == "Python Application"


def test_walk_settings_recurses_into_settings_classes():
    s = make_fake_settings()
    leaves = dict(gen.walk_settings(s))
    assert "transaction_tracer.enabled" in leaves
    assert leaves["transaction_tracer.enabled"] is True
    assert "attributes.include" in leaves


def test_walk_settings_does_not_recurse_into_non_settings_objects():
    # NotASettingsObject does not end in 'Settings'. walk must yield
    # it as an opaque leaf rather than descending into it.
    s = make_fake_settings()
    leaves = dict(gen.walk_settings(s))
    assert "attribute_filter" in leaves
    assert isinstance(leaves["attribute_filter"], NotASettingsObject)


def test_walk_settings_skips_private_attrs():
    s = make_fake_settings()
    leaves = dict(gen.walk_settings(s))
    assert "_internal" not in leaves


# ---------------------------------------------------------------------------
# is_excluded
# ---------------------------------------------------------------------------


def test_is_excluded_exact_match():
    assert gen.is_excluded("agent_run_id", {"agent_run_id"})


def test_is_excluded_no_match():
    assert not gen.is_excluded("app_name", {"agent_run_id"})


def test_is_excluded_wildcard_matches_descendant():
    excludes = {"cross_application_tracer.*"}
    assert gen.is_excluded("cross_application_tracer.enabled", excludes)
    assert gen.is_excluded("cross_application_tracer.deep.nested.key", excludes)


def test_is_excluded_wildcard_matches_root():
    # The 'foo.*' entry should also match the bare 'foo' path so a
    # subtree exclude can drop the top-level node too.
    assert gen.is_excluded("cross_application_tracer", {"cross_application_tracer.*"})


def test_is_excluded_wildcard_does_not_match_unrelated_key():
    excludes = {"cross_application_tracer.*"}
    assert not gen.is_excluded("cross_app", excludes)
    assert not gen.is_excluded("transaction_tracer.enabled", excludes)


# ---------------------------------------------------------------------------
# anyOf helpers
# ---------------------------------------------------------------------------


def test_string_array_or_delimited_shape_no_default():
    s = gen.string_array_or_delimited()
    assert s == {"anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "string"}]}


def test_string_array_or_delimited_shape_with_empty_default():
    s = gen.string_array_or_delimited(default=[])
    assert s["default"] == []
    assert "anyOf" in s


def test_string_array_or_delimited_shape_with_populated_default():
    s = gen.string_array_or_delimited(default=["a", "b"])
    assert s["default"] == ["a", "b"]


def test_string_array_or_delimited_custom_item_type():
    s = gen.string_array_or_delimited(item_type="integer")
    assert s["anyOf"][0]["items"] == {"type": "integer"}


def test_status_code_array_or_range_shape_three_options():
    s = gen.status_code_array_or_range()
    types = [opt.get("type") for opt in s["anyOf"]]
    assert types == ["integer", "array", "string"]
    # Range string carries a description so consumers know the format.
    assert "range" in s["anyOf"][2]["description"].lower()
    assert s["anyOf"][1]["items"] == {"type": "integer"}


def test_status_code_array_or_range_shape_with_default():
    s = gen.status_code_array_or_range(default=[404])
    assert s["default"] == [404]


# ---------------------------------------------------------------------------
# make_property
# ---------------------------------------------------------------------------


def test_make_property_boolean_with_default():
    p = gen.make_property("enabled", True, "Enable the thing", TEST_ENUMS, TEST_TYPES)
    assert p["type"] == "boolean"
    assert p["default"] is True
    assert p["description"] == "Enable the thing"


def test_make_property_integer():
    p = gen.make_property("count", 42, "", TEST_ENUMS, TEST_TYPES)
    assert p["type"] == "integer"
    assert p["default"] == 42
    assert "description" not in p


def test_make_property_float_is_number():
    p = gen.make_property("threshold", 0.5, "", TEST_ENUMS, TEST_TYPES)
    assert p["type"] == "number"
    assert p["default"] == 0.5


def test_make_property_empty_set_auto_anyof():
    # Set-typed live values (regardless of population) get auto-anyOf
    # because the underlying agent setting is INI-string-parseable.
    p = gen.make_property("some.set", set(), "", {}, {})
    assert "type" not in p
    assert "anyOf" in p
    assert p["anyOf"][0] == {"type": "array", "items": {"type": "string"}}
    assert p["anyOf"][1] == {"type": "string"}
    assert p["default"] == []


def test_make_property_set_with_values_anyof_sorted_default():
    p = gen.make_property("some.set", {"b", "a"}, "", {}, {})
    assert "anyOf" in p
    assert p["default"] == ["a", "b"]


def test_make_property_set_of_ints_auto_anyof_int_items():
    # Auto-anyOf should pick up the inner item type from the first
    # element of a non-empty set.
    p = gen.make_property("status_codes", {404, 500}, "", {}, {})
    assert p["anyOf"][0]["items"] == {"type": "integer"}
    assert p["default"] == [404, 500]


def test_make_property_empty_list_pins_items_to_string():
    # Plain lists (not sets) still emit a regular array. Only set-typed
    # live values trigger the auto-anyOf path.
    p = gen.make_property("some.list", [], "", {}, {})
    assert p["type"] == "array"
    assert p["items"] == {"type": "string"}
    assert p["default"] == []


def test_make_property_dict_is_object_with_additional_properties_true():
    p = gen.make_property("some.dict", {}, "", {}, {})
    assert p["type"] == "object"
    assert p["additionalProperties"]


def test_make_property_log_level_int_translated_to_string():
    p = gen.make_property("log_level", 20, "", TEST_ENUMS, TEST_TYPES)
    assert p["type"] == "string"
    assert "enum" not in p
    assert p["default"] == "info"  # 20 -> 'info', not 20


def test_make_property_log_level_unknown_int_no_default():
    p = gen.make_property("log_level", 99, "", TEST_ENUMS, TEST_TYPES)
    assert p["type"] == "string"
    assert "enum" not in p
    assert "default" not in p


def test_make_property_enum_with_matching_string_default():
    p = gen.make_property("transaction_tracer.record_sql", "obfuscated", "", TEST_ENUMS, TEST_TYPES)
    assert p["enum"] == TEST_ENUMS["transaction_tracer.record_sql"]
    assert p["default"] == "obfuscated"


def test_make_property_enum_with_non_matching_default_no_default():
    p = gen.make_property("transaction_tracer.record_sql", "weird", "", TEST_ENUMS, TEST_TYPES)
    assert p["enum"] == TEST_ENUMS["transaction_tracer.record_sql"]
    assert "default" not in p


def test_make_property_type_override_takes_precedence():
    p = gen.make_property("transaction_tracer.transaction_threshold", None, "", TEST_ENUMS, TEST_TYPES)
    assert p["type"] == "string"
    assert "default" not in p


def test_make_property_type_override_anyof_for_array():
    # The TEST_TYPES override for attributes.include uses the
    # string_array_or_delimited helper; the override should win over
    # auto-anyOf and just be applied verbatim.
    p = gen.make_property("attributes.include", set(), "doc", TEST_ENUMS, TEST_TYPES)
    assert "anyOf" in p
    assert p["anyOf"][0] == {"type": "array", "items": {"type": "string"}}
    assert p["anyOf"][1] == {"type": "string"}
    assert p["default"] == []
    assert p["description"] == "doc"


def test_make_property_none_with_no_override_returns_none():
    # license_key has no override in TEST_TYPES; make_property should
    # signal "skip me" to the caller.
    result = gen.make_property("license_key", None, "", {}, {})
    assert result is None


# ---------------------------------------------------------------------------
# build_properties
# ---------------------------------------------------------------------------


def test_build_properties_excludes_applied():
    s = make_fake_settings()
    props = gen.build_properties(s, {}, TEST_EXCLUDES, TEST_ENUMS, TEST_TYPES)
    assert "agent_run_id" not in props
    assert "beacon" not in props
    # Subtree exclude drops the descendant.
    assert "cross_application_tracer.enabled" not in props


def test_build_properties_descriptions_attached_when_present():
    s = make_fake_settings()
    descs = {"app_name": "the application name"}
    props = gen.build_properties(s, descs, set(), TEST_ENUMS, TEST_TYPES)
    assert props["app_name"]["description"] == "the application name"


def test_build_properties_skipped_none_settings_do_not_appear():
    s = make_fake_settings()
    # log_file has no TYPE_OVERRIDE in this fixture (we deliberately
    # omit it from TEST_TYPES below) -> should be skipped.
    types = dict(TEST_TYPES)
    types.pop("log_file")
    props = gen.build_properties(s, {}, set(), TEST_ENUMS, types)
    assert "log_file" not in props


def test_build_properties_write_only_applied_to_secret_settings():
    # Mirrors the strip/obfuscate list in
    # newrelic.core.config.global_settings_dump().
    class FakeSettings:
        pass

    s = FakeSettings()
    s.api_key = "secret-key"
    s.proxy_user = "user"
    s.proxy_pass = "pass"
    s.app_name = "not a secret"

    types = {"api_key": {"type": "string"}, "proxy_user": {"type": "string"}, "proxy_pass": {"type": "string"}}
    props = gen.build_properties(s, {}, set(), {}, types)
    assert props["api_key"]["writeOnly"]
    assert props["proxy_user"]["writeOnly"]
    assert props["proxy_pass"]["writeOnly"]
    assert "writeOnly" not in props["app_name"]


# ---------------------------------------------------------------------------
# generate_schema -- end-to-end integration against the fake tree
# ---------------------------------------------------------------------------


@pytest.fixture
def generated_schema():
    s = make_fake_settings()
    descriptions = {
        "app_name": "The application name.",
        "monitor_mode": "Enable monitoring.",
        "transaction_tracer.enabled": "Capture slow transactions.",
    }
    return gen.generate_schema(
        s, descriptions, exclude_keys=TEST_EXCLUDES, enum_overrides=TEST_ENUMS, type_overrides=TEST_TYPES
    )


@pytest.fixture
def generated_props(generated_schema):
    return generated_schema["properties"]


def test_generate_schema_top_level_required(generated_schema):
    assert generated_schema["required"] == ["license_key", "app_name"]


def test_generate_schema_additional_properties_true(generated_schema):
    assert generated_schema["additionalProperties"]


def test_generate_schema_license_key_overridden(generated_props):
    lk = generated_props["license_key"]
    assert lk["type"] == "string"
    assert lk["minLength"] == 1
    assert "default" not in lk
    assert "license key" in lk["description"].lower()
    assert lk["writeOnly"]


def test_generate_schema_app_name_string_with_default(generated_props):
    an = generated_props["app_name"]
    assert an["type"] == "string"
    assert an["default"] == "Python Application"
    assert an["description"] == "The application name."


def test_generate_schema_log_level_is_string_with_default(generated_props):
    ll = generated_props["log_level"]
    assert ll["type"] == "string"
    assert "enum" not in ll
    assert ll["default"] == "info"


def test_generate_schema_monitor_mode_boolean_default_true(generated_props):
    mm = generated_props["monitor_mode"]
    assert mm["type"] == "boolean"
    assert mm["default"] is True


def test_generate_schema_transaction_tracer_enabled_boolean(generated_props):
    tt = generated_props["transaction_tracer.enabled"]
    assert tt["type"] == "boolean"
    assert tt["default"] is True


def test_generate_schema_transaction_threshold_string_via_override(generated_props):
    tt = generated_props["transaction_tracer.transaction_threshold"]
    assert tt["type"] == "string"
    assert "default" not in tt


def test_generate_schema_attributes_include_anyof_via_override(generated_props):
    ai = generated_props["attributes.include"]
    assert "anyOf" in ai
    assert ai["anyOf"][0] == {"type": "array", "items": {"type": "string"}}
    assert ai["anyOf"][1] == {"type": "string"}
    assert ai["default"] == []


def test_generate_schema_excluded_keys_absent(generated_props):
    assert "agent_run_id" not in generated_props
    assert "beacon" not in generated_props
    assert "cross_application_tracer.enabled" not in generated_props


# ---------------------------------------------------------------------------
# parse_ini_descriptions -- INI is now description-only
# ---------------------------------------------------------------------------


def test_parse_ini_descriptions_single_comment_attached():
    text = "[newrelic]\n# my comment\nfoo = 1\n"
    assert gen.parse_ini_descriptions(text)["foo"] == "my comment"


def test_parse_ini_descriptions_multi_line_comment_joined():
    text = "[newrelic]\n# line one\n# line two\nfoo = 1\n"
    assert gen.parse_ini_descriptions(text)["foo"] == "line one line two"


def test_parse_ini_descriptions_blank_line_resets_pending():
    text = "[newrelic]\n# stale\n\nfoo = 1\n"
    assert "foo" not in gen.parse_ini_descriptions(text)


def test_parse_ini_descriptions_commented_out_example_does_not_bleed():
    text = textwrap.dedent("""\
        [newrelic]
        # proxy_host = hostname

        # real description
        transaction_tracer.enabled = true
        """)
    comments = gen.parse_ini_descriptions(text)
    assert comments["transaction_tracer.enabled"] == "real description"


def test_parse_ini_descriptions_other_section_ignored():
    text = textwrap.dedent("""\
        [newrelic]
        # in newrelic
        foo = 1
        [newrelic:production]
        # in production
        bar = 2
        """)
    comments = gen.parse_ini_descriptions(text)
    assert "foo" in comments
    assert "bar" not in comments


# ---------------------------------------------------------------------------
# merge_schemas -- still lives in generate-schema.py
# ---------------------------------------------------------------------------


def test_merge_schemas_empty_old_returns_new():
    new = {"type": "object", "properties": {"foo": {"type": "string"}}}
    assert gen.merge_schemas({}, new) == new


def test_merge_schemas_keys_only_in_old_preserved():
    old = {"type": "object", "properties": {"legacy": {"type": "string", "default": "x"}}}
    new = {"type": "object", "properties": {"fresh": {"type": "integer"}}}
    merged = gen.merge_schemas(old, new)
    assert "legacy" in merged["properties"]
    assert "fresh" in merged["properties"]
    assert merged["properties"]["legacy"]["default"] == "x"


def test_merge_schemas_keys_in_both_new_wins():
    old = {"type": "object", "properties": {"foo": {"type": "string", "default": "old"}}}
    new = {"type": "object", "properties": {"foo": {"type": "string", "default": "new"}}}
    merged = gen.merge_schemas(old, new)
    assert merged["properties"]["foo"]["default"] == "new"


def test_merge_schemas_top_level_required_uses_new():
    old = {"type": "object", "properties": {"foo": {"type": "string"}}, "required": ["foo"]}
    new = {"type": "object", "properties": {"foo": {"type": "string"}}, "required": []}
    merged = gen.merge_schemas(old, new)
    assert merged["required"] == []


def test_merge_schemas_type_change_clears_stale_constraints():
    old = {"type": "object", "properties": {"x": {"type": "string", "enum": ["a", "b"]}}}
    new = {"type": "object", "properties": {"x": {"type": "integer", "default": 5}}}
    merged = gen.merge_schemas(old, new)
    x = merged["properties"]["x"]
    assert x["type"] == "integer"
    assert x["default"] == 5
    assert "enum" not in x


# ---------------------------------------------------------------------------
# schema_diff.classify_changes
# ---------------------------------------------------------------------------


def _obj(props, required=None, additional=True):
    node = {"type": "object", "properties": props, "additionalProperties": additional}
    if required is not None:
        node["required"] = required
    return node


def _by_kind(changes):
    return {c["kind"]: c for c in changes}


def test_classify_changes_no_changes():
    s = _obj({"foo": {"type": "string", "default": "x"}})
    assert schema_diff.classify_changes(s, s) == []


def test_classify_changes_added_is_additive():
    ch = schema_diff.classify_changes(_obj({}), _obj({"foo": {"type": "string"}}))
    assert ch[0]["severity"] == ADDITIVE


def test_classify_changes_removed_is_breaking():
    ch = schema_diff.classify_changes(_obj({"foo": {"type": "string"}}), _obj({}))
    assert ch[0]["severity"] == BREAKING


def test_classify_changes_type_change_is_breaking():
    ch = _by_kind(schema_diff.classify_changes(_obj({"foo": {"type": "string"}}), _obj({"foo": {"type": "integer"}})))
    assert ch["type_changed"]["severity"] == BREAKING


def test_classify_changes_required_added_is_breaking():
    ch = _by_kind(
        schema_diff.classify_changes(_obj({"foo": {"type": "string"}}, []), _obj({"foo": {"type": "string"}}, ["foo"]))
    )
    assert ch["required_added"]["severity"] == BREAKING


def test_classify_changes_required_removed_is_additive():
    ch = _by_kind(
        schema_diff.classify_changes(_obj({"foo": {"type": "string"}}, ["foo"]), _obj({"foo": {"type": "string"}}, []))
    )
    assert ch["required_removed"]["severity"] == ADDITIVE


def test_classify_changes_additional_properties_tightened_is_breaking():
    ch = _by_kind(schema_diff.classify_changes(_obj({}, None, True), _obj({}, None, False)))
    assert ch["additional_properties_tightened"]["severity"] == BREAKING


def test_classify_changes_additional_properties_loosened_is_additive():
    ch = _by_kind(schema_diff.classify_changes(_obj({}, None, False), _obj({}, None, True)))
    assert ch["additional_properties_loosened"]["severity"] == ADDITIVE


def test_classify_changes_enum_value_removed_is_breaking():
    ch = schema_diff.classify_changes(
        _obj({"x": {"type": "string", "enum": ["a", "b"]}}), _obj({"x": {"type": "string", "enum": ["a"]}})
    )
    assert next(c for c in ch if c["kind"] == "enum_value_removed")["severity"] == BREAKING


def test_classify_changes_enum_value_added_is_additive():
    ch = schema_diff.classify_changes(
        _obj({"x": {"type": "string", "enum": ["a"]}}), _obj({"x": {"type": "string", "enum": ["a", "b"]}})
    )
    assert next(c for c in ch if c["kind"] == "enum_value_added")["severity"] == ADDITIVE


def test_classify_changes_enum_introduced_is_breaking():
    ch = _by_kind(
        schema_diff.classify_changes(_obj({"x": {"type": "string"}}), _obj({"x": {"type": "string", "enum": ["a"]}}))
    )
    assert ch["enum_introduced"]["severity"] == BREAKING


def test_classify_changes_default_changed_is_additive():
    ch = _by_kind(
        schema_diff.classify_changes(
            _obj({"x": {"type": "string", "default": "a"}}), _obj({"x": {"type": "string", "default": "b"}})
        )
    )
    assert ch["default_changed"]["severity"] == ADDITIVE


def test_classify_changes_description_changed_is_cosmetic():
    ch = _by_kind(
        schema_diff.classify_changes(
            _obj({"x": {"type": "string", "description": "old"}}), _obj({"x": {"type": "string", "description": "new"}})
        )
    )
    assert ch["description_changed"]["severity"] == COSMETIC


def test_classify_changes_write_only_introduced_is_breaking():
    # writeOnly has no dedicated handling -- it falls through to the
    # generic keyword catch-all, same as any other unrecognized keyword.
    ch = _by_kind(
        schema_diff.classify_changes(
            _obj({"x": {"type": "string"}}), _obj({"x": {"type": "string", "writeOnly": True}})
        )
    )
    assert ch["writeOnly_changed"]["severity"] == BREAKING


def test_classify_changes_arbitrary_unrecognized_keyword_changed_is_breaking():
    # No special-casing required -- any keyword not in the dedicated
    # list (type/enum/default/description) is caught generically.
    ch = _by_kind(
        schema_diff.classify_changes(
            _obj({"x": {"type": "integer", "minimum": 1}}), _obj({"x": {"type": "integer", "minimum": 5}})
        )
    )
    assert ch["minimum_changed"]["severity"] == BREAKING


def test_classify_changes_unrecognized_keyword_unchanged_is_not_reported():
    ch = schema_diff.classify_changes(
        _obj({"x": {"type": "string", "pattern": "^a"}}), _obj({"x": {"type": "string", "pattern": "^a"}})
    )
    assert ch == []


# ---------------------------------------------------------------------------
# schema_diff.recommend_bump / apply_bump / bump_version / load_existing
# ---------------------------------------------------------------------------


def test_recommend_bump_breaking_is_major():
    assert schema_diff.recommend_bump([{"severity": BREAKING}]) == MAJOR


def test_recommend_bump_additive_is_minor():
    assert schema_diff.recommend_bump([{"severity": ADDITIVE}]) == MINOR


def test_recommend_bump_cosmetic_is_patch():
    assert schema_diff.recommend_bump([{"severity": COSMETIC}]) == PATCH


def test_recommend_bump_empty_is_none():
    assert schema_diff.recommend_bump([]) == NO_BUMP


def test_recommend_bump_breaking_wins_over_additive():
    assert schema_diff.recommend_bump([{"severity": ADDITIVE}, {"severity": BREAKING}]) == MAJOR


def test_apply_bump_bumps():
    assert schema_diff.apply_bump("1.2.3", MAJOR) == "2.0.0"
    assert schema_diff.apply_bump("1.2.3", MINOR) == "1.3.0"
    assert schema_diff.apply_bump("1.2.3", PATCH) == "1.2.4"
    assert schema_diff.apply_bump("1.2.3", NO_BUMP) == "1.2.3"


def test_apply_bump_invalid_semver():
    with pytest.raises(ValueError):
        schema_diff.apply_bump("not-semver", MAJOR)


def test_apply_bump_unknown_kind():
    with pytest.raises(ValueError):
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


def _write_yaml(tmp_path, content=FIXTURE_YAML):
    path = tmp_path / "configurationDefinitions.yml"
    path.write_text(content, encoding="utf-8")
    return path


def test_bump_version_read_returns_old_new(tmp_path):
    path = _write_yaml(tmp_path)
    old_v, new_v = schema_diff.bump_version(path, MINOR, False)
    assert old_v == "1.2.3"
    assert new_v == "1.3.0"


def test_bump_version_write_false_does_not_touch_file(tmp_path):
    path = _write_yaml(tmp_path)
    before = path.read_text()
    schema_diff.bump_version(path, MAJOR, False)
    assert path.read_text() == before


def test_bump_version_write_true_mutates(tmp_path):
    path = _write_yaml(tmp_path)
    schema_diff.bump_version(path, MAJOR, True)
    assert "version: 2.0.0" in path.read_text()


def test_bump_version_missing_version_raises(tmp_path):
    path = _write_yaml(tmp_path, "configurationDefinitions:\n  - platform: foo\n")
    with pytest.raises(RuntimeError):
        schema_diff.bump_version(path, MAJOR, False)


def test_load_existing_missing_returns_empty():
    assert schema_diff.load_existing("/nonexistent/path/to/schema.json") == {}


def test_load_existing_malformed_json_returns_empty(tmp_path):
    path = tmp_path / "schema.json"
    path.write_text("{ this is not valid json", encoding="utf-8")
    assert schema_diff.load_existing(path) == {}


def test_load_existing_valid_json_round_trips(tmp_path):
    payload = {"type": "object", "properties": {"foo": {"type": "string"}}}
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert schema_diff.load_existing(path) == payload


# ---------------------------------------------------------------------------
# bump-schema-version.py -- parse_schema_path / historical_schema_path_in_repo
# ---------------------------------------------------------------------------


def test_parse_schema_path_finds_schema_line():
    text = textwrap.dedent("""\
        configurationDefinitions:
          - platform: KUBERNETESCLUSTER
            schema: ./schemas/config.json
            format: ini
        """)
    assert bump_mod.parse_schema_path(text) == "./schemas/config.json"


def test_parse_schema_path_no_schema_line_returns_none():
    text = "configurationDefinitions:\n  - platform: foo\n"
    assert bump_mod.parse_schema_path(text) is None


def test_parse_schema_path_handles_indentation():
    # The regex must be tolerant of varying leading whitespace.
    text = "    schema: my/schema.json\n"
    assert bump_mod.parse_schema_path(text) == "my/schema.json"


def test_historical_schema_path_in_repo_strips_leading_dot_slash():
    assert bump_mod.historical_schema_path_in_repo("./schemas/config.json") == ".fleetControl/schemas/config.json"


def test_historical_schema_path_in_repo_no_dot_slash():
    assert bump_mod.historical_schema_path_in_repo("schemas/config.json") == ".fleetControl/schemas/config.json"


# ---------------------------------------------------------------------------
# bump-schema-version.py -- main() bootstrap and happy-path branches.
#
# git_show is monkeypatched rather than running real git so the test is
# hermetic.
# ---------------------------------------------------------------------------


def _stub_git_show(monkeypatch, *returns):
    values = iter(returns)
    monkeypatch.setattr(bump_mod, "git_show", lambda *args, **kwargs: next(values))


def test_main_bootstrap_when_config_def_absent(monkeypatch, capsys):
    _stub_git_show(monkeypatch, None)  # configurationDefinitions.yml not at ref
    rc = bump_mod.main(["--since=v0.0.0"])
    assert rc == 0
    assert "Bootstrap" in capsys.readouterr().out


def test_main_bootstrap_when_schema_field_missing(monkeypatch, capsys):
    _stub_git_show(monkeypatch, "configurationDefinitions:\n  - platform: foo\n")
    rc = bump_mod.main(["--since=v0.0.0"])
    assert rc == 0
    assert "`schema:` field" in capsys.readouterr().out


def test_main_bootstrap_when_historical_schema_absent(monkeypatch, capsys):
    # First call returns the configurationDefinitions text; second call
    # (for the schema file) returns None.
    _stub_git_show(monkeypatch, "schema: ./schemas/config.json\n", None)
    rc = bump_mod.main(["--since=v0.0.0"])
    assert rc == 0
    assert "Bootstrap" in capsys.readouterr().out


def test_main_invalid_historical_json_exits_2(monkeypatch, capsys):
    _stub_git_show(monkeypatch, "schema: ./schemas/config.json\n", "this is not valid json")
    rc = bump_mod.main(["--since=v0.0.0"])
    assert rc == 2


@pytest.fixture
def bump_paths(tmp_path, monkeypatch):
    """Point bump_mod's path constants at temp files so main() doesn't
    write into the real repo. Current schema has one extra property
    relative to the historical one used in each test, so the diff is
    additive -> minor bump.
    """
    schema_path = tmp_path / "config.json"
    config_def_path = tmp_path / "configurationDefinitions.yml"

    current = {"type": "object", "properties": {"old_key": {"type": "string"}, "new_key": {"type": "string"}}}
    schema_path.write_text(json.dumps(current), encoding="utf-8")

    config_def_path.write_text(
        textwrap.dedent("""\
            configurationDefinitions:
              - platform: KUBERNETESCLUSTER
                schema: ./schemas/config.json
                version: 1.2.3
                format: ini
            """),
        encoding="utf-8",
    )

    monkeypatch.setattr(bump_mod, "SCHEMA_PATH", schema_path)
    monkeypatch.setattr(bump_mod, "CONFIG_DEF_PATH", config_def_path)

    return schema_path, config_def_path


def test_main_happy_path_dry_run_recommends_bump_does_not_write(bump_paths, monkeypatch):
    _, config_def_path = bump_paths
    _stub_git_show(
        monkeypatch,
        "schema: ./schemas/config.json\nversion: 1.2.3\n",
        json.dumps({"type": "object", "properties": {"old_key": {"type": "string"}}}),
    )
    before = config_def_path.read_text()
    rc = bump_mod.main(["--since=v0.0.0"])
    assert rc == 1
    assert config_def_path.read_text() == before


def test_main_happy_path_ci_applies_bump(bump_paths, monkeypatch):
    _, config_def_path = bump_paths
    _stub_git_show(
        monkeypatch,
        "schema: ./schemas/config.json\nversion: 1.2.3\n",
        json.dumps({"type": "object", "properties": {"old_key": {"type": "string"}}}),
    )
    rc = bump_mod.main(["--since=v0.0.0", "--ci"])
    assert rc == 1
    # New key is additive -> minor bump 1.2.3 -> 1.3.0.
    assert "version: 1.3.0" in config_def_path.read_text()


def test_main_happy_path_no_diff_returns_0(bump_paths, monkeypatch):
    schema_path, _ = bump_paths
    # Historical schema matches current -> no bump.
    current = json.loads(schema_path.read_text())
    _stub_git_show(monkeypatch, "schema: ./schemas/config.json\nversion: 1.2.3\n", json.dumps(current))
    rc = bump_mod.main(["--since=v0.0.0"])
    assert rc == 0
