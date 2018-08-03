import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String testSuffix = "__integration-test"
String slackChannel = '#python-agent'

use(extensions) {
    baseJob("_BENCHMARKS-develop_") {
        label('py-ec2-linux')
        repo(repoFull)
        branch('develop')

        configure {
            description('Run benchmarks on develop, nightly at 5am.')

            triggers {
                // run daily on cron
                cron('H 5 * * 1-5')
            }

            steps {
                shell('./jenkins/scripts/prep_node_for_test.sh')
                shell('./docker/packnsend gitrun ./jenkins/scripts/run_benchmark.sh')
            }

            slackQuiet(slackChannel)
        }
    }
}