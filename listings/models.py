from django.db import models
from django.conf import settings
# Create your models here.
from django.utils import timezone
class Category(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True
    )

    slug = models.SlugField(
        max_length=100,
        unique=True
    )

    def __str__(self):
        return self.name

class Listing(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="listings",
        null=True,
        blank=True
    )
    title = models.CharField(max_length=200,     default="")
    car_model = models.CharField(max_length=200,     default="")
    brand = models.CharField(max_length=200,     default="")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    year = models.PositiveIntegerField()
    mileage = models.PositiveIntegerField()
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    views_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Просмотры"
    )

    is_top = models.BooleanField(
        default=False,
        verbose_name="ТОП"
    )

    top_until = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="ТОП до"
    )

    @property
    def top_active(self):
        return (
            self.is_top
            and self.top_until
            and self.top_until > timezone.now()
        )
    
    
    def __str__(self):
        return f"{self.brand} {self.car_model} {self.year}"
    
class ListingImage(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(
        upload_to="cars/",
        default= "default.png"
    )

    is_main = models.BooleanField(
        default=False
    )
    def __str__(self):
        return f"{self.listing.brand} {self.listing.car_model}"