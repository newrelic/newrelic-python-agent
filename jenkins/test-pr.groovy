import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String slackChannel = '#python-agent'
String gitBranch
Boolean isJaasHostname = InetAddress.getLocalHost().getHostName() == 'python-agent-build.pdx.vm.datanerd.us'

if ( !isJaasHostname ) {
    slackChannel = '#python-agent-verbose'
}

use(extensions) {

    ['pullrequest', 'manual'].each { jobType ->
        multiJob("_COMBINED-TESTS-${jobType}_") {
            label('py-ec2-linux')
            description('Run both the integration and unit tests')
            logRotator { numToKeep(10) }
            blockOnJobs('python_agent-dsl-seed')

            if (jobType == 'pullrequest') {
                repositoryPR(repoFull)
                triggers {
                    // run for all pull requests
                    pullRequest {
                        permitAll(true)
                        useGitHubHooks()
                    }
                }
                gitBranch = '${ghprbActualCommit}'
            } else {
                repository(repoFull, '${GIT_REPOSITORY_BRANCH}')
                gitBranch = ''
            }

            parameters {
                stringParam('GIT_REPOSITORY_BRANCH', gitBranch,
                            'Branch in git repository to run test against.')
                stringParam('MOST_RECENT_ONLY', 'true',
                            'Run tests only on most recent version of all packages?')
            }

            steps {
                phase('run-all-the-tests', 'COMPLETED') {
                    job("_UNIT-TESTS-${jobType}_") {
                        killPhaseCondition('NEVER')
                    }
                    job("_INTEGRATION-TESTS-${jobType}_") {
                        killPhaseCondition('NEVER')
                    }
                }
            }

            if (jobType == 'pullrequest') {
                slackQuiet(slackChannel) {
                    customMessage '$ghprbPullTitle (<${ghprbPullLink}|${ghprbSourceBranch}>)'
                    notifySuccess true
                    notifyNotBuilt true
                    notifyAborted true
                }
            }
        }
    }
}
