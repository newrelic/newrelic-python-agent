from newrelic.api.transaction import current_transaction
from newrelic.common.encoding_utils import deobfuscate, json_decode


OUTBOUND_TRACE_KEYS_REQUIRED = (
        'ty', 'ac', 'ap', 'tr', 'pr', 'sa', 'ti')


def validate_outbound_headers(header_id='X-NewRelic-ID',
        header_transaction='X-NewRelic-Transaction'):
    transaction = current_transaction()
    headers = transaction._test_request_headers
    settings = transaction.settings
    encoding_key = settings.encoding_key

    assert header_id in headers

    values = headers[header_id]
    if isinstance(values, list):
        assert len(values) == 1, headers
        assert isinstance(values[0], type(''))
        value = values[0]
    else:
        value = values

    cross_process_id = deobfuscate(value, encoding_key)
    assert cross_process_id == settings.cross_process_id

    assert header_transaction in headers

    values = headers[header_transaction]
    if isinstance(values, list):
        assert len(values) == 1, headers
        assert isinstance(values[0], type(''))
        value = values[0]
    else:
        value = values

    (guid, record_tt, trip_id, path_hash) = \
            json_decode(deobfuscate(value, encoding_key))

    assert guid == transaction.guid
    assert record_tt == transaction.record_tt
    assert trip_id == transaction.trip_id
    assert path_hash == transaction.path_hash
