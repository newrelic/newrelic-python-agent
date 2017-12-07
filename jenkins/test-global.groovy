import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String integTestSuffix = "__integration-test"
String unitTestSuffix = "__unit-test"
String slackChannelPrivate = '#python-dev'
String slackChannelPublic = '#python-agent'
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

    ['pullrequest', 'manual'].each { jobType ->
        multiJob("_INTEGRATION-TESTS-${jobType}_") {
            description("Perform full suite of tests on Python Agent on the ${jobType} branch")
            logRotator { numToKeep(10) }
            label('py-ec2-linux')
            blockOnJobs('python_agent-dsl-seed')

            if (jobType == 'pullrequest') {
                repositoryPR(repoFull)
                gitBranch = '${ghprbActualCommit}'
                mostRecent = 'true'
            } else {
                repository(repoFull, '${GIT_REPOSITORY_BRANCH}')
                gitBranch = ''
                mostRecent = 'true'
            }

            parameters {
                stringParam('GIT_REPOSITORY_BRANCH', gitBranch,
                            'Branch in git repository to run test against.')
                stringParam('MOST_RECENT_ONLY', mostRecent,
                            'Run tests only on most recent version of all packages?')
                stringParam('AGENT_FAKE_COLLECTOR', 'false',
                            'Whether fake collector is used or not.')
                stringParam('AGENT_PROXY_HOST', '',
                            'URI for location of proxy. e.g. http://proxy_host:proxy_port')
            }

            steps {
                phase('seed-multi-job', 'SUCCESSFUL') {
                    job('reseed-pr-tests')
                }
                phase('test-multi-job', 'SUCCESSFUL') {
                    job('pr-test-multijob')
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
            } else if (jobType == 'master' || jobType == 'mmf') {
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

    baseJob("reseed-pr-tests") {
        label('master')
        repo(repoFull)
        branch('${GIT_REPOSITORY_BRANCH}')

        configure {
            description('reseeds only pr-test-multijob')
            logRotator { numToKeep(10) }
            blockOnJobs(['pr-test-multijob', ".*${integTestSuffix}"])

            parameters {
                stringParam('GIT_REPOSITORY_BRANCH', 'develop',
                            'Branch in git repository to run test against.')
                stringParam('MOST_RECENT_ONLY', 'false',
                            'Run tests only on most recent version of all packages?')
            }

            steps {
                reseedFrom('jenkins/reseed-pr.groovy')
            }
        }
    }

}
