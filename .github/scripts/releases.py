import os

from github import Github

# How to use this script:
# Set the following env vars:
#   * GH_RELEASE_TOKEN
#   * LAMBDA_RUNTIME (optional)
#   * INITCONTAINER_RUNTIME (optional)
#   * AGENT_VERSION
#   * DRY_RUN (optional) set to 1 to run the flow without creating the release tag.
#
# Lambda runtime options:
# nodejs
# python
# ruby
# dotnet
#
# Initcontainer runtime options:
# nodejs
# python
# ruby
# java
# dotnet

DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("on", "true", "1")


def run_container_releases():
    gh = Github(os.environ["GH_RELEASE_TOKEN"])
    lambda_runtime = os.environ.get("LAMBDA_RUNTIME")
    initcontainer_runtime = os.environ.get("INITCONTAINER_RUNTIME")
    latest_version = os.environ["AGENT_VERSION"]

    lambda_repo = gh.get_repo("newrelic/newrelic-lambda-layers")
    initcontainer_repo = gh.get_repo("newrelic/newrelic-agent-init-container")

    if lambda_runtime:
        create_release(lambda_repo, lambda_runtime, latest_version)
    if initcontainer_runtime:
        create_release(initcontainer_repo, initcontainer_runtime, latest_version)


def create_release(repo, runtime, latest_version):
    tag_name = f"{latest_version}.0_{runtime}"
    release_name = f"New Relic {runtime} Agent {latest_version}.0"

    print(f'{repo.full_name} - Releasing "{release_name}" with tag "{tag_name}"')

    if not DRY_RUN:
        git_release = repo.create_git_release(tag_name, release_name, "")
        print(git_release.__repr__())


if __name__ == "__main__":
    run_container_releases()
