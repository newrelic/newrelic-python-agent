from django import template

register = template.Library()

@register.inclusion_tag('results.html')
def show_results():
    return {'results' : 'Inclusion tag'}
