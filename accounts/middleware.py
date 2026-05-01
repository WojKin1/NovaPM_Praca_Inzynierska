from django.shortcuts import redirect

EXEMPT_PATHS = {'/password/change/', '/logout/'}
EXEMPT_PREFIXES = ('/admin/', '/static/')


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and getattr(request.user, 'must_change_password', False)
            and request.path not in EXEMPT_PATHS
            and not any(request.path.startswith(p) for p in EXEMPT_PREFIXES)
        ):
            return redirect('password_change_forced')
        return self.get_response(request)
