import sys
import os


def uninstrumented_tester(correct_order=True):

    config_file = os.path.join(os.path.abspath(os.path.dirname(__file__)),
            'uninstrumented.ini')

    if correct_order:

        from newrelic.config import initialize
        from newrelic.api.application import register_application

        initialize(config_file)
        register_application(name='Python Agent Test (uninstrumented 1)',
                timeout=10)
        register_application(name='Python Agent Test (uninstrumented 2)',
                timeout=10)

        import sqlite3

        metrics = [
                ('Supportability/Uninstrumented/sqlite3', None),
                ('Supportability/Uninstrumented/sqlite3.dbapi2', None),
                ('Supportability/Python/Uninstrumented', None),
        ]

    else:

        import sqlite3  # noqa

        from newrelic.config import initialize
        from newrelic.api.application import register_application

        initialize(config_file)
        register_application(name='Python Agent Test (uninstrumented 1)',
                timeout=10)
        register_application(name='Python Agent Test (uninstrumented 2)',
                timeout=10)

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


if __name__ == '__main__':
    correct_order = sys.argv[1] == 'True'
    uninstrumented_tester(correct_order=correct_order)
