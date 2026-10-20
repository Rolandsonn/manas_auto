from django.contrib import admin
from .models import Listing, ListingImage, Category
# Register your models here.
admin.site.register(Listing)
admin.site.register(ListingImage)
admin.site.register(Category)