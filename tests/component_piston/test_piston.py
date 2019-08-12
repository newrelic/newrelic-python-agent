from testing_support.fixtures import validate_transaction_metrics


@validate_transaction_metrics(
    "_target_application:MyHandler.read",
    scoped_metrics=(("Function/_target_application:MyHandler.read", 1),),
)
def test_piston(app):
    response = app.get("/")
    assert response.status_code == 200
