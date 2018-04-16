import argparse
import os


def initialize_agent():
    from newrelic.config import initialize
    from newrelic.api.application import register_application

    initialize()
    register_application(name='Python Agent Test (uninstrumented 1)',
            timeout=10)
    register_application(name='Python Agent Test (uninstrumented 2)',
            timeout=10)


def uninstrumented_tester(correct_order=True, license_key=None, host=None):

    os.environ['NEW_RELIC_LICENSE_KEY'] = license_key
    os.environ['NEW_RELIC_HOST'] = host

    if correct_order:

        initialize_agent()

        import sqlite3

        metrics = [
                ('Supportability/Uninstrumented/sqlite3', None),
                ('Supportability/Uninstrumented/sqlite3.dbapi2', None),
                ('Supportability/Python/Uninstrumented', None),
        ]

    else:

        import sqlite3  # noqa

        initialize_agent()

        metrics = [
                ('Supportability/Uninstrumented/sqlite3', 1),
                ('Supportability/Uninstrumented/sqlite3.dbapi2', 1),
                ('Supportability/Python/Uninstrumented', 2),
        ]

    from testing_support.validators.validate_metric_payload import (
            validate_metric_payload)
    from newrelic.core.agent import shutdown_agent

    @validate_metric_payload(metrics)
    def _test():
        # Shutdown the agent, forcing a harvest of both registered applications
        shutdown_agent(10.0)

    _test()


def _get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--correct-order', type=bool)
    parser.add_argument('--license-key', type=str)
    parser.add_argument('--host', type=str)

    return parser.parse_args()


if __name__ == '__main__':
    args = _get_args()
    uninstrumented_tester(correct_order=args.correct_order,
            license_key=args.license_key, host=args.host)
