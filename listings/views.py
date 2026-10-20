from django.shortcuts import render
from datetime import datetime, timedelta

from django.db.models import F
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import Listing
# Create your views here.
def listing_list(requests):
    return render(requests, 'listings/list.html')
def listing_create(requests):
    return render(requests, "listings/create.html")
def listing_detail(request, pk):
    listing = get_object_or_404(
        Listing,
        pk=pk
    )

    # Владелец объявления не увеличивает
    # количество просмотров своего объявления
    is_owner = (
        request.user.is_authenticated
        and request.user == listing.owner
    )

    if not is_owner:

        # Для каждого объявления создаётся
        # отдельный ключ в сессии браузера
        session_key = f"listing_view_{listing.pk}"

        last_view = request.session.get(session_key)

        should_count = False

        # Пользователь ещё не открывал объявление
        if last_view is None:

            should_count = True

        else:

            try:
                last_view_time = datetime.fromtimestamp(
                    float(last_view),
                    tz=timezone.get_current_timezone()
                )

                # Новый просмотр можно засчитать
                # только спустя 24 часа
                if (
                    timezone.now() - last_view_time
                    >= timedelta(hours=24)
                ):
                    should_count = True

            except (ValueError, TypeError, OverflowError):

                should_count = True


        if should_count:

            # Увеличиваем количество просмотров
            # безопасно на уровне базы данных
            Listing.objects.filter(
                pk=listing.pk
            ).update(
                views_count=F("views_count") + 1
            )

            # Запоминаем время просмотра
            request.session[session_key] = (
                timezone.now().timestamp()
            )

            # Получаем новое значение views_count
            listing.refresh_from_db(
                fields=["views_count"]
            )


    return render(
        request,
        "listings/listing_detail.html",
        {
            "listing": listing
        }
    )


def car_list(request):
    listings = Listing.objects.all().order_by("-created_at")

    context = {
        "listings": listings,
        "page_title": "Автомобили",
        "page_subtitle": "Все автомобили на ManasAuto",
        "page_type": "all",
    }

    return render(
        request,
        "listings/car_list.html",
        context
    )


def new_cars(request):
    seven_days_ago = timezone.now() - timedelta(days=7)

    listings = Listing.objects.filter(
        created_at__gte=seven_days_ago
    ).order_by("-created_at")

    context = {
        "listings": listings,
        "page_title": "Новые объявления",
        "page_subtitle": "Автомобили, добавленные за последние 7 дней",
        "page_type": "new",
    }

    return render(
        request,
        "listings/car_list.html",
        context
    )
from django.utils import timezone


def top_cars(request):

    listings = Listing.objects.filter(
        is_top=True,
        top_until__gt=timezone.now()
    ).order_by(
        "-top_until",
        "-created_at"
    )

    context = {
        "listings": listings,
        "page_title": "ТОП объявления",
        "page_subtitle": "Продвигаемые автомобили на ManasAuto",
        "page_type": "top",
    }

    return render(
        request,
        "listings/car_list.html",
        context
    )