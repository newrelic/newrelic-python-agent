import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String testSuffix = "__integration-test"
String slackChannel = '#python-agent'

use(extensions) {

    view('PY_Tests', 'Test jobs',
         "(_INTEGRATION-TESTS_)|(.*${testSuffix})|(_UNIT-TESTS.*)")

    multiJob('_INTEGRATION-TESTS_') {
        description('Perform full suite of tests on Python Agent')
        logRotator { numToKeep(10) }
        triggers { cron('H 10 * * *') }
        label('py-ec2-linux')
        publishers {
            extendedEmail('python-agent-dev@newrelic.com')
        }

        parameters {
            stringParam('GIT_REPOSITORY_BRANCH', 'develop',
                        'Branch in git repository to run test against.')
            stringParam('AGENT_FAKE_COLLECTOR', 'false',
                        'Whether fake collector is used or not.')
            stringParam('AGENT_PROXY_HOST', '',
                        'URI for location of proxy. e.g. http://proxy_host:proxy_port')
        }

        steps {
            phase('seed-multi-job', 'SUCCESSFUL') {
                job('reseed-integration-tests')
            }
            phase('run-child-multijob', 'COMPLETED') {
                job('integration-test-multijob')
            }
        }

        slack(slackChannel){
            notifySuccess true
        }
    }

    baseJob("reseed-integration-tests") {
        label('master')
        repo(repoFull)
        branch('${GIT_REPOSITORY_BRANCH}')

        configure {
            description('reseeds only integration-test-multijob')
            logRotator { numToKeep(10) }
            blockOnJobs(['integration-test-multijob', 'python_agent-dsl-seed'])

            parameters {
                stringParam('GIT_REPOSITORY_BRANCH', 'develop',
                            'Branch in git repository to run test against.')
            }

            steps {
                reseedFrom('jenkins/test-integration.groovy')
            }
        }
    }

    ['develop', 'master', 'pullrequest'].each { jobType ->
        jaasBaseJob("_UNIT-TESTS-${jobType}_") {
            label('py-ec2-linux')
            description('Run the old style tests (i.e. ./tests.sh)')
            logRotator { numToKeep(10) }
            blockOnJobs('.*-Reset-Nodes')

            wrappers {
                timeout {
                    // abort if time is > 500% of the average of the
                    // last 3 builds, or 60 minutes
                    elastic(500, 3, 60)
                    abortBuild()
                }
            }

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
            }
            else {
                repository(repoFull, jobType)
                triggers {
                    // trigger on push to develop/master
                    githubPush()
                }
            }

            steps {
                environmentVariables {
                    env('DOCKER_HOST', 'unix:///var/run/docker.sock')
                }
                shell('./jenkins/prep_node_for_test.sh')
                shell('./build.sh')
                shell('./docker/packnsend run /data/tests.sh')
            }

            slackQuiet(slackChannel) {
                notifySuccess true
            }
        }
    }
}
