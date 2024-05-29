from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseBadRequest

from utilities.api import is_api_request

from .constants import COOKIE_NAME, CONTEXT_HEADER, QUERY_PARAM
from .models import Context
from .utilities import activate_context

__all__ = (
    'ContextMiddleware',
)


class ContextMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Set/clear the active Context on the request
        try:
            context = self.get_active_context(request)
        except ObjectDoesNotExist:
            return HttpResponseBadRequest("Invalid context identifier")

        with activate_context(context):
            response = self.get_response(request)

        # Set/clear the context cookie (for non-API requests)
        if not is_api_request(request):
            if context:
                response.set_cookie('active_context', context.schema_id)
            elif '_context' in request.GET:
                response.delete_cookie('active_context')

        return response

    @staticmethod
    def get_active_context(request):
        """
        Return the active Context (if any).
        """
        # The active Context is specified by HTTP header for REST API requests.
        if is_api_request(request) and (schema_id := request.headers.get(CONTEXT_HEADER)):
            return Context.objects.get(schema_id=schema_id)

        # Context activated/deactivated by URL query parameter
        elif QUERY_PARAM in request.GET:
            if schema_id := request.GET.get(QUERY_PARAM):
                return Context.objects.get(schema_id=schema_id)
            else:
                request.COOKIES.pop(COOKIE_NAME, None)  # Delete cookie if set
                return None

        # Context set by cookie
        elif schema_id := request.COOKIES.get('active_context'):
            return Context.objects.filter(schema_id=schema_id).first()
