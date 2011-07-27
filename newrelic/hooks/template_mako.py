import newrelic.api.function_trace

def name_template_render(template, *args, **kwargs):
    return template.filename or  '--template--'

def instrument(module):

    if module.__name__ == 'mako.runtime':

        newrelic.api.function_trace.wrap_function_trace(
                module, '_render', name_template_render, 'Template/Render')
