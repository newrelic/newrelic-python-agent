import groovy.json.JsonSlurper
import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String testSuffix = "__integration-test"
String slackChannel = '#python-agent-dev'

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
            "python2.7 ${workspace}/jenkins/scripts/parse_integration_test_tox_files.py " +
                "--test-suffix ${testSuffix} " +
                "--max-group-size ${maxEnvsPerContainer} " +
                "--most-recent-only ${mostRecentOnly} " +
                "--workspace ${workspace}"
        ).execute()

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


use(extensions) {
    def packnsendTests = getPacknsendTests("${WORKSPACE}", testSuffix, "false")

    ['develop', 'master'].each { jobType ->
        multiJob("_INTEGRATION-TESTS-${jobType}_") {
            concurrentBuild true
            description("Perform full suite of tests on Python Agent on the ${jobType} branch")
            logRotator { numToKeep(10) }
            label('py-ec2-linux')
            blockOnJobs('python_agent-dsl-seed')

            if (jobType == 'develop') {
                repository(repoFull, jobType)
                triggers {
                    // run daily on cron
                    cron('H 2 * * 1-5')
                }
                gitBranch = jobType
            } else if (jobType == 'master') {
                repository(repoFull, jobType)
                triggers {
                    // trigger on push to master
                    githubPush()
                }
                gitBranch = jobType
            }

            parameters {
                stringParam('GIT_REPOSITORY_BRANCH', gitBranch,
                            'Branch in git repository to run test against.')
                stringParam('AGENT_FAKE_COLLECTOR', 'false',
                            'Whether fake collector is used or not.')
                stringParam('AGENT_PROXY_HOST', '',
                            'URI for location of proxy. e.g. http://proxy_host:proxy_port')
            }

            steps {
                conditionalSteps {
                    condition {
                        alwaysRun()
                    }

                    // do not run the following jobs if the above condition
                    // fails
                    runner('DontRun')

                    steps {
                        phase('tox-tests', 'COMPLETED') {
                            for (test in packnsendTests) {
                                job(test[0]) {
                                    killPhaseCondition('NEVER')
                                }
                            }
                        }
                    }
                }
            }

            if (jobType == 'master') {
                slackQuiet(slackChannel) {
                    notifyNotBuilt true
                    notifyAborted true
                }
            } else if (jobType == 'develop') {
                slackQuiet(slackChannel) {
                    notifyNotBuilt true
                    notifyAborted true
                }
            }
        }
    }

    // create all packnsend base tests
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
                    shell('./jenkins/scripts/prep_node_for_test.sh')

                    if (composePath) {
                        shell("./docker/packnsend run -c ${composePath} tox -vvv -c ${toxPath} -e ${testEnvs}")
                    } else {
                        shell("./docker/packnsend run tox -vvv -c ${toxPath} -e ${testEnvs}")
                    }
                }
            }
        }
    }
}
