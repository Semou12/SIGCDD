from django.urls import path

from users.views import user_detail_view, user_redirect_view, user_update_view,home_view,profile_view,user_simple_view

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<str:username>/", view=user_detail_view, name="detail"),
    path("", view=home_view, name="home_view"),
    path("profile", view=profile_view, name="profile_view"),

    path("default", view=user_simple_view, name="user_simple_view"),

]
