
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.conf import settings
from django.shortcuts import redirect
def app_perms_required(group, login_url=None, raise_exception=False):
    """
    Decorator for views that checks whether a user has a group permission,
    redirecting to the log-in page if necessary.
    If the raise_exception parameter is given the PermissionDenied exception
    is raised.
    """
    def check_perms(user):
        if isinstance(group, str):
            groups = (group, )
        else:
            groups = group
        # First check if the user has the permission (even anon users)

        if user.groups.filter(name__in=groups).exists():
            return True
        # In case the 403 handler should be called raise the exception
        if raise_exception:
            raise PermissionDenied
        # As the last resort, show the login form
        return False
    return user_passes_test(check_perms, login_url=login_url)


def user_role_required(role,function=None, raise_exception=True):
    '''
    Decorator for views that checks that the logged in user is a teacher,
    redirects to the log-in page if necessary.
    '''

    if isinstance(role, str):
        groups = (role,)
    else:
        groups = role

    def check_perms(user):
        if not user.is_authenticated:
            return False
        if user.is_active and user.role in groups:
            return True
        else:
            raise PermissionDenied
            #return redirect(change_url)

        if raise_exception:
            raise PermissionDenied
        # In case the 403 handler should be called raise the exception

        return False
    actual_decorator = user_passes_test(check_perms)
    if function:
        return actual_decorator(function)
    return actual_decorator


import functools
from django.shortcuts import redirect
from django.contrib import messages

def user_change_pwd_required(view_func, change_url=settings.FIRST_LOGIN_MODE_REDIRECT_URL):
    """
        this decorator restricts users who have not been verified
        from accessing the view function passed as it argument and
        redirect the user to page where their account can be activated
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if request.user.is_active and request.user.is_authenticated and request.user.force_change_pwd :
            if not settings.FIRST_LOGIN_MODE: return view_func(request, *args, **kwargs)
        messages.info(request, "Merci de changer votre mot de passe")

        return redirect(change_url)
    return wrapper

