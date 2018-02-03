import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String integTestSuffix = "__pr-integration-test"
String slackChannelPrivate = '#python-dev'
String slackChannelPublic = '#python-agent'
String gitBranch


use(extensions) {

    view('PY_Tests', 'Test jobs',
            '(_COMBINED-TESTS-manual_)|' +
            '(_COMBINED-TESTS-pullrequest_)|' +
            '(_INTEGRATION-TESTS-develop_)|' +
            '(_INTEGRATION-TESTS-master_)|' +
            '(_INTEGRATION-TESTS-mmf_)|' +
            '(_UNIT-TESTS-develop_)|' +
            '(_UNIT-TESTS-master_)|' +
            '(_UNIT-TESTS-mmf_)'
    )

    baseJob("reseed-pr-tests") {
        label('master')
        branch('${GIT_REPOSITORY_BRANCH}')

        configure {
            repositoryPR(repoFull)
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
