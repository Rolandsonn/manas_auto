from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path(
    "listing/create/",
    views.create_listing_view,
    name="create_listing"
    ),
    path(
        "",
        views.home,
        name="home"
    ),
    path(
    "security/",
    views.security,
    name="security"
    ),
    path(
    "help/",
    views.help_page,
    name="help"
    ),
    path(
        "about/",
        views.about,
        name="about"
    ),
    path(
    "contacts/",
    views.contacts,
    name="contacts"
),
    path(
    "privacy/",
    views.privacy,
    name="privacy"
),
    path(
    "terms/",
    views.terms,
    name="terms"
),  
]