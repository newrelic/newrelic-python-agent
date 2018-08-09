from newrelic.api.web_transaction import WebTransaction
from benchmarks.util import (MockApplication, make_synthetics_header,
        make_cross_agent_headers)

ENCODING_KEY = '1234567890123456789012345678901234567890'
SYNTHETICS_RESOURCE_ID = '09845779-16ef-4fa7-b7f2-44da8e62931c'
SYNTHETICS_JOB_ID = '8c7dd3ba-4933-4cbb-b1ed-b62f511782f4'
SYNTHETICS_MONITOR_ID = 'dc452ae9-1a93-4ab5-8a33-600521e9cd00'


class Lite(object):

    def setup(self, settings=None):
        self.app = MockApplication(settings=settings)
        self.environ = {"REQUEST_URI": "/web_transaction"}

    def time_web_application_init(self):
        WebTransaction(self.app, self.environ)


class AllEnviron(Lite):

    def setup(self, settings={
        'cross_process_id': '1#1',
        'encoding_key': ENCODING_KEY,
        'trusted_account_ids': [1],
    }):
        super(AllEnviron, self).setup(settings=settings)
        self.environ = {
            'newrelic.enabled': True,
            'newrelic.set_background_task': False,
            'newrelic.ignore_transaction': False,
            'newrelic.suppress_apdex_metric': False,
            'newrelic.suppress_transaction_trace': False,
            'newrelic.capture_request_params': False,
            'newrelic.disable_browser_autorum': False,
            'SERVER_PORT': 8000,
            'RAW_URI': '/web_transaction?foo=bar',
            'SCRIPT_NAME': 'foobar',
            'PATH_INFO': '/web_transaction',
            'HTTP_X_REQUEST_START': 0,
            'HTTP_X_QUEUE_START': 0,
            'mod_wsgi.request_start': 0,
            'mod_wsgi.queue_start': 0,
            'QUERY_STRING': 'foo=bar',
            'CONTENT_LENGTH': 80,
            'REQUEST_METHOD': 'GET',
            'HTTP_USER_AGENT': 'benchmarks',
            'HTTP_REFERER': 'nobody',
            'CONTENT_TYPE': 'garbage',
            'HTTP_HOST': 'trashcan',
            'HTTP_ACCEPT': 'trash',
        }


class AllEnvironPlusSynthetics(AllEnviron):
    def setup(self):
        super(AllEnvironPlusSynthetics, self).setup()
        header = make_synthetics_header(
                account_id=1,
                resource_id=SYNTHETICS_RESOURCE_ID,
                job_id=SYNTHETICS_JOB_ID,
                monitor_id=SYNTHETICS_MONITOR_ID,
                encoding_key=ENCODING_KEY)

        self.environ['HTTP_X_NEWRELIC_SYNTHETICS'] = list(header.values())[0]


class AllEnvironPlusCAT(AllEnviron):
    def setup(self):
        super(AllEnvironPlusCAT, self).setup()

        payload = ['b854df4feb2b1f06', False, '7e249074f277923d', '5d2957be']
        headers = make_cross_agent_headers(payload, ENCODING_KEY, '1#1')
        self.environ.update({
            'HTTP_X_NEWRELIC_ID': headers['X-NewRelic-ID'],
            'HTTP_X_NEWRELIC_TRANSACTION': headers['X-NewRelic-Transaction'],
        })


class AllEnvironPlusDT(AllEnviron):
    def setup(self, settings={
        'cross_process_id': '1#1',
        'encoding_key': ENCODING_KEY,
        'trusted_account_ids': [1],
        'trusted_account_key': '1',
        'distributed_tracing.enabled': True,
    }):
        super(AllEnvironPlusDT, self).setup(settings=settings)
        payload = ('eyJkIjogeyJwciI6IDAuMjczMTM1OTc2NTQ0MjQ1NCwgImFjIjogIj'
            'IwMjY0IiwgInR4IjogIjI2MWFjYTliYzhhZWMzNzQiLCAidHkiOiAiQXBwIiw'
            'gInRyIjogIjI2MWFjYTliYzhhZWMzNzQiLCAiYXAiOiAiMTAxOTUiLCAidGsi'
            'OiAiMSIsICJ0aSI6IDE1MjQwMTAyMjY2MTAsICJzYSI6IGZhbHNlfSwgInYiO'
            'iBbMCwgMV19')

        self.environ['HTTP_NEWRELIC'] = payload
