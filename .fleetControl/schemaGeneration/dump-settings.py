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
Dev helper: dump every leaf in the agent's live settings tree alongside
how it shows up in .fleetControl/schemas/config.json.

This isn't part of the schema-generation workflow -- it's a debugging
tool so you can spot-check what made it into the schema and why
something didn't.

Run from the repo root:

    python3 .fleetControl/schemaGeneration/dump-settings.py

Each row is one setting in the agent's `global_settings()` tree:

    PATH                                LIVE                  SCHEMA
    ----                                ----                  ------
    account_id                          NoneType              -- EXCLUDED (server-set)
    app_name                            str='Python App...'   string, default='Python Application'  REQ
    license_key                         NoneType              string, minLength=1 [hardcoded]  REQ
    log_level                           int=20                string, enum, default='info' [enum override]

Filters:
    --missing       Only show settings that did NOT make it into the schema.
    --grep PATTERN  Only show paths matching the substring (case-insensitive).
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FLEET_CONTROL_DIR = SCRIPT_DIR.parent
REPO_ROOT = FLEET_CONTROL_DIR.parent
SCHEMA_PATH = FLEET_CONTROL_DIR / "schemas" / "config.json"

# Make the agent importable.
sys.path.insert(0, str(REPO_ROOT))

# Load generate-schema.py so we can reuse its walk/exclude logic and the
# override tables. The hyphen in the filename means we can't just import
# it as a module -- importlib.util is the standard workaround.
_GEN_PATH = SCRIPT_DIR / "generate-schema.py"
_spec = importlib.util.spec_from_file_location("gen", _GEN_PATH)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def _truncate(s, n=24):
    s = str(s)
    return s if len(s) <= n else s[: n - 3] + "..."


def _live_summary(value):
    """Compact "type=value" string for the live default column."""
    t = type(value).__name__
    if value is None:
        return t
    if isinstance(value, str):
        return f"{t}={_truncate(repr(value))}"
    if isinstance(value, (list, set, tuple, dict)):
        return f"{t}={_truncate(repr(value))}"
    return f"{t}={value!r}"


def _schema_summary(prop):
    """Compact one-line summary of a schema property."""
    parts = []
    t = prop.get("type")
    if t:
        parts.append(t)
    if "anyOf" in prop:
        # Render anyOf as the union of its branch types so the column
        # reads like "anyOf=array(string)|string" rather than collapsing
        # to just the default.
        branches = []
        for branch in prop["anyOf"]:
            bt = branch.get("type", "?")
            if bt == "array":
                inner = branch.get("items", {}).get("type", "?")
                branches.append(f"array({inner})")
            else:
                branches.append(bt)
        parts.append("anyOf=" + "|".join(branches))
    if "enum" in prop:
        parts.append(f"enum={prop['enum']}")
    if "default" in prop:
        parts.append(f"default={prop['default']!r}")
    if "minLength" in prop:
        parts.append(f"minLength={prop['minLength']}")
    if "items" in prop:
        parts.append(f"items={prop['items'].get('type', '?')}")
    return ", ".join(parts) or "(empty)"


def _why_missing(path):
    """Explain why a path didn't end up in the schema."""
    if gen.is_excluded(path, gen.EXCLUDE_KEYS):
        # Find which exclude entry matched, to surface the rationale.
        for entry in gen.EXCLUDE_KEYS:
            if entry == path:
                return f"-- EXCLUDED (matched: {entry})"
            if entry.endswith(".*"):
                prefix = entry[:-2]
                if path == prefix or path.startswith(prefix + "."):
                    return f"-- EXCLUDED (matched: {entry})"
        return "-- EXCLUDED"
    return "-- SKIPPED (None default + no TYPE_OVERRIDE; add one to surface it)"


def _override_note(path, value):
    """Tag schema entries with the override that produced them, if any."""
    if path == "license_key":
        return "[hardcoded]"
    if path in gen.TYPE_OVERRIDES:
        return "[type override]"
    if path in gen.ENUM_OVERRIDES:
        return "[enum override]"
    if path == "log_level":
        return "[log_level int->str]"
    return ""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Dump live settings and how they appear in the generated schema.")
    parser.add_argument(
        "--missing", action="store_true", help="Only show settings absent from the schema (excluded or skipped)."
    )
    parser.add_argument(
        "--grep", metavar="PATTERN", help="Filter to paths containing PATTERN (case-insensitive substring)."
    )
    args = parser.parse_args(argv)

    if not SCHEMA_PATH.exists():
        print(f"error: {SCHEMA_PATH} not found. Run generate-schema.py first.", file=sys.stderr)
        return 2
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema_props = schema.get("properties", {})
    required = set(schema.get("required", []))

    settings = gen.load_settings()

    rows = []
    for path, value in gen.walk_settings(settings):
        in_schema = path in schema_props
        if args.missing and in_schema:
            continue
        if args.grep and args.grep.lower() not in path.lower():
            continue

        live = _live_summary(value)
        if in_schema:
            schema_col = _schema_summary(schema_props[path])
            note = _override_note(path, value)
            if note:
                schema_col = f"{schema_col}  {note}"
        else:
            schema_col = _why_missing(path)

        if path in required:
            schema_col += "  REQ"

        rows.append((path, live, schema_col))

    # license_key gets a hardcoded entry that walk_settings won't yield
    # if its live value is None (it does have a property in the schema
    # though). Surface it explicitly so the dump shows the override row.
    if not args.missing and (not args.grep or args.grep.lower() in "license_key"):
        if "license_key" in schema_props and not any(r[0] == "license_key" for r in rows):
            rows.append(
                (
                    "license_key",
                    "NoneType",
                    f"{_schema_summary(schema_props['license_key'])}  [hardcoded]"
                    + ("  REQ" if "license_key" in required else ""),
                )
            )
            rows.sort()

    if not rows:
        print("(no rows match)")
        return 0

    # Compute column widths from the data, capped to keep the output usable.
    path_w = min(max(len(r[0]) for r in rows), 60)
    live_w = min(max(len(r[1]) for r in rows), 30)

    print(f"{'PATH'.ljust(path_w)}  {'LIVE'.ljust(live_w)}  SCHEMA")
    print(f"{'-' * path_w}  {'-' * live_w}  ------")
    for path, live, schema_col in rows:
        print(f"{path.ljust(path_w)}  {live.ljust(live_w)}  {schema_col}")

    print(f"\n{len(rows)} rows", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
