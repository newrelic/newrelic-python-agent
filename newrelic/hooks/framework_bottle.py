import newrelic.api.web_transaction
import newrelic.api.out_function
import newrelic.api.name_transaction
import newrelic.api.error_trace
import newrelic.api.function_trace

def instrument(module):

    version = map(int, module.__version__.split('.'))

    def out_Bottle_match(result):
        callback, args = result
        callback = newrelic.api.name_transaction.NameTransactionWrapper(
                callback)
        callback = newrelic.api.error_trace.ErrorTraceWrapper(callback,
                ignore_errors=['bottle.HTTPResponse', 'bottle.RouteReset'])
        return callback, args

    if version >= [0, 9, 0]:
        newrelic.api.web_transaction.wrap_wsgi_application(
                module, 'Bottle.wsgi')

        newrelic.api.out_function.wrap_out_function(
                module, 'Bottle._match', out_Bottle_match)

        newrelic.api.function_trace.wrap_function_trace(
                module, 'SimpleTemplate.render')
        newrelic.api.function_trace.wrap_function_trace(
                module, 'MakoTemplate.render')
        newrelic.api.function_trace.wrap_function_trace(
                module, 'CheetahTemplate.render')
        newrelic.api.function_trace.wrap_function_trace(
                module, 'Jinja2Template.render')
        newrelic.api.function_trace.wrap_function_trace(
                module, 'SimpleTALTemplate.render')

    else:
        newrelic.api.web_transaction.wrap_wsgi_application(
                module, 'Bottle.__call__')

        newrelic.api.out_function.wrap_out_function(
                module, 'Bottle.match_url', out_Bottle_match)

        newrelic.api.function_trace.wrap_function_trace(
                module, 'SimpleTemplate.render')
        newrelic.api.function_trace.wrap_function_trace(
                module, 'MakoTemplate.render')
        newrelic.api.function_trace.wrap_function_trace(
                module, 'CheetahTemplate.render')
        newrelic.api.function_trace.wrap_function_trace(
                module, 'Jinja2Template.render')
