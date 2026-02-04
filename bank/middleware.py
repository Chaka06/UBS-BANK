from django.conf import settings
from django.utils import translation


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            preferred = getattr(user, 'preferred_language', None)
            if preferred:
                translation.activate(preferred)
                request.LANGUAGE_CODE = preferred
                if hasattr(request, 'session'):
                    request.session['django_language'] = preferred

        response = self.get_response(request)

        if user and user.is_authenticated:
            preferred = getattr(user, 'preferred_language', None)
            if preferred:
                response.set_cookie(settings.LANGUAGE_COOKIE_NAME, preferred)
        return response
