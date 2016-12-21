import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String testSuffix = "__unit-test"
String slackChannel = '#python-agent'
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

    ['develop', 'master', 'pullrequest'].each { jobType ->
        multiJob("_UNIT-TESTS-${jobType}_") {
            label('py-ec2-linux')
            description("Run unit tests (i.e. ./tests.sh) on the _${jobType}_ branch")
            logRotator { numToKeep(10) }
            blockOnJobs('.*-Reset-Nodes')

            if (jobType == 'pullrequest') {
                repositoryPR(repoFull)
                triggers {
                    // run for all pull requests
                    pullRequest {
                        permitAll(true)
                        useGitHubHooks()
                    }
                }
                concurrentBuild true
                gitBranch = '${ghprbActualCommit}'
            }
            else {
                repository(repoFull, jobType)
                triggers {
                    // trigger on push to develop/master
                    githubPush()
                }
                gitBranch = jobType
            }

            parameters {
                stringParam('GIT_REPOSITORY_BRANCH', gitBranch,
                            'Branch in git repository to run test agaisnt.')
            }

            steps {
                phase('unit-tests', 'COMPLETED') {

                    job("devpi-pre-build-hook_${testSuffix}") {
                        killPhaseCondition('NEVER')
                    }
                    job("build.sh_${testSuffix}") {
                        killPhaseCondition('NEVER')
                    }

                    for (testEnv in unitTestEnvs) {
                        job("tests.sh-${testEnv}_${testSuffix}") {
                            killPhaseCondition('NEVER')
                        }
                    }
                }
            }

            slackQuiet(slackChannel) {
                notifySuccess true
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
                        // abort if time is > 500% of the average of the
                        // last 3 builds, or 60 minutes
                        elastic(500, 3, 60)
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
            description('Run the devpi pre-build hook.')
            logRotator { numToKeep(10) }
            concurrentBuild true

            wrappers {
                timeout {
                    // abort if time is > 500% of the average of the
                    // last 3 builds, or 60 minutes
                    elastic(500, 3, 60)
                    abortBuild()
                }
            }

            parameters {
                stringParam('GIT_REPOSITORY_BRANCH', 'develop',
                            'Branch in git repository to run test against.')
            }

            steps {
                shell('./docker/devpi/pre-build.sh')
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
                    // abort if time is > 500% of the average of the
                    // last 3 builds, or 60 minutes
                    elastic(500, 3, 60)
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
