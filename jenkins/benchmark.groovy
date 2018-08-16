import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String testSuffix = "__integration-test"
String slackChannel = '#python-agent-dev'

use(extensions) {
    baseJob("_BENCHMARKS-develop_") {
        label('py-benchmarking')
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
                shell('./jenkins/scripts/prep_benchmarks.sh')
                shell('./docker/packnsend asvrun ./jenkins/scripts/run_benchmarks.sh')
                shell('./jenkins/scripts/commit_benchmarks.sh')
            }

            slackQuiet(slackChannel)
        }
    }
}
