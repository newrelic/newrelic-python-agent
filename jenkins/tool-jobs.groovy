import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String testPrefix = "${organization}-tools"
String slackChannel = '#python-agent'


// Views for any tool-like jobs

use(extensions) {
    view('Python_Agent_Tools', 'A view for some tools', "${testPrefix}.*")

    projectSeedJob() {
        repo(repoGHE)
        org(organization)
        dslPath('jenkins')

        configure {
            displayName("${testPrefix}-dsl-seed")

            // set repository a second time to ensure building from develop
            // branch instead of master
            repository(repoFull, 'develop')
        }
    }

    baseJob("${testPrefix}-Packnsend-Build-and-Push") {
        label('ec2-linux')
        repo(repoFull)
        branch('${GIT_BRANCH}')

        configure {
            description('A job to build packnsend images then push them to dogestry')

            parameters {
                stringParam('GIT_BRANCH', 'develop', '')
            }

            steps {
                environmentVariables {
                    // dogestry creds
                    env('AWS_ACCESS_KEY_ID', '${NR_DOCKER_DEV_ACCESS_KEY_ID}')
                    env('AWS_SECRET_ACCESS_KEY', '${NR_DOCKER_DEV_SECRET_ACCESS_KEY}')
                    env('DOCKER_HOST', 'unix:///var/run/docker.sock')
                }
                shell(readFileFromWorkspace('./jenkins/packnsend-buildnpush.sh'))
            }

            slackQuiet(slackChannel){
                notifySuccess true
            }
        }
    }
}
