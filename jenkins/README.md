# Jenkins

https://python-agent-build.pdx.vm.datanerd.us

## Jenkins DSL
All tests are written using [Jenkins DSL](https://wiki.jenkins-ci.org/display/JENKINS/Job+DSL+Plugin) which allows us to save our job configurations as groovy files here in our repo. The [more-jenkins-dsl](https://source.datanerd.us/commune/more-jenkins-dsl) is used as a starting point.

## Existing Jobs
Jobs are grouped into three views:

### Python Agent Deploy
**deploy-to-pypi:** On demand job. Will upload the source distribution package to PyPI. By default, it will upload to Test PyPi.

**deploy-to-s3:** On demand job. Will upload the source distribution package to our S3 bucket. By default, it will upload to the "testing" directory.

**build-and-archive-package:** On demand job. Will build the source distribution package and upload it to Artifactory.

### Python Agent Tests
**\_PYTHON-AGENT-DOCKER-TESTS\_:** Multijob run hourly on cron. Will run all tests currently configured in the `jenkins/test-pipeline-config.json` file. (See below for more details on adding new tests) The tests will all run in parallel in EC2 worker nodes.

**\*__docker-test:** These tests are configured in the `jenkins/test-pipeline-config.json` file and are the subjobs to the PYTHON-AGENT-DOCKER-TESTS multijob. They will pull packnsend images from the New Relic docker repository (cf-registry.nr-ops.net) then start all containers. If a container is already running, the action is a noop. The consequence of this is if an image changes in the docker repository, the jobs will not pick up this change automatically (see the Reset Nodes job).

**oldstyle-tests-*:** Run on push to master/deploy and on all pull requests. They run `./build.sh` then `./tests.sh`.

### Python Agent Tools
**python-agent-tools-dsl-seed:** Job to run on every push to the develop branch. Will rebuild all jenkins jobs from DSL. Any files in the *jenkins* directory with extension `.groovy` will be read and sourced.

**python-agent-tools-Packnsend-Build-and-Push:** On demand job. Will build all packnsend docker images (as currently found in the develop branch) then push them to the New Relic docker repository (cf-registry.nr-ops.net). Any pre-existing EC2 nodes will not start using these images until the images are restarted (see the Reset Nodes job). New EC2 nodes will automatically use these new images.

**python-agent-tools-Reset-Nodes:** On demand job. Should be run after a change is made to a packnsend image. Will run on each EC2 node, powering the node on first if necessary. Executes two commands: `packnsend pull` then `packnsend restart`. Requires two parameters: 1) *NODE_NAME* is the label of the nodes to run the jobs on, do not change this from "py-ec2-linux", and 2) *GIT_BRANCH* is the branch the job will use to run the packnsend commands.

## EC2 Nodes
EC2 nodes are provisioned on demand by Jenkins. When there are waiting jobs and no available node, Jenkins will first try to power on any offline nodes, then if none are available, it will create new ones. Jenkins will power off nodes when they have gone idle. This is a simple power off, not a deprovision. Thus, any docker containers will be stopped, but no images will be removed.

The nodes run Docker version 1.12 that is installed when the node is first created. This is done to prevent errors in removing containers when using `packnsend`, `btrfs`, and earlier versions of docker (see https://newrelic.atlassian.net/browse/PYTHON-2038). Configuration for the nodes is owned by the tools team and is detailed in the [tools/jenkins-admin-tools](https://source.datanerd.us/tools/jenkins-admin-tools/blob/master/config/hosts/python-agent-build.pdx.vm.datanerd.us.yaml) repo.

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

## Jenkins Plugins
We have installed the following plugins on our JaaS instance:
+ envinject
+ jenkins-multijob-plugin
+ email-ext
+ nodelabelparameter
+ build-blocker-plugin
