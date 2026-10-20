from django import forms
from listings.models import Listing


class ListingForm(forms.ModelForm):

    class Meta:
        model = Listing

        fields = [
            "category",
            "title",
            "brand",
            "car_model",
            "price",
            "year",
            "mileage",
        ]

        widgets = {

            "category": forms.Select(
                attrs={
                    "class": "listing-input"
                }
            ),

            "title": forms.TextInput(
                attrs={
                    "class": "listing-input",
                    "placeholder": "Например: Toyota Camry 70"
                }
            ),

            "brand": forms.TextInput(
                attrs={
                    "class": "listing-input",
                    "placeholder": "Toyota"
                }
            ),

            "car_model": forms.TextInput(
                attrs={
                    "class": "listing-input",
                    "placeholder": "Camry"
                }
            ),

            "price": forms.NumberInput(
                attrs={
                    "class": "listing-input",
                    "placeholder": "1500000",
                    "min": "0"
                }
            ),

            "year": forms.NumberInput(
                attrs={
                    "class": "listing-input",
                    "placeholder": "2020",
                    "min": "1950"
                }
            ),

            "mileage": forms.NumberInput(
                attrs={
                    "class": "listing-input",
                    "placeholder": "85000",
                    "min": "0"
                }
            ),
        }