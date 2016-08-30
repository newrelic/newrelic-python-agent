import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String slackChannel = '#python-agent'


// Views for any build and deploy jobs

use(extensions) {
    view('PY_Deploy', 'Deployment jobs',
         '(deploy-to-pypi)|(deploy-to-s3)|(build-and-archive-package)')

    baseJob('deploy-to-pypi') {
        label('py-ec2-linux')
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
                    string('PYPI_TEST_PASSWORD',
                           '69637954-dd74-4407-a2f7-3f328d463a2b')
                    string('PYPI_PRODUCTION_PASSWORD',
                           '91421320-8a18-4b8e-99cf-bb12fc96522b')
                }
            }

            steps {
                environmentVariables {
                    env('PATH', '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin')
                }
                shell('./deploy/deploy-to-pypi.sh')
            }

            slackQuiet(slackChannel){
                notifySuccess true
            }
        }
    }

    baseJob('deploy-to-s3') {
        label('py-ec2-linux')
        repo(repoFull)
        branch('master')

        configure {
            description('Upload the source distribution package to our S3 bucket.')
            logRotator { numToKeep(10) }
            buildInDockerImage('./deploy')

            parameters {
                choiceParam('S3_RELEASE_TYPE', ['testing', 'archive', 'release'],
                        'The specific S3 directory name to upload the distribution to.')
                stringParam('AGENT_VERSION', '', 'Version of the agent to release. (Ex. 2.56.0.42)')
            }

            wrappers {
                credentialsBinding {
                    string('AWS_ACCESS_KEY_ID',
                           '448d1824-c480-4a00-8d78-a25ee72ed7db')
                    string('AWS_SECRET_ACCESS_KEY',
                           'c6af0f0d-f67b-4fd3-89cc-2cb7e92decc9')
                }
            }

            steps {
                environmentVariables {
                    env('PATH', '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin')
                }
                shell('./deploy/deploy-to-s3.sh')
            }

            slackQuiet(slackChannel){
                notifySuccess true
            }
        }
    }

    baseJob('build-and-archive-package') {
        label('py-ec2-linux')
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
                environmentVariables {
                    env('PATH', '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin')
                }
                shell('./build.sh')
                shell('./deploy/upload-to-artifactory.sh')
            }

            publishers {
                archiveArtifacts {
                    pattern 'dist/newrelic*tar.gz'
                }
            }

            slackQuiet(slackChannel){
                notifySuccess true
            }
        }
    }
}
