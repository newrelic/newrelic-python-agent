import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String integTestSuffix = "__integration-test"
String unitTestSuffix = "__unit-test"
String slackChannel = '#python-agent'
String gitBranch

use(extensions) {

    view('PY_Tests', 'Test jobs',

            '(_COMBINED-TESTS-manual_)|' +
            '(_COMBINED-TESTS-pullrequest_)|' +
            '(_INTEGRATION-TESTS-develop_)|' +
            '(_INTEGRATION-TESTS-manual_)|' +
            '(_INTEGRATION-TESTS-master_)|' +
            '(_UNIT-TESTS-develop_)|' +
            '(_UNIT-TESTS-manual_)|' +
            '(_UNIT-TESTS-master_)'
    )

    ['develop', 'master', 'pullrequest', 'manual'].each { jobType ->
        multiJob("_INTEGRATION-TESTS-${jobType}_") {
            description("Perform full suite of tests on Python Agent on the ${jobType} branch")
            logRotator { numToKeep(10) }
            label('py-ec2-linux')
            publishers {
                extendedEmail('python-agent-dev@newrelic.com')
            }
            blockOnJobs('python_agent-dsl-seed')

            if (jobType == 'pullrequest') {
                repositoryPR(repoFull)
                gitBranch = '${ghprbActualCommit}'
            }
            else if (jobType == 'develop') {
                repository(repoFull, jobType)
                triggers {
                    // trigger on push to develop
                    githubPush()
                    // run daily on cron
                    cron('H 10 * * *')
                }
                gitBranch = jobType
            } else if (jobType == 'master') {
                repository(repoFull, jobType)
                triggers {
                    // trigger on push to master
                    githubPush()
                }
                gitBranch = jobType
            } else {
                repository(repoFull, '${GIT_REPOSITORY_BRANCH}')
                gitBranch = ''
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
    }

    baseJob("reseed-integration-tests") {
        label('master')
        repo(repoFull)
        branch('${GIT_REPOSITORY_BRANCH}')

        configure {
            description('reseeds only integration-test-multijob')
            logRotator { numToKeep(10) }
            blockOnJobs(['integration-test-multijob', ".*${integTestSuffix}"])

            parameters {
                stringParam('GIT_REPOSITORY_BRANCH', 'develop',
                            'Branch in git repository to run test against.')
            }

            steps {
                reseedFrom('jenkins/test-integration.groovy')
            }
        }
    }

}
