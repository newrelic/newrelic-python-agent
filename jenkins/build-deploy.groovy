import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String slackChannel = '#python-agent'


// Views for any build and deploy jobs

use(extensions) {
    view('Python_Agent_Deploy', 'Deployment jobs',
         '(deploy-to-pypi)|(build-and-archive-package)')

    baseJob('deploy-to-pypi') {
        label('ec2-linux')
        repo(repoFull)
        branch('master')

        configure {
            description('Upload the source distribution package to PyPI. By default, this will upload to Test PyPI.\n\n' +
                        '**ONLY SELECT \'pypi-production\' IF YOU WANT TO RELEASE!!**')
            logRotator { numToKeep(10) }
            buildInDockerImage('./deploy')

            parameters {
                choiceParam('PYPI_REPOSITORY', ['pypi-test', 'pypi-production'], '')
                stringParam('AGENT_VERSION', '', 'Version of the agent to release. (Ex. 2.56.0.42)')
            }

            wrappers {
                credentialsBinding {
                    string('PYPI_TEST_PASSWORD', 'put the password here!')
                    string('PYPI_PRODUCTION_PASSWORD', 'put the password here!')
                }
            }

            steps {
                shell(readFileFromWorkspace('./deploy/deploy-to-pypi.sh'))
            }

            //slackQuiet(slackChannel){
            //    notifySuccess true
            //}
        }
    }

    baseJob('build-and-archive-package') {
        label('ec2-linux')
        repo(repoFull)
        branch('master')

        configure {
            description('Build the source distribution package and upload it to Artifactory.')
            logRotator { numToKeep(10) }
            buildInDockerImage('./deploy')

            parameters {
                stringParam('AGENT_VERSION', '', 'Version of the agent to release. (Ex. 2.56.0.42)')
            }

            wrappers {
                credentialsBinding {
                    string('ARTIFACTORY_PASSWORD', 'put the password here!')
                }
            }

            steps {
                shell(readFileFromWorkspace('./build.sh'))
                shell(readFileFromWorkspace('./deploy/upload-to-artifactory.sh'))
            }

            publishers {
                archiveArtifacts {
                    pattern 'dist/newrelic*tar.gz'
                }
            }

            //slackQuiet(slackChannel){
            //    notifySuccess true
            //}
        }
    }
}
