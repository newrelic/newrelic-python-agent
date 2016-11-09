import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String slackChannel = '#python-agent'

use(extensions) {

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
