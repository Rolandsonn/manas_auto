from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    avatar = models.ImageField(
        upload_to="users/",
        blank=True,
        null=True
    )

    @property
    def whatsapp_phone(self):
        """
        WhatsApp принимает номер только цифрами:
        +996 555 12 34 56 -> 996555123456
        """
        return "".join(
            char for char in self.phone
            if char.isdigit()
        )

    def __str__(self):
        return self.user.username