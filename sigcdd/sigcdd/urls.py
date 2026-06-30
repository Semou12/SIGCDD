"""sigcdd URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static

from django.views import defaults as default_views
from django.views.generic import TemplateView
from users.views import home_view,SigcddPasswordChangeView

import notifications.urls
urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/", include("allauth_2fa.urls")),
    path('accounts/password/change/',
         SigcddPasswordChangeView.as_view(),
         name='account_change_password'),
    path("accounts/", include("allauth.urls")),
    path("users/", include('users.urls', namespace='users')),
    path("helpers/", include('helpers.urls', namespace='helpers')),
    path("core/", include('core.urls', namespace='core')),
    path("cddaccount/", include('cddaccount.urls', namespace='cddaccount')),
    path("bankcheck/", include('bankcheck.urls', namespace='bankcheck')),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path("", home_view),
    path('inbox/notifications/', include(notifications.urls, namespace='notifications')),
    path('api/', include('api.urls',namespace='api')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:

    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

    from rest_framework.documentation import include_docs_urls
    from rest_framework import authentication, permissions
    from rest_framework.renderers import DocumentationRenderer

    class CustomRenderer(DocumentationRenderer):
        languages = ['python','javascript']
    from drf_yasg.views import get_schema_view
    from drf_yasg import openapi
    schema_view = get_schema_view(
       openapi.Info(
          title="ASTER",
          default_version='v1',
          description="ASTER description",
          terms_of_service="https://www.google.com/policies/terms/",
          contact=openapi.Contact(email="asster.tresor@tresor.com"),
          license=openapi.License(name="BSD License"),
       ),
       public=True,
       #authentication_classes=[authentication.BasicAuthentication],
       permission_classes=[permissions.AllowAny],

       authentication_classes=[authentication.TokenAuthentication],

       #patterns=swaggerapi_urlpatterns,
    )

    urlpatterns += [
       path('swagger(<str:format>\.json|\.yaml)', schema_view.without_ui(cache_timeout=0), name='schema-json'),
       path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
       path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    ]
