import groovy.json.JsonSlurper
import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String integrationSuffix = "__pr-integration-test"
String unitSuffix = "__unit-test"

String mostRecentOnly
try {
   mostRecentOnly = "${MOST_RECENT_ONLY}"
} catch (all) {
   mostRecentOnly = "false"
}

def getPacknsendTests (String workspace, String testSuffix, String mostRecentOnly) {
    Integer maxEnvsPerContainer = 14

    // Get list of lists. Each item represents a single test. For example:
    //
    // [
    //     "framework_django_tox.ini__docker_test",
    //     "tests/framework_django/tox.ini",
    //     "py27-with-extensions,py27-without-extensions",
    //     "tests/framework_django/docker-compose.yml",
    // ]
    //
    // Where the first item is the name of the test. The second is the path to
    // the tox file relative to the job's workspace. The third is the list tox
    // environments to run the test on. The fourth is the path to the
    // docker-compose file relative to the job's workspace if it exists, if it
    // does not exist, this value is `null`.

    println "Reseed to run tests on only most recent package versions? ${mostRecentOnly}"

    def proc = (
        "python2.7 ${workspace}/jenkins/parse_integration_test_tox_files.py " +
            "--test-suffix ${testSuffix} " +
            "--max-group-size ${maxEnvsPerContainer} " +
            "--most-recent-only ${mostRecentOnly} " +
            "--workspace ${workspace}"
    )
    println("Running ${proc}")
    proc = proc.execute()

    def stdout = new StringBuilder()
    def stderr = new StringBuilder()

    proc.consumeProcessOutput(stdout, stderr)
    proc.waitForOrKill(15000)

    if ( proc.exitValue() != 0 ) {
        println("=======")
        println("stdout:\n${stdout}")
        println("=======")
        println("stderr:\n${stderr}")
        println("=======")
        throw new Exception("Process failed with code ${proc.exitValue()}")
    }

    new JsonSlurper().parseText(stdout.toString())
}

def getUnitTestEnvs = {

    def proc = "tox --listenvs -c ${WORKSPACE}/tox.ini"
    println("Running ${proc}")
    proc = proc.execute()
    def stdout = new StringBuilder()
    def stderr = new StringBuilder()

    proc.consumeProcessOutput(stdout, stderr)
    proc.waitForOrKill(5000)

    if ( proc.exitValue() != 0 ) {
        println("=======")
        println("stdout:\n${stdout}")
        println("=======")
        println("stderr:\n${stderr}")
        println("=======")
        throw new Exception("Process failed with code ${proc.exitValue()}")
    }

    List<String> unitTestEnvs = new String(stdout).split('\n')
}

def getChangedTests (String dirs) {

    // Get list of directories which have python files that import changed files.
    //
    // [
    //     "tests/framework_django/tox.ini",
    //     "tests/framework_aiohttp/tox.ini",
    // ]
    //
    // Each directory returned contains python files which import files that
    // have changed relative to the base branch.

    def proc = (
        "/usr/local/bin/python3.6 ${WORKSPACE}/jenkins/extract_changed.py " +
            "-nr_path ${WORKSPACE} " +
            "${dirs}"
    )
    println("Running ${proc}")
    proc = proc.execute()

    def stdout = new StringBuilder()
    def stderr = new StringBuilder()

    proc.consumeProcessOutput(stdout, stderr)
    proc.waitForOrKill(20000)

    if ( proc.exitValue() != 0 ) {
        println("=======")
        println("stdout:\n${stdout}")
        println("=======")
        println("stderr:\n${stderr}")
        println("=======")
        throw new Exception("Process failed with code ${proc.exitValue()}")
    }

    new JsonSlurper().parseText(stdout.toString())
}

use(extensions) {
    def packnsendTests = getPacknsendTests("${WORKSPACE}", integrationSuffix, mostRecentOnly)
    def changedIntegrationTests = getChangedTests("${WORKSPACE}/tests/*")
    def changedUnitTests = getChangedTests(
            "newrelic/*/tests newrelic/tests")
    def unitTestEnvs = getUnitTestEnvs()

    ['pullrequest', 'manual'].each { jobType ->
        multiJob("_INTEGRATION-TESTS-${jobType}_") {
            description('Real multijob which runs the actual integration tests.')
            logRotator { numToKeep(10) }
            label('py-ec2-linux')
            repository(repoFull, '${GIT_REPOSITORY_BRANCH}')

            parameters {
                stringParam('GIT_REPOSITORY_BRANCH', 'develop',
                            'Branch in git repository to run test against.')
                stringParam('AGENT_FAKE_COLLECTOR', 'false',
                            'Whether fake collector is used or not.')
                stringParam('AGENT_PROXY_HOST', '',
                            'URI for location of proxy. e.g. http://proxy_host:proxy_port')
            }

            steps {
                phase('tox-tests', 'COMPLETED') {
                    for (test in packnsendTests) {
                        for (testToRun in changedIntegrationTests) {
                            // determine if test should be run by matching
                            // against the directory
                            if (jobType == 'manual' || test[1].startsWith(testToRun)) {
                                job(test[0]) {
                                    killPhaseCondition('NEVER')
                                }
                                break;
                            }
                        }
                    }
                }
            }

            if (jobType == 'manual') {
                // enable build-user-vars-plugin
                wrappers { buildUserVars() }
                // send private slack message
                slackQuiet('@${BUILD_USER_ID}') {
                    customMessage 'on branch `${GIT_REPOSITORY_BRANCH}`'
                    notifySuccess true
                    notifyNotBuilt true
                    notifyAborted true
                }
            }
        }
    }

    // create all packnsend base tests
    // TODO: If testName excludes the suffix we can avoid recreating ALL of the
    // tests on every PR
    packnsendTests.each { testName, toxPath, testEnvs, composePath ->
        baseJob(testName) {
            label('py-ec2-linux')
            repo(repoFull)
            branch('${GIT_REPOSITORY_BRANCH}')

            configure {
                description("Run tox file ${toxPath}")
                logRotator { numToKeep(10) }
                blockOnJobs('.*-Reset-Nodes')

                wrappers {
                    timeout {
                        // abort if nothing is printed to stdout/stderr
                        // in 120 seconds
                        noActivity(120)
                        abortBuild()
                    }
                }

                parameters {
                    stringParam('GIT_REPOSITORY_BRANCH', 'develop',
                                'Branch in git repository to run test against.')
                    stringParam('AGENT_FAKE_COLLECTOR', 'true',
                                'Whether fake collector is used or not.')
                    stringParam('AGENT_PROXY_HOST', '',
                                'URI for location of proxy. e.g. http://proxy_host:proxy_port')
                }

                steps {
                    environmentVariables {
                        env('NEW_RELIC_DEVELOPER_MODE', '${AGENT_FAKE_COLLECTOR}')
                        env('NEW_RELIC_PROXY_HOST', '${AGENT_PROXY_HOST}')
                        env('DOCKER_HOST', 'unix:///var/run/docker.sock')
                    }
                    shell('./jenkins/prep_node_for_test.sh')

                    if (composePath) {
                        shell("./docker/packnsend run -c ${composePath} tox -c ${toxPath} -e ${testEnvs}")
                    } else {
                        shell("./docker/packnsend run tox -c ${toxPath} -e ${testEnvs}")
                    }
                }
            }
        }
    }

    ['pullrequest', 'manual'].each { jobType ->
        multiJob("_UNIT-TESTS-${jobType}_") {
            label('py-ec2-linux')
            description("Run unit tests (i.e. ./tests.sh) on the _${jobType}_ branch")
            logRotator { numToKeep(10) }
            concurrentBuild true
            blockOnJobs('python_agent-dsl-seed')

            if (jobType == 'pullrequest') {
                repositoryPR(repoFull)
                gitBranch = '${ghprbActualCommit}'
            } else {
                repository(repoFull, '${GIT_REPOSITORY_BRANCH}')
                gitBranch = ''
            }

            parameters {
                stringParam('GIT_REPOSITORY_BRANCH', gitBranch,
                            'Branch in git repository to run test against.')
            }

            steps {
                phase('unit-tests', 'COMPLETED') {

                    job("devpi-pre-build-hook_${unitSuffix}") {
                        killPhaseCondition('NEVER')
                    }
                    job("build.sh_${unitSuffix}") {
                        killPhaseCondition('NEVER')
                    }

                    if (!changedUnitTests.isEmpty()) {
                        for (testEnv in unitTestEnvs) {
                            job("tests.sh-${testEnv}_${unitSuffix}") {
                                killPhaseCondition('NEVER')
                            }
                        }
                    }
                }
            }

            if (jobType == 'manual') {
                // enable build-user-vars-plugin
                wrappers { buildUserVars() }
                // send private slack message
                slackQuiet('@${BUILD_USER_ID}') {
                    customMessage 'on branch `${GIT_REPOSITORY_BRANCH}`'
                    notifySuccess true
                    notifyNotBuilt true
                    notifyAborted true
                }
            }
        }
    }
}
