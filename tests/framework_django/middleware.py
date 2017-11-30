from django.http import HttpResponseGone


class Custom410(Exception):
    pass


class ExceptionTo410Middleware(object):

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    @staticmethod
    def process_exception(request, exception):
        if isinstance(exception, Custom410):
            return HttpResponseGone()
