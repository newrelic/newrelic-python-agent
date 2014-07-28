from django.http import HttpResponse
from django.views.generic.base import View

def index(request):
    return HttpResponse('INDEX RESPONSE')

class MyView(View):
    def get(self, request):
        return HttpResponse('CBV RESPONSE')

def deferred_cbv(request):
    return MyView.as_view()(request)

def html_insertion(request):
    return HttpResponse('<!DOCTYPE html><html><head>Some header</head>'
            '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
            '</body></html>')
