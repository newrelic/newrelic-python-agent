# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# HeaderMixin assumes the mixin class also inherits from TimeTrace
class HeaderMixin:
    synthetics_key = "X-NewRelic-Synthetics"
    synthetics_info_key = "X-NewRelic-Synthetics-Info"
    settings = None

    def __enter__(self):
        result = super().__enter__()
        if result is self and self.transaction:
            self.settings = self.transaction.settings or None
        return result

    @classmethod
    def generate_request_headers(cls, transaction):
        """
        Return a list of NewRelic specific headers as tuples
        [(HEADER_NAME0, HEADER_VALUE0), (HEADER_NAME1, HEADER_VALUE1)]

        """

        if transaction is None or transaction.settings is None:
            return []

        settings = transaction.settings

        nr_headers = []

        if settings.distributed_tracing.enabled:
            transaction.insert_distributed_trace_headers(nr_headers)

        if transaction.synthetics_header:
            nr_headers.append((cls.synthetics_key, transaction.synthetics_header))
            if transaction.synthetics_info_header:
                nr_headers.append((cls.synthetics_info_key, transaction.synthetics_info_header))

        return nr_headers
