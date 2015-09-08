from urllib.parse import urlparse
from django.core.exceptions import PermissionDenied
from django.utils.decorators import available_attrs
from django.utils.six import wraps
from djangle import settings


def user_passes_test_with_403(test_func):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if not logged in and to 403 page if necessary.
    Test should be a callable that takes the user object and returns True if the user passes.

    :param test_func: callable function that takes request User and returns True if the user is allowed to view the page
    :return: render requested page if user has permissions, login page if user isn't authenticated, error 403 if user
    hasn't permissions
    """

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated() and test_func(request.user):
                return view_func(request, *args, **kwargs)
            if request.user.is_authenticated():
                raise PermissionDenied
            path = request.path
            # If the login url is the same scheme and net location then just use
            # the path as the 'next' url.
            login_scheme, login_netloc = urlparse(settings.LOGIN_URL)[:2]
            current_scheme, current_netloc = urlparse(path)[:2]
            if ((not login_scheme or login_scheme == current_scheme) and
                    (not login_netloc or login_netloc == current_netloc)):
                path = request.get_full_path()
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(
                path, settings.LOGIN_URL)
        return _wrapped_view
    return decorator
