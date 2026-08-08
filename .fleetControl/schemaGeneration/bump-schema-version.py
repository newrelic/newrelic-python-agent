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
Fleet Control Config Schema Version Bumper -- Python Agent

Reads the schema and metadata at a prior git ref (typically the latest
release tag), diffs against the current schema, classifies the cumulative
changes, and bumps the version in .fleetControl/configurationDefinitions.yml.

Splits the bump responsibility out of generate-schema.py so the
per-push regen workflow doesn't churn the version on every PR.

Run standalone:
  python3 bump-schema-version.py --since=v10.21.0           # dry-run
  python3 bump-schema-version.py --since=v10.21.0 --ci      # apply

Bootstrap case:
  If the given ref predates .fleetControl/ entirely, OR predates the
  `schema:` field in configurationDefinitions.yml, the script exits 0
  with a "bootstrap" message and writes nothing. The first release that
  ships the schema does so at whatever version is currently in
  configurationDefinitions.yml.

Exit codes:
  0 -- no bump needed (no schema diff, or bootstrap case)
  1 -- bump applied (--ci) or recommended (without --ci)
  2 -- hard failure (missing args, malformed inputs, git invocation failed)
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FLEET_CONTROL_DIR = SCRIPT_DIR.parent
REPO_ROOT = FLEET_CONTROL_DIR.parent
SCHEMA_PATH = FLEET_CONTROL_DIR / "schemas" / "config.json"
CONFIG_DEF_PATH = FLEET_CONTROL_DIR / "configurationDefinitions.yml"

# Reuse the diff helpers and version-bump rewriter from the shared module.
sys.path.insert(0, str(SCRIPT_DIR))
from schema_diff import apply_bump, bump_version, classify_changes, print_changes, recommend_bump  # noqa: E402

# Path inside the repo (POSIX, since git uses forward slashes regardless
# of platform). Used when invoking `git show <ref>:<path>`.
CONFIG_DEF_GIT_PATH = ".fleetControl/configurationDefinitions.yml"


def git_show(ref, path):
    """Return file contents at the given ref, or None if the path is
    absent at that ref. Raises on any other git error.
    """
    try:
        # S603/S607: invoking git with a partial path is intentional for a
        # CI tool that runs in environments where git is always on PATH.
        # The `ref` and `path` arguments are validated by git itself and
        # are not used as shell input (no shell=True).
        result = subprocess.run(  # noqa: S603
            ["git", "show", f"{ref}:{path}"],  # noqa: S607
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git executable not found on PATH") from exc

    if result.returncode == 0:
        return result.stdout

    # Distinguish "path didn't exist at this ref" (which is the bootstrap
    # signal we want to handle gracefully) from any other git failure.
    stderr = result.stderr or ""
    if "exists on disk, but not in" in stderr or "does not exist" in stderr or "fatal: path" in stderr:
        return None
    raise RuntimeError(f"git show {ref}:{path} failed: {stderr.strip()}")


# Used to find the schema-relative path inside an unparsed YAML blob. This
# avoids pulling in a YAML dependency for what is a single-line read.
_SCHEMA_LINE_RE = re.compile(r"(?m)^\s*schema:\s*(\S+)\s*$")


def parse_schema_path(yaml_text):
    """Return the path string from the `schema:` line in
    configurationDefinitions.yml, or None if no such line exists.
    """
    m = _SCHEMA_LINE_RE.search(yaml_text)
    return m.group(1) if m else None


def historical_schema_path_in_repo(schema_field):
    """Translate a schema: value (relative to .fleetControl/) into a
    repo-root-relative POSIX path suitable for `git show`.
    """
    schema_field = schema_field.lstrip("./")
    return f".fleetControl/{schema_field}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compute and optionally apply a schema version bump.")
    parser.add_argument(
        "--since", required=True, metavar="REF", help="Git ref (tag or commit) to compare the current schema against."
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Write the bumped version into configurationDefinitions.yml. "
        "Without this flag the script just prints the recommendation.",
    )
    args = parser.parse_args(argv)

    # Step 1: read configurationDefinitions.yml at the historical ref.
    historical_def = git_show(args.since, CONFIG_DEF_GIT_PATH)
    if historical_def is None:
        print(f"Bootstrap: {CONFIG_DEF_GIT_PATH} did not exist at {args.since}. No bump computed.")
        return 0

    # Step 2: extract the historical schema path. If the schema: field
    # was added later, that is also a bootstrap case.
    schema_field = parse_schema_path(historical_def)
    if schema_field is None:
        print(f"Bootstrap: configurationDefinitions.yml at {args.since} has no `schema:` field. No bump computed.")
        return 0

    historical_schema_path = historical_schema_path_in_repo(schema_field)

    # Step 3: read the historical schema. Same bootstrap treatment if the
    # path is absent (e.g. schema: was set but the file hadn't landed
    # yet at the reference).
    historical_schema_text = git_show(args.since, historical_schema_path)
    if historical_schema_text is None:
        print(f"Bootstrap: {historical_schema_path} did not exist at {args.since}. No bump computed.")
        return 0

    try:
        old_schema = json.loads(historical_schema_text)
    except json.JSONDecodeError as e:
        print(f"error: historical schema at {args.since} is not valid JSON: {e}", file=sys.stderr)
        return 2

    # Step 4: read the current schema from disk.
    if not SCHEMA_PATH.exists():
        print(f"error: current schema not found at {SCHEMA_PATH}", file=sys.stderr)
        return 2
    new_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    # Step 5: classify changes and recommend a bump.
    changes = classify_changes(old_schema, new_schema)
    print_changes(changes, header=f"Schema changes since {args.since}")

    bump = recommend_bump(changes)

    # Step 6: apply (or dry-run print) the bump against the *current*
    # configurationDefinitions.yml -- not the historical one. The
    # historical doc is only the source of the diff baseline.
    old_v, new_v = bump_version(CONFIG_DEF_PATH, bump, args.ci)

    if bump == "none":
        print(f"\nNo bump needed (current version: {old_v}).")
        return 0

    if args.ci:
        if new_v == old_v:
            # apply_bump returns the input version when bump == 'none';
            # this branch covers the rare case where bump != 'none' but
            # the version was already at the bumped value (manual edit).
            print(f"\nRecommended bump: {bump}, but {old_v} already reflects it. No write.")
            return 0
        print(f"\nApplied bump: {bump} ({old_v} -> {new_v})")
        print(f"Wrote: {CONFIG_DEF_PATH}")
    else:
        print(f"\nRecommended bump: {bump} ({old_v} -> {apply_bump(old_v, bump)}). Re-run with --ci to apply.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
