# Agent Config Schema Generator

This directory contains the Python scripts that walk
`newrelic.core.config.global_settings()` to produce a JSON Schema
(`../schemas/config.json`) and to manage version bumps in
`../configurationDefinitions.yml` for Fleet Control.

## Files

| File | Description |
|------|-------------|
| `generate-schema.py` | Per-push regenerator. Reads the live agent settings tree, writes `config.json`. Never touches `configurationDefinitions.yml`. |
| `bump-schema-version.py` | Release-time version bumper. Compares the schema at a prior git ref to the current schema and writes a new version into `configurationDefinitions.yml`. |
| `schema_diff.py` | Shared library (no `main`). Holds the diff classification (`classify_changes`), bump arithmetic (`recommend_bump`, `apply_bump`, `bump_version`), and schema loading (`load_existing`). Imported by both top-level scripts. |
| `dump-settings.py` | Dev helper. Lists every leaf in `global_settings()` and how it appears in the generated schema (or why it was excluded). Not part of the workflow. |
| `tests/test_generate_schema.py` | Tests for the generator (`infer_type`, `make_property`, `build_properties`, `generate_schema`, anyOf helpers). |
| `tests/test_schema_diff.py` | Tests for the shared library (`classify_changes`, `recommend_bump`, `apply_bump`, `bump_version`, `load_existing`). |
| `tests/test_bump_schema_version.py` | Tests for the bump script (parsing helpers + main bootstrap/happy paths with mocked `git_show`). |
| `../schemas/config.json` | Generated JSON Schema (Draft 2020-12). |
| `../configurationDefinitions.yml` | Fleet Control metadata, including the schema's semver version. Bumped only at release time. |

## How the generator works

The agent's live settings tree (`newrelic.core.config.global_settings()`)
is the source of truth for which keys exist, their types, and their
defaults. `newrelic/newrelic.ini` is consulted only for descriptions
(comments adjacent to `key = value` lines in the `[newrelic]` section).

`generate-schema.py`:

1. Imports `newrelic.core.config` and walks every leaf whose containing
   class name ends in `Settings`.
2. Loads descriptions from `newrelic/newrelic.ini`.
3. For every leaf, applies (in order): `TYPE_OVERRIDES`, `ENUM_OVERRIDES`,
   set-typed auto-anyOf, type inference from the live value.
4. Skips leaves whose path matches `EXCLUDE_KEYS` (exact or `prefix.*`).
5. Validates the result against the JSON Schema Draft 2020-12 meta-schema.
6. Deep-merges the freshly generated schema into the existing on-disk
   `config.json` so the published schema only ever grows.
7. Writes `config.json` and prints a classified diff summary.

The generator does **not** touch `configurationDefinitions.yml` --
version bumps live in the next section.

## How versioning works

Schema regeneration runs **per push** on feature branches via
`.github/workflows/fleet-control-schema.yml`. It writes `config.json`
and nothing else. Reviewers see schema diffs in PRs.

Version bumps run **manually before each release** via
`.github/workflows/fleet-control-schema-bump.yml`, which is
`workflow_dispatch`-only. The bump workflow:

1. Finds the latest `v*` tag on `main` (overridable via the
   `since_ref` workflow input).
2. Reads the historical `configurationDefinitions.yml` from that tag --
   the version stored there is the **starter version** for the bump.
3. Reads the historical schema using the path declared in that file's
   `schema:` field.
4. Compares the historical schema to the current `config.json` on `main`,
   classifies the cumulative diff, and applies the recommended bump kind
   (major/minor/patch).
5. Opens a PR titled `chore: bump agent config schema version` for team
   review.

If the latest release tag predates the schema (the `.fleetControl/`
directory or the `schema:` field in `configurationDefinitions.yml`),
`bump-schema-version.py` exits 0 with a bootstrap message and no PR
is opened. The first release that includes the schema ships at whatever
version is currently in `configurationDefinitions.yml`.

### Release ordering -- run the bump workflow before cutting the tag

The bump PR is a separate review/merge step from the agent's `vX.Y.Z`
release tag. Run the workflows in this order:

1. Trigger `Fleet Control Config Schema Bump` (manual `workflow_dispatch`).
2. Wait for the PR to open (or the workflow to report that no bump is needed).
3. Review and merge the bump PR if one was opened.
4. Cut the GitHub Release from the post-merge `main`.

If the release tag is cut before the bump PR merges, the tag's
`configurationDefinitions.yml` will still say the pre-bump version,
even though the schema itself (`config.json`) at that tag reflects the
new keys. Consumers see a mismatch. The next release will compute its
bump correctly from this tag's metadata, but the tag itself ships
mismatched.

## Quick start

Regenerate the schema, run tests, and surface excluded settings in one
command:

```bash
tox -e fleet-schema
```

This runs the unit tests, regenerates `.fleetControl/schemas/config.json`
(deep-merged into the existing schema), prints the classified diff, and
dumps any settings that didn't make it into the schema. Exit code matches
`generate-schema.py`: `0` if no schema changes, `1` if the schema changed
(commit before pushing), `2` on a hard failure.

> **Run with a clean shell.** `import newrelic.core.config` reads
> `NEW_RELIC_*` env vars at import time and bakes them into the live
> defaults. The tox env unsets them defensively; if you invoke the
> generator directly, do the same (`env -i PATH="$PATH" HOME="$HOME"
> python3 ...`).

### Lower-level commands

If you want to invoke a single step directly without going through tox:

```bash
# Regenerate schema only (from repo root)
python3 .fleetControl/schemaGeneration/generate-schema.py

# Force-regenerate without comparing to existing on-disk schema
python3 .fleetControl/schemaGeneration/generate-schema.py --force

# Dry-run a release-time bump against a tag
python3 .fleetControl/schemaGeneration/bump-schema-version.py --since=v10.21.0

# Apply a release-time bump (writes configurationDefinitions.yml)
python3 .fleetControl/schemaGeneration/bump-schema-version.py --since=v10.21.0 --ci

# Dump every live setting alongside how it appears in the schema
python3 .fleetControl/schemaGeneration/dump-settings.py

# Filter the dump to settings missing from the schema
python3 .fleetControl/schemaGeneration/dump-settings.py --missing
```

## Adding new configuration keys

When new settings land in `newrelic/core/config.py`, the generator
picks them up automatically on the next push -- no manual schema edit
needed for the common case.

**Special handling is required for certain key types**, configured via
override maps in `generate-schema.py`.

### Array-or-string keys (`_environ_as_set`-backed)

Many agent config keys accept either a structured array OR a delimited
string (the INI form):

```ini
attributes.include = request.parameters.* response.headers.content-type
```

These keys are parsed via `_environ_as_set` /
`_environ_as_comma_separated_set` in `newrelic/core/config.py`. For the
JSON Schema to correctly represent both forms, set-typed live values
auto-detect into the right shape -- you don't need a per-key entry
unless the live default is empty (in which case `set` vs. `list` cannot
be distinguished from the value alone). Empty defaults need an explicit
override:

```python
'new_feature.include': string_array_or_delimited(default=[]),
'new_feature.exclude': string_array_or_delimited(default=[]),
```

The auto-detection covers the long tail (the seven `*.attributes.*`
subtrees, `opentelemetry.traces.*`, etc.) because their live values
arrive as Python `set` objects.

### Status code keys

Keys that accept integers, arrays of integers, or range strings (e.g.,
`"100-102 200-208 226 300-308 404"`) should use:

```python
'error_collector.new_status_codes': status_code_array_or_range(),
'error_collector.new_status_codes_with_default': status_code_array_or_range(default=[404]),
```

### Enum keys

Keys with a fixed set of allowed values should be added to `ENUM_OVERRIDES`:

```python
ENUM_OVERRIDES = {
    'new_feature.mode': ['option1', 'option2', 'option3'],
}
```

### None-defaulted leaves

Settings whose live default is `None` cannot have their type inferred,
so they're skipped from the schema with a warning. To surface them, add
an explicit type in `TYPE_OVERRIDES`:

```python
'proxy_user': {'type': 'string'},
```

## Excluding keys

Add keys to `EXCLUDE_KEYS` to drop them from the schema:

```python
EXCLUDE_KEYS = {
    'agent_run_id',                # exact match
    'cross_application_tracer.*',  # subtree exclusion
}
```

The `.*` suffix matches both the prefix itself and any descendant.

## Checklist for new config keys

1. Add the setting to `newrelic/core/config.py` as you would any other.
2. **Run the generator locally** (`python3 .fleetControl/schemaGeneration/generate-schema.py`) to pick up the new key.
3. **Check the inferred type** in the generated schema.
4. **If the live default is `None`** → add an entry to `TYPE_OVERRIDES`.
5. **If the key uses `_environ_as_set` and the default is empty** → add to `TYPE_OVERRIDES` with `string_array_or_delimited()`.
6. **If the key has enum values** → add to `ENUM_OVERRIDES`.
7. **If the key should be hidden** → add to `EXCLUDE_KEYS`.
8. **Run the generator again**; verify the schema entry looks correct.
9. **Run the tests** (`python3 -m unittest discover .fleetControl/schemaGeneration/tests`).
10. The next release will pick up the bump when the maintainer runs the
    bump workflow as part of release prep.

## CLI options

### Generator CLI (`generate-schema.py`)

| Option | Description |
|--------|-------------|
| `--force` | Overwrite the schema without comparing to the existing one. Always exits 0. |

### Bumper CLI (`bump-schema-version.py`)

| Option | Description |
|--------|-------------|
| `--since=<ref>` | Required. Compare the current schema to the schema at `<ref>` and recommend a bump. |
| `--ci` | Write the bumped version to `configurationDefinitions.yml`. Without this, the script just prints the recommendation. |

## Exit codes

### Generator exit codes (`generate-schema.py`)

| Code | Meaning |
|------|---------|
| 0 | No schema changes (or first run, or `--force` mode). |
| 1 | Schema regenerated and on-disk differed (CI should commit). |
| 2 | Generator failure (invalid schema, malformed inputs). |

### Bumper exit codes (`bump-schema-version.py`)

| Code | Meaning |
|------|---------|
| 0 | No bump needed (no schema diff, or bootstrap case where `<ref>` predates the schema). |
| 1 | Bump applied (`--ci`) or recommended (without `--ci`). |
| 2 | Bump failure (uncaught exception, missing args, malformed historical inputs). |

## Version bumping rules

`bump-schema-version.py` classifies each schema change and the bump
kind is the highest severity across all changes:

| Change type | Severity | Bump |
|-------------|----------|------|
| Property removed | Breaking | Major |
| Type changed | Breaking | Major |
| Enum value removed | Breaking | Major |
| Enum newly introduced | Breaking | Major |
| Required field added | Breaking | Major |
| `additionalProperties` tightened (true → false) | Breaking | Major |
| Property added | Additive | Minor |
| Enum value added | Additive | Minor |
| Enum removed entirely | Additive | Minor |
| Required field removed | Additive | Minor |
| Default changed | Additive | Minor |
| `additionalProperties` loosened (false → true) | Additive | Minor |
| Description changed | Cosmetic | Patch |

## Running the tests

```bash
# All schema-generation tests in one shot
python3 -m unittest discover .fleetControl/schemaGeneration/tests

# Individual files
python3 -m unittest .fleetControl.schemaGeneration.tests.test_generate_schema
python3 -m unittest .fleetControl.schemaGeneration.tests.test_schema_diff
python3 -m unittest .fleetControl.schemaGeneration.tests.test_bump_schema_version
```
