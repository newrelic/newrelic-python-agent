from fastapi import FastAPI
from testing_support.asgi_testing import AsgiTest
from newrelic.api.transaction import current_transaction

app = FastAPI()


@app.get("/sync")
def sync():
    assert current_transaction() is not None
    return {}


@app.get("/async")
async def non_sync():
    assert current_transaction() is not None
    return {}


target_application = AsgiTest(app)
