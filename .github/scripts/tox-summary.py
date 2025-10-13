#!/usr/bin/env python
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

import json
import os
import re
from pathlib import Path
from textwrap import dedent

REPO_DIR = Path(__file__).parent.parent.parent
TOX_DIR = REPO_DIR / ".tox"
GITHUB_SUMMARY = Path(os.environ.get("GITHUB_STEP_SUMMARY", TOX_DIR / "summary.md"))
RESULTS_FILE_RE = re.compile(
    r"(?P<job_name>[a-zA-Z0-9_-]+)-(?P<job_num>\d+)-(?P<run_id>[a-zA-Z0-9]+)-(?P<job_id>[a-zA-Z0-9_-]+)-results.json"
)

GITHUB_SERVER_URL = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "newrelic/newrelic-python-agent")

TABLE_HEADER = """
# Tox Results Summary

| Environment | Status | Duration (s) | Setup Duration (s) | Test Duration (s) | Runner |
|-------------|--------|--------------|--------------------|-------------------|--------|
"""
TABLE_HEADER = dedent(TABLE_HEADER).strip()


def main():
    results = {}
    # Search both repo and .tox dirs
    filepaths = list(REPO_DIR.glob("*-results.json")) + list(TOX_DIR.glob("*-results.json"))
    for filepath in filepaths:
        with filepath.open() as f:
            # Load the JSON data
            data = json.load(f)
            envs = data.get("testenvs", ())

            # Extract GitHub info from filename
            match = RESULTS_FILE_RE.match(filepath.name)
            if match:
                runner_link = f"{GITHUB_SERVER_URL}/{GITHUB_REPOSITORY}/actions/runs/{match.group('run_id')}/job/{match.group('job_id')}"
                runner = f"[{match.group('job_name')} ({match.group('job_num')})]({runner_link})"
            else:
                runner = "N/A"

            # Aggregate any non-empty results
            sub_results = {k: v for k, v in envs.items() if v and k != ".pkg"}
            for result in sub_results.values():
                result["runner"] = runner
            results.update(sub_results)

    if not results:
        raise RuntimeError("No tox results found.")

    with GITHUB_SUMMARY.open("w") as output_fp:
        summary = summarize_results(results)
        # Print table header
        print(TABLE_HEADER, file=output_fp)

        for result in summary:
            line = "| {env_name} | {status} | {duration} | {setup_duration} | {test_duration} | {runner} |".format(
                **result
            )
            print(line, file=output_fp)


def summarize_results(results):
    summary = []
    for env, result in results.items():
        duration = result["result"].get("duration", 0)
        duration = f"{duration:.2f}" if duration >= 0 else "N/A"
        status = "OK ✅" if result["result"]["success"] else "FAIL ❌"
        runner = result.get("runner", "N/A")

        # Sum up setup and test durations from individual commands
        setup_duration = 0
        for cmd in result.get("setup", ()):
            setup_duration += cmd.get("elapsed", 0)
        setup_duration = f"{setup_duration:.2f}" if setup_duration >= 0 else "N/A"

        test_duration = 0
        for cmd in result.get("test", ()):
            test_duration += cmd.get("elapsed", 0)
        test_duration = f"{test_duration:.2f}" if test_duration >= 0 else "N/A"

        summary.append(
            {
                "env_name": env,
                "status": status,
                "duration": duration,
                "setup_duration": setup_duration,
                "test_duration": test_duration,
                "runner": runner,
            }
        )

    return sorted(summary, key=lambda result: (1 if "OK" in result["status"] else 0, result["env_name"]))


if __name__ == "__main__":
    main()
