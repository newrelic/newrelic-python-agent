// Grab will no longer be supported in jenkins-dsl 1.36, we currently use 1.35
@Grab('org.yaml:snakeyaml:1.17')
import org.yaml.snakeyaml.Yaml
import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String testSuffix = "__integration-test"

def yaml = new Yaml()
List<String> disabledList = yaml.load(readFileFromWorkspace('jenkins/test-integration-config.yml')).disable

def getPacknsendTests = {

    // Get list of lists. Each item represents a single test. For example:
    //
    // [
    //     framework_django_tox.ini__docker_test,
    //     tests/framework_django/tox.ini,
    //     tests/framework_django/docker-compose.yml,
    // ]
    //
    // Where the first item is the name of the test. The second is the path to
    // the tox file relative to the job's workspace. The third is the path to
    // the docker-compose file relative to the job's workspace if it exists, if
    // it does not exist, this value is an empty string.

    def packnsendTestsList = []
    String composeName = 'docker-compose.yml'
    new File("${WORKSPACE}/tests").eachDir() { dir ->
        String dirName = dir.getName()

        // Determine if there is an available docker-compose environment
        String composePath = ""
        dir.eachFileMatch(composeName) { composeFile ->
            composePath = "tests/${dirName}/${composeName}"
        }

        dir.eachFileMatch(~/^tox.*.ini$/) { toxFile ->
            File canonicalFile = toxFile.getCanonicalFile()
            String canonicalName = canonicalFile.getPath()
            String absoluteName = toxFile.getAbsolutePath()

            // If this is not a symlink
            //   or if it's a symlink that doesn't match tox.ini
            // -> add it to tests
            if ((canonicalName == absoluteName) ||
                !canonicalFile.getName().matches(~/^tox.*.ini$/)) {

                String toxName = toxFile.getName()
                String toxPath = "tests/${dirName}/${toxName}"
                String testName = "${dirName}_${toxName}_${testSuffix}"

                if (!disabledList.contains(toxPath)) {
                    def test = [testName, toxPath, composePath]
                    packnsendTestsList.add(test)
                }
            }
        }
    }
    packnsendTestsList
}

use(extensions) {
    def packnsendTests = getPacknsendTests()

    multiJob('integration-test-multijob') {
        description('Real multijob which runs the actual integration tests.')
        logRotator { numToKeep(10) }
        label('py-ec2-linux')

        parameters {
            stringParam('GIT_REPOSITORY_BRANCH', 'develop',
                        'Branch in git repository to run test against.')
            stringParam('AGENT_FAKE_COLLECTOR', 'false',
                        'Whether fake collector is used or not.')
            stringParam('AGENT_PROXY_HOST', '',
                        'URI for location of proxy. e.g. http://proxy_host:proxy_port')
        }

        steps {
            phase('tox-tests', 'COMPLETED') {
                for (test in packnsendTests) {
                    job(test[0]) {
                        killPhaseCondition('NEVER')
                    }
                }
            }
        }
    }

    // create all packnsend base tests
    packnsendTests.each { testName, toxPath, composePath ->
        baseJob(testName) {
            label('py-ec2-linux')
            repo(repoFull)
            branch('${GIT_REPOSITORY_BRANCH}')

            configure {
                description("Run tox file ${toxPath}")
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

                parameters {
                    stringParam('GIT_REPOSITORY_BRANCH', 'develop',
                                'Branch in git repository to run test against.')
                    stringParam('AGENT_FAKE_COLLECTOR', 'true',
                                'Whether fake collector is used or not.')
                    stringParam('AGENT_PROXY_HOST', '',
                                'URI for location of proxy. e.g. http://proxy_host:proxy_port')
                }

                steps {
                    environmentVariables {
                        env('NEW_RELIC_DEVELOPER_MODE', '${AGENT_FAKE_COLLECTOR}')
                        env('NEW_RELIC_PROXY_HOST', '${AGENT_PROXY_HOST}')
                        env('DOCKER_HOST', 'unix:///var/run/docker.sock')
                    }
                    shell('./jenkins/prep_node_for_test.sh')

                    if (composePath != "") {
                        shell("./docker/packnsend run -c ${composePath} tox -c ${toxPath}")
                    } else {
                        shell("./docker/packnsend run tox -c ${toxPath}")
                    }
                }
            }
        }
    }
}
