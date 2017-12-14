import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String testSuffix = "__unit-test"
String slackChannelPrivate = '#python-dev'
String slackChannelPublic = '#python-agent'
String gitBranch


def getUnitTestEnvs = {

    def proc = "tox --listenvs -c ${WORKSPACE}/tox.ini".execute()
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

use(extensions) {
   def unitTestEnvs = getUnitTestEnvs()

    ['develop', 'master', 'mmf'].each { jobType ->
        multiJob("_UNIT-TESTS-${jobType}_") {
            label('py-ec2-linux')
            description("Run unit tests (i.e. ./tests.sh) on the _${jobType}_ branch")
            logRotator { numToKeep(10) }
            concurrentBuild true
            blockOnJobs('python_agent-dsl-seed')

            if (jobType == 'develop') {
                repository(repoFull, jobType)
                triggers {
                    // run daily on cron
                    cron('H 0 * * 1-5')
                }
                gitBranch = jobType
            } else if (jobType == 'master') {
                repository(repoFull, jobType)
                triggers {
                    // trigger on push to master
                    githubPush()
                }
                gitBranch = jobType
            } else if (jobType == 'mmf') {
                // branch will be correctly set later with the
                // get_mmf_branch.sh script
                repository(repoFull, 'develop')
                triggers {
                    // run daily on cron
                    cron('H 2 * * 1-5')
                }
            }

            if (jobType != 'mmf') {
                parameters {
                    stringParam('GIT_REPOSITORY_BRANCH', gitBranch,
                                'Branch in git repository to run test against.')
                }
            }

            steps {
                if (jobType == 'mmf') {
                    shell('./jenkins/get_mmf_branch.sh')
                }

                phase('unit-tests', 'COMPLETED') {
                    job("devpi-pre-build-hook_${testSuffix}") {
                        killPhaseCondition('NEVER')
                        if (jobType == 'mmf') {  // pass git branch to mmf test
                            parameters {
                                propertiesFile('jenkins/environ')
                            }
                        }
                    }
                    job("build.sh_${testSuffix}") {
                        killPhaseCondition('NEVER')
                        if (jobType == 'mmf') {  // pass git branch to mmf test
                            parameters {
                                propertiesFile('jenkins/environ')
                            }
                        }
                    }

                    for (testEnv in unitTestEnvs) {
                        job("tests.sh-${testEnv}_${testSuffix}") {
                            killPhaseCondition('NEVER')
                            if (jobType == 'mmf') {  // pass git branch to mmf test
                                parameters {
                                    propertiesFile('jenkins/environ')
                                }
                            }
                        }
                    }
                }
            }

            if (jobType == 'master' || jobType == 'mmf') {
                slackQuiet(slackChannelPrivate) {
                    notifyNotBuilt true
                    notifyAborted true
                }
            } else if (jobType == 'develop') {
                slackQuiet(slackChannelPrivate + ',' + slackChannelPublic) {
                    notifyNotBuilt true
                    notifyAborted true
                }
            }
        }
    }

    unitTestEnvs.each { testEnv ->
        baseJob("tests.sh-${testEnv}_${testSuffix}") {
            label('py-ec2-linux')
            repo(repoFull)
            branch('${GIT_REPOSITORY_BRANCH}')

            configure {
                description("Runs ./tests.sh with the ${testEnv} environment")
                logRotator { numToKeep(10) }
                blockOnJobs('.*-Reset-Nodes')
                concurrentBuild true

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
                }

                steps {
                    shell('./jenkins/prep_node_for_test.sh')
                    shell("./docker/packnsend run /data/tests.sh ${testEnv}")
                }
            }
        }
    }

    baseJob("devpi-pre-build-hook_${testSuffix}") {
        label('py-ec2-linux')
        repo(repoFull)
        branch('${GIT_REPOSITORY_BRANCH}')

        configure {
            description('Run the devpi pre-build hook and test the parseconfig.py script.')
            logRotator { numToKeep(10) }
            blockOnJobs('.*-Reset-Nodes')
            concurrentBuild true

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
            }

            steps {
                shell('./docker/devpi/pre-build.sh')
                shell('./docker/packnsend run python ./docker/devpi/test_parseconfig.py')
            }
        }
    }

    baseJob("build.sh_${testSuffix}") {
        label('py-ec2-linux')
        repo(repoFull)
        branch('${GIT_REPOSITORY_BRANCH}')

        configure {
            description('Run ./build.sh')
            logRotator { numToKeep(10) }
            concurrentBuild true

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
            }

            steps {
                shell('./build.sh')
            }
        }
    }

}
