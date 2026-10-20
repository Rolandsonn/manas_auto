from listings.models import Listing
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db import transaction

from .models import ContactMessage
from .forms import ListingForm
from listings.models import ListingImage
# Create your views here.
def home(request):
    listings = (
        Listing.objects
        .prefetch_related("images")
        .order_by("-created_at")[:8]
    )
    print(listings)
    context = {
        'listings': listings
    }
    
    return render(request, template_name='home.html', context=context)

def about(request):
    return render(
        request,
        "pages/about.html"
    )

def security(request):
    return render(
        request,
        "pages/security.html"
    )

def help_page(request):
    return render(
        request,
        "pages/help.html"
    )
    



def contacts(request):

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()

        if not name or not email or not subject or not message:
            messages.error(
                request,
                "Пожалуйста, заполните все поля."
            )

            return render(
                request,
                "pages/contacts.html",
                {
                    "name": name,
                    "email": email,
                    "subject": subject,
                    "user_message": message,
                }
            )

        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message,
        )

        messages.success(
            request,
            "Спасибо! Ваше сообщение отправлено."
        )

        return redirect("core:contacts")

    return render(
        request,
        "pages/contacts.html"
    )

def privacy(request):
    return render(
        request,
        "pages/privacy.html"
    )

def terms(request):
    return render(
        request,
        "pages/terms.html"
    )
 
@login_required(login_url="registration:login")
def create_listing_view(request):

    if request.method == "POST":

        form = ListingForm(request.POST)

        images = request.FILES.getlist("images")

        # Проверяем форму
        if form.is_valid():

            # Требуем хотя бы одну фотографию
            if not images:
                messages.error(
                    request,
                    "Добавьте хотя бы одну фотографию автомобиля."
                )

                return render(
                    request,
                    "core/create_listing.html",
                    {
                        "form": form
                    }
                )

            # Ограничиваем количество фотографий
            if len(images) > 10:
                messages.error(
                    request,
                    "Можно загрузить максимум 10 фотографий."
                )

                return render(
                    request,
                    "core/create_listing.html",
                    {
                        "form": form
                    }
                )

            with transaction.atomic():

                # Пока НЕ сохраняем
                listing = form.save(commit=False)

                # Владелец = текущий пользователь
                listing.owner = request.user

                listing.save()


                # Сохраняем фотографии
                for index, image in enumerate(images):

                    ListingImage.objects.create(
                        listing=listing,
                        image=image,

                        # Первая фотография будет главной
                        is_main=(index == 0)
                    )


            messages.success(
                request,
                "Объявление успешно опубликовано!"
            )

            return redirect(
                "registration:profile"
            )

    else:

        form = ListingForm()


    return render(
        request,
        "core/create_listing.html",
        {
            "form": form
        }
    )