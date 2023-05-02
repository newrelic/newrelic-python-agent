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

import pytest
from newrelic.api.background_task import background_task
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics


@pytest.fixture(scope="session")
def feedparser():
    import feedparser
    return feedparser


@pytest.mark.parametrize("url", (
    "http://localhost",
    "feed:http://localhost",
    "feed://localhost",
))
def test_feedparser_external(feedparser, server, url):
    url = url + ':' + str(server.port)

    @validate_transaction_metrics(
        "test_feedparser_external",
        background_task=True,
        scoped_metrics=(("External/localhost:%d/feedparser/GET" % server.port, 1),),
    )
    @background_task(name="test_feedparser_external")
    def _test():
        feed = feedparser.parse(url)
        assert feed["feed"]["link"] == u"https://pypi.org/"

    _test()


@pytest.mark.parametrize("stream", (True, False))
def test_feedparser_file(feedparser, stream, server):

    @validate_transaction_metrics(
        "test_feedparser_file",
        background_task=True,
        scoped_metrics=(("External/localhost:%d/feedparser/GET" % server.port, None),),
    )
    @background_task(name="test_feedparser_file")
    def _test():
        if stream:
            with open("packages.xml", "rb") as f:
                feed = feedparser.parse(f)
        else:
            feed = feedparser.parse("packages.xml")
        assert feed["feed"]["link"] == u"https://pypi.org/"

    _test()


@pytest.mark.parametrize("url", (
    "http://localhost",
    "packages.xml",
))
def test_feedparser_no_transaction(feedparser, server, url):
    if url.startswith('http://'):
        url = url + ':' + str(server.port)
    feed = feedparser.parse(url)
    assert feed["feed"]["link"] == u"https://pypi.org/"
