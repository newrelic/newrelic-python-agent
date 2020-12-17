from mako.template import Template
from testing_support.fixtures import validate_transaction_metrics
from newrelic.api.background_task import background_task


@validate_transaction_metrics(
    'test_render',
    background_task=True,
    scoped_metrics=(('Template/Render/<template>', 1),),
)
@background_task(name='test_render')
def test_render():
    template = Template("hello, ${name}!")
    result = template.render(name="NR")
    assert result == "hello, NR!"
