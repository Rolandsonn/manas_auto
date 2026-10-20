# registration/urls.py

from django.urls import path

from . import views


app_name = "registration"


urlpatterns = [

    path(
        "register/",
        views.register_view,
        name="register"
    ),

    path(
        "verify-phone/",
        views.verify_phone_view,
        name="verify_phone"
    ),

    path(
        "verify-phone/resend/",
        views.resend_phone_code,
        name="resend_phone_code"
    ),

    path(
        "login/",
        views.login_view,
        name="login"
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),

    path(
        "profile/",
        views.profile_view,
        name="profile"
    ),

    path(
        "profile/edit/",
        views.edit_profile_view,
        name="edit_profile"
    ),

]