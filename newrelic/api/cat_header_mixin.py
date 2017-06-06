from newrelic.common.encoding_utils import (obfuscate, deobfuscate,
        json_encode, json_decode)


class CatHeaderMixin(object):
    cat_id_key = 'X-NewRelic-ID'
    cat_transaction_key = 'X-NewRelic-Transaction'
    cat_appdata_key = 'X-NewRelic-App-Data'
    cat_synthetics_key = 'X-NewRelic-Synthetics'

    def process_response_headers(self, response_headers):
        """
        Decode the response headers and create appropriate metics based on the
        header values. The response_headers are passed in as a list of tuples.
        [(HEADER_NAME0, HEADER_VALUE0), (HEADER_NAME1, HEADER_VALUE1)]

        """

        if not self.settings.cross_application_tracer.enabled:
            return

        appdata = None

        try:
            for k, v in response_headers:
                if k.upper() == self.cat_appdata_key.upper():
                    appdata = json_decode(deobfuscate(v,
                            self.settings.encoding_key))
                    break

            if appdata:
                self.params['cross_process_id'] = appdata[0]
                self.params['external_txn_name'] = appdata[1]
                self.params['transaction_guid'] = appdata[5]

        except Exception:
            pass

    @classmethod
    def generate_request_headers(cls, transaction):
        """
        Return a list of NewRelic specific headers as tuples
        [(HEADER_NAME0, HEADER_VALUE0), (HEADER_NAME1, HEADER_VALUE1)]

        """

        if transaction is None:
            return []

        settings = transaction.settings

        nr_headers = []

        if settings.cross_application_tracer.enabled:

            transaction.is_part_of_cat = True
            encoded_cross_process_id = obfuscate(settings.cross_process_id,
                    settings.encoding_key)
            nr_headers.append((cls.cat_id_key, encoded_cross_process_id))

            transaction_data = [transaction.guid, transaction.record_tt,
                    transaction.trip_id, transaction.path_hash]
            encoded_transaction = obfuscate(json_encode(transaction_data),
                    settings.encoding_key)
            nr_headers.append((cls.cat_transaction_key, encoded_transaction))

        if transaction.synthetics_header:
            nr_headers.append(
                    (cls.cat_synthetics_key, transaction.synthetics_header))

        return nr_headers
