from newrelic.agent import (wrap_function_trace)

def name_template_render(self, *args, **kwargs):
    return "%s Template" % (self.name or self.filename)

def name_template_compile(self, source, name=None, filename=None, raw=False,
            defer_init=False):
    return "%s Compile" % (name or '<template>')

def instrument(module):

    wrap_function_trace('jinja2.environment', 'Template.render',
            name_template_render)
    wrap_function_trace('jinja2.environment', 'Environment.compile',
            name_template_compile)
