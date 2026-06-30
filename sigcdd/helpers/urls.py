from . import views
from django.urls import path
app_name = 'helpers'
from django.urls import re_path as pattern
urlpatterns = [
    path('fakes/', views.list_fakemodel_view, name='list_fakemodel_view'),
    pattern(r'^api/unread_count/$', views.live_unread_notification_count, name='live_unread_notification_count'),
    path('sentry-debug/', views.trigger_sentry_error,name="trigger_sentry_error"),
]
