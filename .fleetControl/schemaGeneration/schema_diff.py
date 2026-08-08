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
Schema diff + version bump helpers shared between generate-schema.py and
bump-schema-version.py.

Pure functions for classifying schema changes, recommending a semver
bump, and rewriting the version line in configurationDefinitions.yml.

No side effects beyond bump_version (which writes a YAML file when its
write= flag is true).
"""

import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Schema I/O
# ---------------------------------------------------------------------------


def load_existing(path):
    """Load a JSON Schema from disk, returning {} if absent or unreadable.

    Used to diff a freshly generated schema against the on-disk one. A
    malformed file is treated as "no prior schema" rather than a hard
    failure -- the caller will overwrite it.
    """
    if not Path(path).exists():
        return {}
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------------------
# Schema diff classification
# ---------------------------------------------------------------------------


def render_change(c):
    """Format a single change record as a one-line `+/-/~ path: detail` string."""
    kind = c["kind"]
    sym = "+" if kind == "added" else ("-" if kind == "removed" else "~")
    detail = c.get("detail") or ""
    path = c["path"]
    return f"{sym} {path}: {detail}" if detail else f"{sym} {path}"


def classify_changes(old_s, new_s, path=""):
    """Walk two schemas in parallel, returning a list of change records.

    Each change record has keys: path, kind, severity (breaking/additive/
    cosmetic), detail. The caller turns severities into bump kinds via
    recommend_bump.
    """
    changes = []

    old_req = set(old_s.get("required") or [])
    new_req = set(new_s.get("required") or [])
    changes.extend(
        {
            "path": f"{path}.{k}" if path else k,
            "kind": "required_added",
            "severity": "breaking",
            "detail": "now required",
        }
        for k in sorted(new_req - old_req)
    )
    changes.extend(
        {
            "path": f"{path}.{k}" if path else k,
            "kind": "required_removed",
            "severity": "additive",
            "detail": "no longer required",
        }
        for k in sorted(old_req - new_req)
    )

    old_ap = old_s.get("additionalProperties", True)
    new_ap = new_s.get("additionalProperties", True)
    if old_ap is True and new_ap is False:
        changes.append(
            {
                "path": path or "<root>",
                "kind": "additional_properties_tightened",
                "severity": "breaking",
                "detail": "additionalProperties: true -> false",
            }
        )
    elif old_ap is False and new_ap is True:
        changes.append(
            {
                "path": path or "<root>",
                "kind": "additional_properties_loosened",
                "severity": "additive",
                "detail": "additionalProperties: false -> true",
            }
        )

    old_props = old_s.get("properties") or {}
    new_props = new_s.get("properties") or {}
    for key in sorted(set(old_props.keys()) | set(new_props.keys())):
        child_path = f"{path}.{key}" if path else key
        if key not in old_props:
            changes.append({"path": child_path, "kind": "added", "severity": "additive", "detail": "new property"})
        elif key not in new_props:
            changes.append(
                {"path": child_path, "kind": "removed", "severity": "breaking", "detail": "property removed"}
            )
        else:
            op = old_props[key]
            np = new_props[key]
            if op.get("type") == "object" and np.get("type") == "object":
                changes.extend(classify_changes(op, np, child_path))
            else:
                changes.extend(classify_leaf(op, np, child_path))
    return changes


def classify_leaf(op, np, path):
    """Compare two leaf property nodes and return a list of change records."""
    changes = []

    if op.get("type") != np.get("type"):
        changes.append(
            {
                "path": path,
                "kind": "type_changed",
                "severity": "breaking",
                "detail": f"type {op.get('type')} -> {np.get('type')}",
            }
        )

    oe = op.get("enum")
    ne = np.get("enum")
    if oe is None and ne is not None:
        changes.append(
            {
                "path": path,
                "kind": "enum_introduced",
                "severity": "breaking",
                "detail": f"newly constrained to enum {ne}",
            }
        )
    elif oe is not None and ne is None:
        changes.append(
            {"path": path, "kind": "enum_removed_entirely", "severity": "additive", "detail": "enum constraint removed"}
        )
    elif oe and ne and set(oe) != set(ne):
        changes.extend(
            {"path": path, "kind": "enum_value_removed", "severity": "breaking", "detail": f"enum value '{v}' removed"}
            for v in sorted(set(oe) - set(ne))
        )
        changes.extend(
            {"path": path, "kind": "enum_value_added", "severity": "additive", "detail": f"enum value '{v}' added"}
            for v in sorted(set(ne) - set(oe))
        )

    if op.get("default") != np.get("default"):
        changes.append(
            {
                "path": path,
                "kind": "default_changed",
                "severity": "additive",
                "detail": f"default {op.get('default')} -> {np.get('default')}",
            }
        )

    if op.get("description") != np.get("description"):
        changes.append(
            {"path": path, "kind": "description_changed", "severity": "cosmetic", "detail": "description updated"}
        )

    return changes


# ---------------------------------------------------------------------------
# Semver bump
# ---------------------------------------------------------------------------


def recommend_bump(changes):
    """Reduce a list of change records to a single bump kind.

    Returns the highest-severity bump implied by any change: a single
    breaking change forces 'major'; otherwise any additive change forces
    'minor'; otherwise any cosmetic change forces 'patch'; otherwise 'none'.
    """
    if any(c.get("severity") == "breaking" for c in changes):
        return "major"
    if any(c.get("severity") == "additive" for c in changes):
        return "minor"
    if any(c.get("severity") == "cosmetic" for c in changes):
        return "patch"
    return "none"


def apply_bump(version, bump):
    """Return a new MAJOR.MINOR.PATCH string after applying the given bump kind."""
    if bump == "none":
        return version
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"version '{version}' is not semver MAJOR.MINOR.PATCH")
    major, minor, patch = (int(p) for p in parts)
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown bump kind '{bump}'")


_VERSION_LINE_RE = re.compile(r"(?m)^(\s*version:\s*)(\S+)(\s*)$")


def bump_version(yaml_path, bump, write):
    """Read the single `version:` line from yaml_path, apply the bump, and
    optionally write the result back. Returns (old_version, new_version).

    Raises if the file does not contain exactly one `version:` line --
    catches ambiguity caused by future template additions to
    configurationDefinitions.yml.
    """
    text = Path(yaml_path).read_text(encoding="utf-8")
    matches = list(_VERSION_LINE_RE.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(f"{yaml_path}: expected exactly 1 'version:' line, found {len(matches)}")
    old_version = matches[0].group(2)
    new_version = apply_bump(old_version, bump)
    if write and new_version != old_version:
        new_text = _VERSION_LINE_RE.sub(lambda m: f"{m.group(1)}{new_version}{m.group(3)}", text)
        Path(yaml_path).write_text(new_text, encoding="utf-8")
    return old_version, new_version


def print_changes(changes, *, header="Schema changes"):
    """Pretty-print a classified change list grouped by severity.

    Lifted out of generate-schema.py's main so bump-schema-version.py can
    reuse the same formatting.
    """
    if not changes:
        print("\nNo schema changes.")
        return

    breaking = [c for c in changes if c["severity"] == "breaking"]
    additive = [c for c in changes if c["severity"] == "additive"]
    cosmetic = [c for c in changes if c["severity"] == "cosmetic"]
    print(f"\n{header} ({len(changes)}):")
    if breaking:
        print(f"  BREAKING ({len(breaking)}):")
        for c in breaking:
            print(f"    {render_change(c)}")
    if additive:
        print(f"  ADDITIVE ({len(additive)}):")
        for c in additive:
            print(f"    {render_change(c)}")
    if cosmetic:
        print(f"  COSMETIC ({len(cosmetic)}):")
        for c in cosmetic:
            print(f"    {render_change(c)}")
