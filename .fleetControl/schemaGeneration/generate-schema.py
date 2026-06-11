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

"""
Fleet Control Config Schema Generator -- Python Agent

Walks `newrelic.core.config.global_settings()` and writes JSON Schema
Draft 2020-12 to .fleetControl/schemas/config.json.

Source of truth:
  The agent's live settings tree (`global_settings()`) is the source of
  truth for *which* keys exist, their *types*, and their *default values*.
  Descriptions still come from `newrelic/newrelic.ini` because that is
  the only place the agent ships human-readable explanations of the
  settings; settings not documented there are emitted without a
  description.

Environment requirement:
  `import newrelic.core.config` reads NEW_RELIC_* environment variables
  to populate certain defaults at import time (NEW_RELIC_LICENSE_KEY,
  NEW_RELIC_LOG, NEW_RELIC_ENABLED, etc.). RUN THIS GENERATOR WITH NO
  NEW_RELIC_* VARIABLES SET, otherwise their values leak into the
  generated schema's defaults. The CI workflow unsets them explicitly
  before invocation; locally, ensure your shell does not export any.

Merge behavior:
  The generator never starts fresh -- each run deep-merges the freshly
  generated schema into whatever already exists at config.json. Properties
  are union'd (keys present only in the old schema are preserved); leaf
  nodes and the top-level `required` list take the new run's values. This
  guarantees the published schema only ever grows, so a config that
  validated against an older agent's schema continues to validate against
  the current one.

Version bumping is NOT this script's concern. See bump-schema-version.py
for the release-time bump path. This script only writes config.json; it
never touches configurationDefinitions.yml.

Diff helpers (classify_changes, recommend_bump, etc.) live in schema_diff.py
and are imported when needed for the per-run change report.

Exit codes:
  0 -- no schema changes (or first run, or --force mode)
  1 -- schema changed and on-disk differed (CI should commit)
  2 -- hard failure (invalid schema, malformed inputs)

Run standalone:
  python3 generate-schema.py

Force-regenerate without comparing:
  python3 generate-schema.py --force

---------------------------------------------------------------------------
Why the schema emits `additionalProperties: true`
---------------------------------------------------------------------------
The generator sets `additionalProperties: true` at the root. This is
intentional and serves two purposes:

  1. Forward compatibility. The agent ships new config keys in every
     release. A Fleet Control deployment may be validating against a
     schema generated from an older agent -- strict validation would
     reject any newer key, breaking users who upgrade the agent before
     the schema is republished.

  2. Coverage gaps. Some keys are deliberately excluded (see EXCLUDE_KEYS)
     and some shapes the generator can't represent faithfully (settings
     with None defaults and no TYPE_OVERRIDE entry). Permitting unknown
     properties means a config that uses those still validates instead
     of being flagged as malformed.

If a future requirement calls for strict validation (catch typos, reject
unknown keys), flip this to `false` -- but doing so should be paired with
a release process that republishes the schema in lockstep with the agent.

---------------------------------------------------------------------------
Why list-typed settings emit `anyOf [array, string]`
---------------------------------------------------------------------------
The Python agent's INI format documents many list values as space- or
comma-separated *strings* (e.g. `attributes.include = foo bar baz`).
The agent parses these via `_environ_as_set` / `_environ_as_comma_separated_set`
in newrelic/core/config.py, then exposes them as Python `set` objects in
`global_settings()`.

A schema that emits `{"type": "array", ...}` for these would reject every
legitimate INI configuration -- the user can't write a JSON array in an
INI file. Emitting `anyOf [array, string]` instead means both the
structured form (used by configuration formats that *do* support it,
like Fleet Control's structured backend) and the INI string form validate.

The generator handles this in two layers:

  1. Explicit overrides via `string_array_or_delimited()` in TYPE_OVERRIDES.
     Used for keys whose live default is an empty list (so set vs. list
     can't be inferred from the value alone) or that need a special
     description.

  2. Auto-detection in `make_property`: any leaf whose live value is a
     Python `set` is emitted as `anyOf [array, string]` regardless of
     whether it's in TYPE_OVERRIDES. This catches the long tail of
     `_environ_as_set`-backed settings (the seven `*.attributes.*`
     subtrees, opentelemetry.traces.*, heroku.dyno_name_prefixes_to_shorten,
     etc.) without requiring a per-key allowlist.
"""

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths -- all resolved relative to this script. Script lives at
# <repo-root>/.fleetControl/schemaGeneration/ so the repo root is two
# levels up.
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
FLEET_CONTROL_DIR = SCRIPT_DIR.parent
REPO_ROOT = FLEET_CONTROL_DIR.parent
SCHEMA_DIR = FLEET_CONTROL_DIR / "schemas"
SCHEMA_PATH = SCHEMA_DIR / "config.json"
CONFIG_DEF_PATH = FLEET_CONTROL_DIR / "configurationDefinitions.yml"
DEFAULT_INI_PATH = REPO_ROOT / "newrelic" / "newrelic.ini"

# Make `import newrelic` resolve to this repo's source rather than any
# globally-installed agent.
sys.path.insert(0, str(REPO_ROOT))

# Schema-diff helpers live in their own module so bump-schema-version.py
# can reuse them. Use the explicit relative-import dance because this
# script is loaded as __main__ (not a package).
sys.path.insert(0, str(SCRIPT_DIR))
from schema_diff import classify_changes, load_existing, print_changes  # noqa: E402

# ---------------------------------------------------------------------------
# Type override helpers -- factory functions for common shape patterns.
# ---------------------------------------------------------------------------


def string_array_or_delimited(default=None, item_type="string"):
    """Schema for keys that accept either a YAML/JSON array OR a delimited
    string (space- or comma-separated).

    The Python agent parses these via `_environ_as_set` /
    `_environ_as_comma_separated_set`, so the INI string form is
    documented as the user-facing format. The structured array form is
    accepted for Fleet Control consumers that emit structured config.
    """
    schema = {"anyOf": [{"type": "array", "items": {"type": item_type}}, {"type": "string"}]}
    if default is not None:
        schema["default"] = default
    return schema


def status_code_array_or_range(default=None):
    """Schema for status code keys that accept an integer, an array of
    integers, or a delimited string with optional range syntax
    (e.g. "100-102 200-208 226 300-308 404").

    Parsed by `_parse_status_codes` in newrelic/core/config.py. The
    range string form is what newrelic.ini documents.
    """
    schema = {
        "anyOf": [
            {"type": "integer"},
            {"type": "array", "items": {"type": "integer"}},
            {
                "type": "string",
                "description": (
                    'Comma- or space-separated integers and ranges (e.g. "100-102 200-208 226 300-308 404")'
                ),
            },
        ]
    }
    if default is not None:
        schema["default"] = default
    return schema


# ---------------------------------------------------------------------------
# Enum overrides. The customer-facing form of a setting may differ from
# its in-memory representation -- log_level for example is stored as a
# Python logging int (20 == INFO) but customers configure it as a string.
# When an enum override matches a setting whose live default is not in
# the enum, the override emits the enum's first matching string and the
# inferred type is dropped in favor of `string`.
# ---------------------------------------------------------------------------
ENUM_OVERRIDES = {
    "log_level": ["critical", "error", "warning", "info", "debug"],
    "transaction_tracer.record_sql": ["off", "raw", "obfuscated"],
}

# Settings whose live default is an int log-level but the schema should
# present a string. Used by make_property to pick the right enum default.
LOG_LEVEL_INT_TO_STRING = {50: "critical", 40: "error", 30: "warning", 20: "info", 10: "debug"}

# ---------------------------------------------------------------------------
# Type overrides -- when the live default doesn't tell the full story.
# Three reasons to use this:
#   (a) The leaf default is None, so we cannot infer the JSON Schema type
#       (proxy_*, ca_bundle_path, audit_log_file, transaction_threshold).
#   (b) The leaf is a list/set whose default is empty, so the items type
#       cannot be inferred from contents -- and we want the explicit
#       anyOf [array, string] shape used by INI list values.
#   (c) The leaf needs a multi-form anyOf shape (status codes:
#       int | int[] | range string).
# ---------------------------------------------------------------------------
TYPE_OVERRIDES = {
    # --- INI string-or-array list values (parsed via _environ_as_set,
    # _environ_as_comma_separated_set, or documented as space-separated
    # in newrelic.ini). Empty defaults can't be inferred as set-typed
    # from the live value, so they need the override here. The auto-
    # detection in make_property covers the non-empty cases (sets in
    # global_settings() get anyOf'd automatically).
    "error_collector.ignore_classes": string_array_or_delimited(default=[]),
    "error_collector.expected_classes": string_array_or_delimited(default=[]),
    "transaction_tracer.function_trace": string_array_or_delimited(default=[]),
    "transaction_tracer.generator_trace": string_array_or_delimited(default=[]),
    "attributes.include": string_array_or_delimited(default=[]),
    "attributes.exclude": string_array_or_delimited(default=[]),
    # --- Status codes (integer | array of integers | range string) ---
    "error_collector.ignore_status_codes": status_code_array_or_range(),
    "error_collector.expected_status_codes": status_code_array_or_range(),
    # None-defaulted leaves -- declare the type so the setting still appears.
    "transaction_tracer.transaction_threshold": {"type": "string"},  # 'apdex_f' or float-as-string
    "proxy_host": {"type": "string"},
    "proxy_port": {"type": "integer"},
    "proxy_user": {"type": "string"},
    "proxy_pass": {"type": "string"},
    "proxy_scheme": {"type": "string"},
    "ca_bundle_path": {"type": "string"},
    "audit_log_file": {"type": "string"},
    "log_file": {"type": "string"},
    "labels": {"type": "string"},  # documented as "name1:value1;name2:value2"
    "api_key": {"type": "string"},  # deprecated but still documented in INI
    "cloud.aws.account_id": {"type": "integer"},  # 12-digit number
    "transaction_name.limit": {"type": "integer"},
    "transaction_name.naming_scheme": {"type": "string"},
    "browser_monitoring.loader_version": {"type": "string"},
    "browser_monitoring.ssl_for_http": {"type": "boolean"},
    "console.listener_socket": {"type": "string"},
    "debug.otlp_content_encoding": {"type": "string"},
    "agent_limits.data_compression_level": {"type": "integer"},
    "capture_params": {"type": "boolean"},
    "utilization.billing_hostname": {"type": "string"},
    # Distributed tracing sampler knobs -- all None-defaulted; types come
    # from the leaf names (sampling_target -> int, ratio -> float). Listed
    # explicitly so future additions are visible.
    "distributed_tracing.sampler.root.adaptive.sampling_target": {"type": "integer"},
    "distributed_tracing.sampler.root.trace_id_ratio_based.ratio": {"type": "number"},
    "distributed_tracing.sampler.remote_parent_sampled.adaptive.sampling_target": {"type": "integer"},
    "distributed_tracing.sampler.remote_parent_sampled.trace_id_ratio_based.ratio": {"type": "number"},
    "distributed_tracing.sampler.remote_parent_not_sampled.adaptive.sampling_target": {"type": "integer"},
    "distributed_tracing.sampler.remote_parent_not_sampled.trace_id_ratio_based.ratio": {"type": "number"},
    "distributed_tracing.sampler.partial_granularity.root.adaptive.sampling_target": {"type": "integer"},
    "distributed_tracing.sampler.partial_granularity.root.trace_id_ratio_based.ratio": {"type": "number"},
    "distributed_tracing.sampler.partial_granularity.remote_parent_sampled.adaptive.sampling_target": {
        "type": "integer"
    },
    "distributed_tracing.sampler.partial_granularity.remote_parent_sampled.trace_id_ratio_based.ratio": {
        "type": "number"
    },
    "distributed_tracing.sampler.partial_granularity.remote_parent_not_sampled.adaptive.sampling_target": {
        "type": "integer"
    },
    "distributed_tracing.sampler.partial_granularity.remote_parent_not_sampled.trace_id_ratio_based.ratio": {
        "type": "number"
    },
}

# ---------------------------------------------------------------------------
# Keys to exclude from the customer-facing schema.
#
# Matching: an entry without a trailing `.*` matches a leaf path exactly;
# an entry ending in `.*` matches any descendant of that prefix. Easy to
# surface a setting later -- just delete its line.
# ---------------------------------------------------------------------------
EXCLUDE_KEYS = {
    # Server- or runtime-assigned identity (assigned by the collector at
    # connect time; not customer-tunable).
    "agent_run_id",
    "account_id",
    "application_id",
    "primary_application_id",
    "trusted_account_ids",
    "trusted_account_key",
    "encoding_key",
    "request_headers_map",
    "feature_flag",  # internal toggles, not part of the public surface
    # Browser / RUM internals -- server-pushed, not customer-tunable.
    "beacon",
    "browser_key",
    "error_beacon",
    "episodes_url",
    "js_agent_file",
    "js_agent_loader",
    # Other server-set / non-Settings-class objects on the tree.
    "entity_guid",  # server-assigned at connect
    "attribute_filter",  # AttributeFilter instance, not a config value
    # Internal-only QA / debug toggles. Surfacing these as customer-tunable
    # would let an end user disable TLS validation, suppress harvests, swap
    # logging payloads, etc. -- all of which are support / development
    # affordances, not configuration.
    "developer_mode",
    # Subtree exclusions (use `.*` suffix).
    "cross_application_tracer.*",  # legacy, replaced by distributed tracing
    "process_host.*",  # platform-derived (ip_address, display_name, etc.)
    "debug.*",  # internal QA toggles (cert-validation off-switch, verbose log dumps, etc.)
}


# ---------------------------------------------------------------------------
# Settings tree walk
# ---------------------------------------------------------------------------


def walk_settings(obj, prefix=""):
    """Yield (dotted_path, value) for every leaf in a Settings tree.

    Recurses only into objects whose class name ends with 'Settings' --
    this is the convention in newrelic.core.config and avoids descending
    into incidental objects (AttributeFilter, etc.) that may live on the
    tree as instance attributes.
    """
    for attr in sorted(vars(obj)):
        if attr.startswith("_"):
            continue
        v = getattr(obj, attr)
        full = f"{prefix}.{attr}" if prefix else attr
        if hasattr(v, "__dict__") and type(v).__name__.endswith("Settings"):
            yield from walk_settings(v, full)
        else:
            yield full, v


def is_excluded(path, exclude_keys):
    """True if `path` matches an exact entry in `exclude_keys`, OR matches
    any `prefix.*` entry by being equal to `prefix` or starting with
    `prefix.`.
    """
    if path in exclude_keys:
        return True
    for entry in exclude_keys:
        if entry.endswith(".*"):
            prefix = entry[:-2]
            if path == prefix or path.startswith(prefix + "."):
                return True
    return False


# ---------------------------------------------------------------------------
# Type inference -- map a live Python value to a JSON Schema type.
# ---------------------------------------------------------------------------


def infer_type(value):
    """Map a live Python value to a JSON Schema type string.

    Returns None for `None` (caller must consult TYPE_OVERRIDES).
    """
    # bool MUST be checked before int -- bool is a subclass of int in Python.
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (list, set, tuple)):
        return "array"
    if isinstance(value, dict):
        return "object"
    return None  # None / unknown


def default_for(value, json_type):
    """Convert a live Python value into a JSON-serializable default.

    Sets become sorted lists (sets unordered would produce nondeterministic
    diffs). Tuples become lists. String-only lists also get sorted -- some
    list defaults in newrelic.core.config are derived from `_environ_as_set`
    (e.g. heroku.dyno_name_prefixes_to_shorten = list(set(...))), which
    yields a list whose order varies across Python processes due to hash
    randomization. Sorting makes the generated schema reproducible.
    """
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list) and value and all(isinstance(v, str) for v in value):
        return sorted(value)
    return value


def make_property(path, value, description, enum_overrides, type_overrides):
    """Build a JSON Schema property node for a single setting leaf.

    Resolution order:
      1. type_overrides[path] -- explicit override wins (used for None
         defaults, anyOf shapes, and arrays whose items type cannot be
         inferred).
      2. enum_overrides[path] -- enum forces type=string and translates
         the live default if it is in the enum (or, for log_level, maps
         the int default to its string form).
      3. Auto-anyOf for set values -- any non-explicitly-overridden leaf
         whose live default is a Python `set` gets the
         `anyOf [array, string]` shape used by INI list values.
      4. infer_type(value) -- otherwise.
    """
    if path in type_overrides:
        prop = dict(type_overrides[path])
    elif path in enum_overrides:
        enum_vals = enum_overrides[path]
        prop = {"type": "string", "enum": list(enum_vals)}
        # Map int log levels to their string form; other settings just
        # pass the value through if it's already in the enum.
        default = LOG_LEVEL_INT_TO_STRING.get(value, value) if path == "log_level" else value
        if isinstance(default, str) and default in enum_vals:
            prop["default"] = default
    elif isinstance(value, set):
        # Auto-detect: sets in global_settings() come from
        # _environ_as_set / _environ_as_comma_separated_set, which means
        # the INI form is a delimited string. Emit anyOf so both forms
        # validate. Item type comes from the first element if the set is
        # non-empty; empty sets hit string_array_or_delimited's default
        # of "string".
        item_type = "string"
        if value:
            first = next(iter(value))
            inferred = infer_type(first)
            if inferred:
                item_type = inferred
        prop = string_array_or_delimited(default=sorted(value), item_type=item_type)
    else:
        json_type = infer_type(value)
        if json_type is None:
            return None  # caller will skip; no override and no inferable type
        prop = {"type": json_type}

        if json_type == "array":
            # List-typed leaves that aren't sets -- treat as plain arrays.
            # Sets have already been routed to anyOf above; the only
            # list-typed defaults that remain here are tuples-converted-
            # to-lists or pre-sorted lists in the source.
            if not value:
                prop["items"] = {"type": "string"}
            else:
                first = next(iter(value))
                first_type = infer_type(first)
                prop["items"] = {"type": first_type or "string"}
            prop["default"] = default_for(value, json_type)
        elif json_type == "object":
            prop["additionalProperties"] = True
            if value:
                prop["default"] = value
        else:
            prop["default"] = default_for(value, json_type)

    if description:
        prop["description"] = description.strip()
    return prop


# ---------------------------------------------------------------------------
# INI parsing -- now ONLY for descriptions. We keep the same line-by-line
# scanner because it correctly handles commented-out config blocks (e.g.
# the proxy_* example block in newrelic.ini): the live key=value pair's
# preceding contiguous comment block becomes its description, and a blank
# line clears any pending block so commented-out examples don't bleed.
# ---------------------------------------------------------------------------

# Section header: [newrelic] or [newrelic:production], etc.
_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
# Live key=value line. Keys may contain dots and underscores.
_KEY_RE = re.compile(r"^([a-zA-Z_][\w.\-]*)\s*=\s*(.*)$")


def parse_ini_descriptions(text, section="newrelic"):
    """Return a {dotted_key: description} map for the named section."""
    comments = {}
    pending = []
    current_section = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        stripped = line.strip()

        if stripped == "":
            pending = []
            continue

        m = _SECTION_RE.match(line)
        if m:
            current_section = m.group(1).strip()
            pending = []
            continue

        if line.lstrip().startswith("#"):
            content = line.lstrip()[1:].removeprefix(" ")
            pending.append(content.rstrip())
            continue

        if current_section != section:
            pending = []
            continue

        km = _KEY_RE.match(line)
        if km:
            key = km.group(1)
            if pending:
                comments[key] = " ".join(p.strip() for p in pending if p.strip())
            pending = []
        else:
            pending = []

    return comments


def load_descriptions():
    """Load the {dotted_key: description} map from newrelic.ini, if present.
    Returns an empty dict if the file is missing.
    """
    if not DEFAULT_INI_PATH.exists():
        print(f"  warning: {DEFAULT_INI_PATH} not found; schema will have no descriptions", file=sys.stderr)
        return {}
    return parse_ini_descriptions(DEFAULT_INI_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Schema generation
# ---------------------------------------------------------------------------

LICENSE_KEY_OVERRIDE = {
    "type": "string",
    "description": (
        "New Relic license key associated with your account. "
        "Binds the agent's data to your account in the New Relic UI."
    ),
    "minLength": 1,
}


def build_properties(settings, descriptions, exclude_keys, enum_overrides, type_overrides):
    """Walk the settings tree and build the JSON Schema `properties` map.

    Settings paths that match `exclude_keys` are skipped. Settings whose
    live default is None and have no TYPE_OVERRIDE entry are skipped with
    a warning -- their type cannot be inferred.
    """
    properties = {}
    skipped_none = []
    for path, value in walk_settings(settings):
        if is_excluded(path, exclude_keys):
            continue
        prop = make_property(path, value, descriptions.get(path, ""), enum_overrides, type_overrides)
        if prop is None:
            # license_key gets a hardcoded override applied by the caller
            # after this loop, so its None default isn't a gap -- suppress
            # the warning to avoid implying it's missing from the schema.
            if path != "license_key":
                skipped_none.append(path)
            continue
        properties[path] = prop

    if skipped_none:
        print(
            f"  warning: {len(skipped_none)} settings have None defaults and no "
            f"TYPE_OVERRIDE; they were skipped from the schema:",
            file=sys.stderr,
        )
        for path in skipped_none:
            print(f"    - {path}", file=sys.stderr)

    return properties


def generate_schema(settings, descriptions, exclude_keys=None, enum_overrides=None, type_overrides=None):
    """Generate a JSON Schema dict from a live Settings object."""
    if exclude_keys is None:
        exclude_keys = EXCLUDE_KEYS
    if enum_overrides is None:
        enum_overrides = ENUM_OVERRIDES
    if type_overrides is None:
        type_overrides = TYPE_OVERRIDES

    properties = build_properties(settings, descriptions, exclude_keys, enum_overrides, type_overrides)

    # Hardcoded license_key: the live default is None and we always want
    # this surfaced as a required, non-empty string.
    properties["license_key"] = dict(LICENSE_KEY_OVERRIDE)

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "New Relic Python Agent Configuration",
        "description": (
            "Fleet Control configuration schema for the New Relic Python agent. "
            "Generated from newrelic.core.config.global_settings()."
        ),
        "type": "object",
        "properties": properties,
        "required": ["license_key", "app_name"],
        "additionalProperties": True,
    }


# ---------------------------------------------------------------------------
# Schema merge -- deep-merges a freshly generated schema into the existing
# one so the published schema only ever grows for forward-compatibility
# purposes.
#
# Caveat: the "only ever grows" promise does NOT extend to keys that the
# current generator deliberately excludes via EXCLUDE_KEYS. Filtering those
# out of the old schema before merge guarantees that newly-added exclusions
# actually take effect on the next regeneration, instead of being silently
# resurrected from the prior on-disk schema.
# ---------------------------------------------------------------------------


def filter_excluded(schema, exclude_keys):
    """Return a copy of `schema` with any properties whose dotted path
    matches `exclude_keys` removed. Operates on flat top-level property
    paths only -- mirrors how is_excluded is used in build_properties.
    """
    if not schema or "properties" not in schema:
        return schema
    filtered = dict(schema)
    filtered["properties"] = {k: v for k, v in schema["properties"].items() if not is_excluded(k, exclude_keys)}
    return filtered


def merge_schemas(old_s, new_s):
    if not old_s:
        return new_s

    merged = dict(new_s)

    old_props = old_s.get("properties") or {}
    new_props = new_s.get("properties") or {}
    if old_props or new_props:
        merged["properties"] = merge_properties(old_props, new_props)

    return merged


def merge_properties(old_props, new_props):
    result = {}
    for key, new_val in new_props.items():
        if (
            key in old_props
            and isinstance(new_val, dict)
            and isinstance(old_props[key], dict)
            and new_val.get("type") == "object"
            and old_props[key].get("type") == "object"
        ):
            result[key] = merge_schemas(old_props[key], new_val)
        else:
            result[key] = new_val
    for key, old_val in old_props.items():
        if key not in result:
            result[key] = old_val
    return result


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def load_settings():
    """Import the agent and return a fresh `global_settings()` snapshot.

    The import is deferred to function-call time so test code can stub
    or override what `global_settings` returns by patching the module.
    """
    from newrelic.core.config import global_settings

    return global_settings()


def write_schema(schema, path):
    import json

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")


def validate_meta_schema(schema):
    """Validate against JSON Schema 2020-12. Soft-skip if `jsonschema` is
    not installed; hard-fail (exit 2) only on actual schema invalidity.
    """
    try:
        import jsonschema
    except ImportError:
        print("  meta-schema check skipped: jsonschema not installed", file=sys.stderr)
        return
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        print("Meta-schema validation passed (Draft 2020-12)")
    except jsonschema.exceptions.SchemaError as e:
        print("Meta-schema validation FAILED:", file=sys.stderr)
        print(f"  {e.message}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"  meta-schema check skipped: {type(e).__name__}: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate Fleet Control config schema. Writes config.json only; "
        "version bumps live in bump-schema-version.py."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the schema without comparing to the existing one. Always exits 0.",
    )
    args = parser.parse_args(argv)

    print("Reading: newrelic.core.config.global_settings()")
    settings = load_settings()
    descriptions = load_descriptions()
    print(f"  {len(descriptions)} descriptions loaded from {DEFAULT_INI_PATH.name}")

    generated = generate_schema(settings, descriptions)

    old_schema = {} if args.force else load_existing(SCHEMA_PATH)
    # Drop excluded paths from the prior schema before merging so newly-added
    # entries in EXCLUDE_KEYS take effect instead of being preserved by the
    # "schema only ever grows" merge. Keep the original around so the diff
    # classifier can still surface those removals to reviewers.
    filtered_old_schema = filter_excluded(old_schema, EXCLUDE_KEYS)
    new_schema = merge_schemas(filtered_old_schema, generated)

    validate_meta_schema(new_schema)

    write_schema(new_schema, SCHEMA_PATH)
    print(f"Wrote:   {SCHEMA_PATH}")

    if args.force:
        print("\n--force: schema written without diff comparison.")
        return 0

    if not old_schema:
        print("\nFirst run -- schema created.")
        return 0

    changes = classify_changes(old_schema, new_schema)
    print_changes(changes)

    return 1 if changes else 0


if __name__ == "__main__":
    sys.exit(main())
