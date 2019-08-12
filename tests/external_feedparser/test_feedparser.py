import pytest
from newrelic.api.background_task import background_task
from testing_support.fixtures import validate_transaction_metrics


@pytest.fixture(scope="session")
def feedparser():
    import feedparser
    return feedparser


@pytest.mark.parametrize("url", (
    "http://localhost:8989",
    "feed:http://localhost:8989",
    "feed://localhost:8989",
))
@validate_transaction_metrics(
    "test_feedparser_external",
    background_task=True,
    scoped_metrics=(("External/localhost:8989/feedparser/GET", 1),),
)
@background_task(name="test_feedparser_external")
def test_feedparser_external(feedparser, server, url):
    feed = feedparser.parse(url)
    assert feed["feed"]["link"] == u"https://pypi.org/"


@pytest.mark.parametrize("stream", (True, False))
@validate_transaction_metrics(
    "test_feedparser_file",
    background_task=True,
    scoped_metrics=(("External/localhost:8989/feedparser/GET", None),),
)
@background_task(name="test_feedparser_file")
def test_feedparser_file(feedparser, stream):
    if stream:
        with open("packages.xml", "rb") as f:
            feed = feedparser.parse(f)
    else:
        feed = feedparser.parse("packages.xml")
    assert feed["feed"]["link"] == u"https://pypi.org/"


@pytest.mark.parametrize("url", (
    "http://localhost:8989",
    "packages.xml",
))
def test_feedparser_no_transaction(feedparser, server, url):
    feed = feedparser.parse(url)
    assert feed["feed"]["link"] == u"https://pypi.org/"
