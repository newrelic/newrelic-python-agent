from django.http import HttpResponse

def index(request):
    return HttpResponse('INDEX RESPONSE')

def html_snippet(request):
	return HttpResponse('<!DOCTYPE html><html><head>Some header</head><body><h1>My First Heading</h1><p>My first paragraph.</p></body></html>')