from newrelic.agent import (wrap_function_trace)

def name_template_render(self, *args, **kwargs):
    return self.name or self.filename

def name_template_compile(self, source, name=None, filename=None, raw=False,
            defer_init=False):
    return name or '--template--'

def instrument(module):

    if module.__name__ == 'jinja2.environment':

        wrap_function_trace(module, 'Template.render',
                name_template_render, 'Template/Render')
        wrap_function_trace(module, 'Environment.compile',
                name_template_compile, 'Template/Compile')
