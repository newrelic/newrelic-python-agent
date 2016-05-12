# Jenkins

https://python-agent-build.pdx.vm.datanerd.us

## Jenkins DSL
All tests are written using [Jenkins DSL](https://wiki.jenkins-ci.org/display/JENKINS/Job+DSL+Plugin) which allows us to save our job configurations as groovy files here in our repo. The [more-jenkins-dsl](https://source.datanerd.us/commune/more-jenkins-dsl) is used as a starting point.

## Existing Jobs
Jobs are grouped into three views:

### Python Agent Deploy
**deploy-to-pypi:** On demand job. Will upload the source distribution package to PyPI. By default, it will upload to Test PyPi.

**build-and-archive-package:** On demand job. Will build the source distribution package and upload it to Artifactory.


### Python Agent Tests
**PYTHON-AGENT-DOCKER-TESTS:** Multijob run hourly on cron. Will run all tests currently configured in the `jenkins/test-pipeline-config.json` file. (See below for more details on adding new tests) The tests will all run in parallel in EC2 worker nodes.

**python-agent-test-*:** These tests are configured in the `jenkins/test-pipeline-config.json` file and are the subjobs to the PYTHON-AGENT-DOCKER-TESTS multijob. They will first pull packnsend images from dogestry. If the image was updated, any existing running containers that use that image will be stopped. Finally, it will make sure that all packnsend containers are running. It will *not* restart a container if the image has not changed.

**python-agent-oldstyle-tests-*:** Run on push to master/deploy and on all pull requests. They run `./build.sh` then `./tests.sh`.

### Python Agent Tools
**python-agent-tools-dsl-seed:** Job to run on every push to the develop branch. Will rebuild all jenkins jobs from DSL. Any files in the *jenkins* directory with extension `.groovy` will be read and sourced.

**python-agent-tools-Packnsend-Build-and-Push:** On demand job. Will build all packnsend docker images (as currently found in the develop branch) then push them to dogestry.


## EC2 Nodes
EC2 nodes are provisioned on demand by Jenkins. When there are waiting jobs and no available node, Jenkins will first try to power on any offline nodes, then if none are available, it will create new ones. Jenkins will power off nodes when they have gone idle. This is a simple power off, not a deprovision. Thus, any docker containers will be stopped, but no images will be removed.

The AWS keys needed to push and pull from dogestry along with the dogestry binary are pre-loaded onto the nodes. For this reason, it is advised that if you want to make changes to a packnsend docker image, do so from jenkins rather than a laptop.

## Adding New Docker Tests

Adding new `tox` style tests is now super easy! Simply open the `jenkins/test-pipeline-config.json` file and add a new entry. When the change is pushed to develop, the python-agent-tools-dsl-seed job will create and configure the test.

```json
{
  "packnsendTests": {
    "phase": [

      {
        "name": "<YOUR NEW TEST NAME>",
        "description": "<A DESCRIPTION FOR YOUR NEW TEST>",
        "commands": [
          "<COMMAND 1>",
          "<COMMAND 2>",
          "<COMMAND 3>"
        ]
      }

    ]
  }
}
```

It is possible to disable a test by adding `"disable": "true"`.
