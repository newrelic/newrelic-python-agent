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

#### \_INTEGRATION-TESTS-[branch]\_
Multijob to run all tests as defined by `tox.ini` files in the `tests/` directory. The tests will all run in parallel in EC2 worker nodes.

`master` and `develop` tests run on any push to the branch whereas `manual` can be kicked off ad-hoc. `develop` tests will also be run on cron daily.

`pullrequest` tests automatically determine which tests need to be run by inspecting the imports of each test file and seeing if those files changed.

**reseed-integration-tests:** The first step of this job is to parse the tox files and create the list of tests to run. If the job is related to a pull request then only the most recent package version is tested (see Test Configuration below). Tox environments are grouped so as to cut down on testing time. Because of this, depending on if the job is running only the most recent package version or not, a given tox environment could move between Jenkins jobs.

**\*__integration-test:** These tests are are the subjobs to the **INTEGRATION-TESTS** multijob. They will pull packnsend images from the New Relic docker repository (cf-registry.nr-ops.net) then start all containers. If a container is already running, the action is a noop. The consequence of this is if an image changes in the docker repository, the jobs will not pick up this change automatically (see the Reset Nodes job).

#### \_UNIT-TESTS-[branch]\_
Multijob to run `./build.sh` then `./tests.sh`.

`master` and `develop` tests run on any push to the branch whereas `manual` can be kicked off ad-hoc.

`pullrequest` tests automatically determine which tests need to be run by inspecting the imports of each test file and seeing if those files changed.

#### \_COMBINED-TESTS-[branch]\_
Multijob to run both the unit and integration tests on the given branch.

`pullrequest` tests will be run on all pull requests whereas `manual` can be kicked off ad-hoc.

### Python Agent Tools
**python_agent-dsl-seed:** Job to run on every push to the develop branch. Will rebuild all jenkins jobs from DSL. Any files in the *jenkins* directory with extension `.groovy` will be read and sourced.

**python-agent-tools-Packnsend-Build-and-Push:** On demand job. Will build all packnsend docker images (as currently found in the develop branch) then push them to the [New Relic docker repository](https://source.datanerd.us/container-fabric/docs/blob/master/users-guide/docker.md) (cf-registry.nr-ops.net). Any pre-existing EC2 nodes will not start using these images until the images are restarted (see the Reset Nodes job). New EC2 nodes will automatically use these new images.

**python-agent-tools-Reset-Nodes:** On demand job. Should be run after a change is made to a packnsend image. Will run on each EC2 node, powering the node on first if necessary. Executes two commands: `packnsend pull` then `packnsend restart`. Requires two parameters: 1) *NODE_NAME* is the label of the nodes to run the jobs on, do not change this from "py-ec2-linux", and 2) *GIT_BRANCH* is the branch the job will use to run the packnsend commands.

## EC2 Nodes
EC2 nodes are provisioned on demand by Jenkins. When there are waiting jobs and no available node, Jenkins will first try to power on any offline nodes, then if none are available, it will create new ones. Jenkins will power off nodes when they have gone idle. This is a simple power off, not a deprovision. Thus, any docker containers will be stopped, but no images will be removed.

The nodes run Docker version 1.12 that is installed when the node is first created. This is done to prevent errors in removing containers when using `packnsend`, `btrfs`, and earlier versions of docker (see https://newrelic.atlassian.net/browse/PYTHON-2038). Configuration for the nodes is owned by the tools team and is detailed in the [tools/jenkins-admin-tools](https://source.datanerd.us/tools/jenkins-admin-tools/blob/master/config/hosts/python-agent-build.pdx.vm.datanerd.us.yaml) repo.

## Adding New Docker Tests

Adding new `tox` style tests is now super easy because they are auto-discovered!

For those test directories that have a `docker-compose.yml` file, tests will be run inside that docker-compose environment. Otherwise, tests will be run using `packnsend run` as normal.

### Test Configuration
Available settings under the `jenkins` heading in any integration test tox.ini file.

**mostrecent:** If multiple versions of a package are being tested, use this option to specify which is the most recent. Pull request tests will test only this package version.

**disabled:** Set to `true` if you do not want any of the tests defined in the tox file to be run in jenkins.

**max_group_size:** Jenkins will automatically split tests into multiple jobs to cut down on run time. Globally the max number of environments per group is set in the [`maxEnvsPerContainer` variable](https://source.datanerd.us/python-agent/python_agent/blob/develop/jenkins/test-integration.groovy). This option will override that value.

## Jenkins Plugins and Customizations
We have installed the following plugins on our JaaS instance:
+ build-blocker-plugin
+ build-timeout
+ build-user-vars-plugin
+ email-ext
+ envinject
+ jenkins-multijob-plugin
+ nodelabelparameter

We have installed the following packages on the JaaS master:
+ tox==2.4.1
+ python3.6 built and installed from source (https://www.python.org/ftp/python/3.6.3/Python-3.6.3.tgz) (./configure && sudo make install)

## Development

Development of new jobs can be tricky because of the need to get the groovy files to the JaaS host where they can then be seeded and inspected. Fortunately, local development is possible.

Jenkins DSL is "compiled" into xml files which are then stored by Jenkins as configuration for a job. These xml files can be viewed on the web UI at `/config.xml`, for example https://python-agent-build.pdx.vm.datanerd.us/view/PY_Deploy/job/deploy-to-pypi/config.xml.

To "compile" locally, follow these steps then compare the resultant xml files with those found in the UI.

1. Clone the [more-jenkins-dsl](https://source.datanerd.us/commune/more-jenkins-dsl) repo

  ```
  git clone git@source.datanerd.us:commune/more-jenkins-dsl.git
  cd more-jenkins-dsl
  ```

2. Build the required jar

  ```
  ./gradlew build
  ```

3. From within the repo, copy all groovy files and their dependencies to the `jenkins` directory

  ```
  cp ../python_agent/jenkins/* jenkins
  ```

4. Now generate the xml. The `WORKSPACE` environment variable will tell the groovy scripts where to find your `tests` directory.

  ```
  WORKSPACE=/path/to/your/python_agent ./gradlew generateJenkinsDsl
  ```

5. View the new xml files in `build/dsl-workspace`
