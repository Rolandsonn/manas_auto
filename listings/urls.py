from django.urls import path
from . import views

app_name = "listings"

urlpatterns = [
    path("", views.listing_list, name="list"),
    path(
        "create/",
        views.listing_create,
        name="create"
    ),

  
    path(
        "<int:pk>/",
        views.listing_detail,
        name="detail"
    ),
     path(
        "",
        views.car_list,
        name="car_list"
    ),

    path(
        "new/",
        views.new_cars,
        name="new_cars"
    ),

    path(
        "top/",
        views.top_cars,
        name="top_cars"
    ),
]