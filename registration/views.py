# registration/views.py

import logging
import re
import secrets
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import (
    check_password,
    make_password,
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from listings.models import Listing

from .models import Profile
from .services import (
    WhatsAppAPIError,
    send_whatsapp_verification_code,
)


User = get_user_model()

logger = logging.getLogger(__name__)


# =========================================================
# НОРМАЛИЗАЦИЯ ТЕЛЕФОНА
# =========================================================

def normalize_phone(phone):
    """
    Приводит кыргызстанский номер к формату:

    +996555123456
    """

    digits = re.sub(
        r"\D",
        "",
        phone
    )

    # +996 555 123 456
    if (
        digits.startswith("996")
        and len(digits) == 12
    ):
        return f"+{digits}"

    # 0555 123 456
    if (
        digits.startswith("0")
        and len(digits) == 10
    ):
        digits = digits[1:]

    # 555 123 456
    if len(digits) == 9:
        return f"+996{digits}"

    raise ValueError(
        "Введите номер Кыргызстана "
        "в формате +996 555 123 456."
    )


# =========================================================
# РЕГИСТРАЦИЯ
# =========================================================

def register_view(request):

    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip().lower()

        phone_raw = request.POST.get(
            "phone",
            ""
        ).strip()

        password1 = request.POST.get(
            "password1",
            ""
        )

        password2 = request.POST.get(
            "password2",
            ""
        )

        agreement = request.POST.get(
            "agreement"
        )


        context = {
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "email": email,
            "phone": phone_raw,
            "agreement": agreement,
        }


        # =================================================
        # ИМЯ
        # =================================================

        if not first_name:

            messages.error(
                request,
                "Введите имя."
            )

            return render(
                request,
                "registration/register.html",
                context
            )


        # =================================================
        # ЛОГИН
        # =================================================

        if not username:

            messages.error(
                request,
                "Введите логин."
            )

            return render(
                request,
                "registration/register.html",
                context
            )


        if User.objects.filter(
            username__iexact=username
        ).exists():

            messages.error(
                request,
                "Пользователь с таким логином "
                "уже существует."
            )

            return render(
                request,
                "registration/register.html",
                context
            )


        # =================================================
        # EMAIL
        # =================================================

        if not email:

            messages.error(
                request,
                "Введите Email."
            )

            return render(
                request,
                "registration/register.html",
                context
            )


        try:

            validate_email(email)

        except ValidationError:

            messages.error(
                request,
                "Введите корректный Email."
            )

            return render(
                request,
                "registration/register.html",
                context
            )


        if User.objects.filter(
            email__iexact=email
        ).exists():

            messages.error(
                request,
                "Этот Email уже используется."
            )

            return render(
                request,
                "registration/register.html",
                context
            )


        # =================================================
        # ТЕЛЕФОН
        # =================================================

        if not phone_raw:

            messages.error(
                request,
                "Введите номер телефона."
            )

            return render(
                request,
                "registration/register.html",
                context
            )


        try:

            phone = normalize_phone(
                phone_raw
            )

        except ValueError as error:

            messages.error(
                request,
                str(error)
            )

            return render(
                request,
                "registration/register.html",
                context
            )


        if Profile.objects.filter(
            phone=phone
        ).exists():

            messages.error(
                request,
                "Этот номер телефона уже зарегистрирован."
            )

            return render(
                request,
                "registration/register.html",
                context
            )


        # =================================================
        # СОГЛАШЕНИЕ
        # =================================================

        if not agreement:

            messages.error(
                request,
                "Необходимо принять "
                "Пользовательское соглашение "
                "и Политику конфиденциальности."
            )

            return render(
                request,
                "registration/register.html",
                context
            )


        # =================================================
        # ПАРОЛЬ
        # =================================================

        if not password1:

            messages.error(
                request,
                "Введите пароль."
            )

            return render(
                request,
                "registration/register.html",
                context
            )


        if password1 != password2:

            messages.error(
                request,
                "Пароли не совпадают."
            )

            return render(
                request,
                "registration/register.html",
                context
            )


        temp_user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )


        try:

            validate_password(
                password1,
                user=temp_user
            )

        except ValidationError as error:

            for message in error.messages:

                messages.error(
                    request,
                    message
                )

            return render(
                request,
                "registration/register.html",
                context
            )


        # =================================================
        # ГЕНЕРИРУЕМ 4-ЗНАЧНЫЙ КОД
        # =================================================

        verification_code = str(
            secrets.randbelow(9000) + 1000
        )

        now_timestamp = (
            timezone.now().timestamp()
        )


        # =================================================
        # ВРЕМЕННО СОХРАНЯЕМ ДАННЫЕ
        # =================================================

        request.session[
            "pending_registration"
        ] = {

            "first_name": first_name,

            "last_name": last_name,

            "username": username,

            "email": email,

            "phone": phone,

            # Пароль не храним открытым
            "password_hash": make_password(
                password1
            ),

            # Код тоже храним только как hash
            "code_hash": make_password(
                verification_code
            ),

            # Код действует 5 минут
            "expires_at": (
                now_timestamp + 300
            ),

            # Новый код можно запросить
            # через 60 секунд
            "resend_at": (
                now_timestamp + 60
            ),

            # Количество неправильных попыток
            "attempts": 0,
        }


        request.session.modified = True


        # =================================================
        # ОТПРАВЛЯЕМ КОД В WHATSAPP
        # =================================================

        try:

            send_whatsapp_verification_code(
                phone,
                verification_code
            )

        except WhatsAppAPIError as error:

            request.session.pop(
                "pending_registration",
                None
            )

            logger.error(
                "Ошибка отправки WhatsApp OTP: %s",
                error
            )

            messages.error(
                request,
                "Не удалось отправить код в WhatsApp. "
                "Проверьте номер телефона и попробуйте снова."
            )

            return render(
                request,
                "registration/register.html",
                context
            )


        messages.success(
            request,
            "Код подтверждения отправлен в WhatsApp."
        )


        return redirect(
            "registration:verify_phone"
        )


    return render(
        request,
        "registration/register.html"
    )


# =========================================================
# ПОДТВЕРЖДЕНИЕ ТЕЛЕФОНА
# =========================================================

def verify_phone_view(request):

    pending = request.session.get(
        "pending_registration"
    )


    if not pending:

        messages.error(
            request,
            "Сначала заполните форму регистрации."
        )

        return redirect(
            "registration:register"
        )


    now_timestamp = (
        timezone.now().timestamp()
    )


    if request.method == "POST":

        # ================================================
        # ПОЛУЧАЕМ 4 ЦИФРЫ
        # ================================================

        code = (
            request.POST.get(
                "code_1",
                ""
            ).strip()

            + request.POST.get(
                "code_2",
                ""
            ).strip()

            + request.POST.get(
                "code_3",
                ""
            ).strip()

            + request.POST.get(
                "code_4",
                ""
            ).strip()
        )


        # ================================================
        # ФОРМАТ КОДА
        # ================================================

        if (
            len(code) != 4
            or not code.isdigit()
        ):

            messages.error(
                request,
                "Введите 4-значный код."
            )

            return render(
                request,
                "registration/verify_phone.html",
                {
                    "phone": pending["phone"]
                }
            )


        # ================================================
        # ПРОВЕРЯЕМ СРОК
        # ================================================

        if now_timestamp > pending.get(
            "expires_at",
            0
        ):

            messages.error(
                request,
                "Код подтверждения истёк. "
                "Отправьте новый код."
            )

            return render(
                request,
                "registration/verify_phone.html",
                {
                    "phone": pending["phone"]
                }
            )


        # ================================================
        # ПОПЫТКИ
        # ================================================

        attempts = pending.get(
            "attempts",
            0
        )


        if attempts >= 5:

            request.session.pop(
                "pending_registration",
                None
            )

            messages.error(
                request,
                "Слишком много неправильных попыток. "
                "Начните регистрацию заново."
            )

            return redirect(
                "registration:register"
            )


        # ================================================
        # ПРОВЕРЯЕМ КОД
        # ================================================

        if not check_password(
            code,
            pending["code_hash"]
        ):

            attempts += 1

            pending[
                "attempts"
            ] = attempts

            request.session[
                "pending_registration"
            ] = pending

            request.session.modified = True


            attempts_left = (
                5 - attempts
            )


            if attempts_left <= 0:

                request.session.pop(
                    "pending_registration",
                    None
                )

                messages.error(
                    request,
                    "Количество попыток исчерпано. "
                    "Начните регистрацию заново."
                )

                return redirect(
                    "registration:register"
                )


            messages.error(
                request,
                f"Неверный код. "
                f"Осталось попыток: "
                f"{attempts_left}."
            )

            return render(
                request,
                "registration/verify_phone.html",
                {
                    "phone": pending["phone"]
                }
            )


        # ================================================
        # КОД ПРАВИЛЬНЫЙ
        #
        # ЕЩЁ РАЗ ПРОВЕРЯЕМ УНИКАЛЬНОСТЬ
        # ================================================

        if User.objects.filter(
            username__iexact=pending[
                "username"
            ]
        ).exists():

            request.session.pop(
                "pending_registration",
                None
            )

            messages.error(
                request,
                "Этот логин уже зарегистрирован."
            )

            return redirect(
                "registration:register"
            )


        if User.objects.filter(
            email__iexact=pending[
                "email"
            ]
        ).exists():

            request.session.pop(
                "pending_registration",
                None
            )

            messages.error(
                request,
                "Этот Email уже зарегистрирован."
            )

            return redirect(
                "registration:register"
            )


        if Profile.objects.filter(
            phone=pending[
                "phone"
            ]
        ).exists():

            request.session.pop(
                "pending_registration",
                None
            )

            messages.error(
                request,
                "Этот номер телефона уже зарегистрирован."
            )

            return redirect(
                "registration:register"
            )


        # ================================================
        # СОЗДАЁМ USER ТОЛЬКО ПОСЛЕ
        # ПОДТВЕРЖДЕНИЯ ТЕЛЕФОНА
        # ================================================

        with transaction.atomic():

            user = User(
                username=pending[
                    "username"
                ],

                email=pending[
                    "email"
                ],

                first_name=pending[
                    "first_name"
                ],

                last_name=pending[
                    "last_name"
                ],
            )


            # Здесь уже Django-хеш пароля
            user.password = pending[
                "password_hash"
            ]

            user.save()


            # Если Profile создаётся signal-ом,
            # используем get_or_create
            profile, created = (
                Profile.objects.get_or_create(
                    user=user
                )
            )


            profile.phone = pending[
                "phone"
            ]

            profile.save()


        # ================================================
        # УДАЛЯЕМ ВРЕМЕННУЮ РЕГИСТРАЦИЮ
        # ================================================

        request.session.pop(
            "pending_registration",
            None
        )


        messages.success(
            request,
            "Телефон подтверждён. "
            "Регистрация успешно завершена."
        )


        return redirect(
            "registration:login"
        )


    # =====================================================
    # GET
    # =====================================================

    code_expired = (
        now_timestamp
        >
        pending.get(
            "expires_at",
            0
        )
    )


    return render(
        request,
        "registration/verify_phone.html",
        {
            "phone": pending["phone"],
            "code_expired": code_expired,
        }
    )


# =========================================================
# ПОВТОРНАЯ ОТПРАВКА КОДА
# =========================================================

@require_POST
def resend_phone_code(request):

    pending = request.session.get(
        "pending_registration"
    )


    if not pending:

        messages.error(
            request,
            "Данные регистрации не найдены."
        )

        return redirect(
            "registration:register"
        )


    now_timestamp = (
        timezone.now().timestamp()
    )


    # =====================================================
    # НЕ ДАЁМ СПАМИТЬ ОТПРАВКОЙ
    # =====================================================

    resend_at = pending.get(
        "resend_at",
        0
    )


    if now_timestamp < resend_at:

        seconds = max(
            1,
            int(
                resend_at
                - now_timestamp
            )
        )

        messages.error(
            request,
            f"Повторно отправить код "
            f"можно через {seconds} сек."
        )

        return redirect(
            "registration:verify_phone"
        )


    # =====================================================
    # НОВЫЙ КОД
    # =====================================================

    verification_code = str(
        secrets.randbelow(9000) + 1000
    )


    pending[
        "code_hash"
    ] = make_password(
        verification_code
    )


    pending[
        "expires_at"
    ] = (
        now_timestamp + 300
    )


    pending[
        "resend_at"
    ] = (
        now_timestamp + 60
    )


    pending[
        "attempts"
    ] = 0


    request.session[
        "pending_registration"
    ] = pending

    request.session.modified = True


    # =====================================================
    # WHATSAPP
    # =====================================================

    try:

        send_whatsapp_verification_code(
            pending["phone"],
            verification_code
        )

    except WhatsAppAPIError as error:

        logger.error(
            "Ошибка повторной отправки "
            "WhatsApp OTP: %s",
            error
        )

        messages.error(
            request,
            "Не удалось повторно отправить "
            "код в WhatsApp."
        )

        return redirect(
            "registration:verify_phone"
        )


    messages.success(
        request,
        "Новый код отправлен в WhatsApp."
    )


    return redirect(
        "registration:verify_phone"
    )


# =========================================================
# ВХОД
# =========================================================

def login_view(request):

    if request.user.is_authenticated:
        return redirect(
            "core:home"
        )


    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )


        # =================================================
        # ПРОВЕРКА ПОЛЕЙ
        # =================================================

        if not username:

            messages.error(
                request,
                "Введите имя пользователя."
            )

            return render(
                request,
                "registration/login.html",
                {
                    "username": username
                }
            )


        if not password:

            messages.error(
                request,
                "Введите пароль."
            )

            return render(
                request,
                "registration/login.html",
                {
                    "username": username
                }
            )


        # =================================================
        # ИЩЕМ ПОЛЬЗОВАТЕЛЯ
        # =================================================

        try:

            db_user = User.objects.get(
                username=username
            )

        except User.DoesNotExist:

            messages.error(
                request,
                "Пользователь с таким "
                "логином не найден."
            )

            return render(
                request,
                "registration/login.html",
                {
                    "username": username
                }
            )


        # =================================================
        # АКТИВЕН ЛИ АККАУНТ
        # =================================================

        if not db_user.is_active:

            messages.error(
                request,
                "Ваш аккаунт заблокирован."
            )

            return render(
                request,
                "registration/login.html",
                {
                    "username": username
                }
            )


        # =================================================
        # ПРОВЕРКА ПАРОЛЯ
        # =================================================

        user = authenticate(
            request,
            username=username,
            password=password
        )


        if user is None:

            messages.error(
                request,
                "Неверный пароль."
            )

            return render(
                request,
                "registration/login.html",
                {
                    "username": username
                }
            )


        # =================================================
        # ВХОД
        # =================================================

        login(
            request,
            user
        )


        messages.success(
            request,
            f"Добро пожаловать, "
            f"{user.username}!"
        )


        # =================================================
        # NEXT
        # =================================================

        next_url = (
            request.POST.get("next")
            or
            request.GET.get("next")
        )


        if (
            next_url
            and
            url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={
                    request.get_host()
                },
                require_https=(
                    request.is_secure()
                ),
            )
        ):

            return redirect(
                next_url
            )


        return redirect(
            "core:home"
        )


    return render(
        request,
        "registration/login.html"
    )


# =========================================================
# ВЫХОД
# =========================================================

def logout_view(request):

    if request.user.is_authenticated:

        logout(
            request
        )

        messages.success(
            request,
            "Вы успешно вышли из аккаунта."
        )


    return redirect(
        "core:home"
    )


# =========================================================
# ПРОФИЛЬ
# =========================================================

@login_required(
    login_url="registration:login"
)
def profile_view(request):

    profile, created = (
        Profile.objects.get_or_create(
            user=request.user
        )
    )


    listings = Listing.objects.filter(
        owner=request.user
    ).order_by(
        "-created_at"
    )


    context = {
        "profile": profile,
        "listings": listings,
        "listings_count": (
            listings.count()
        ),
    }


    return render(
        request,
        "registration/profile.html",
        context
    )


# =========================================================
# РЕДАКТИРОВАНИЕ ПРОФИЛЯ
# =========================================================

@login_required(
    login_url="registration:login"
)
def edit_profile_view(request):

    user = request.user


    profile, created = (
        Profile.objects.get_or_create(
            user=user
        )
    )


    if request.method == "POST":

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip().lower()

        avatar = request.FILES.get(
            "avatar"
        )


        # =================================================
        # ИМЯ
        # =================================================

        if not first_name:

            messages.error(
                request,
                "Введите имя."
            )

            return redirect(
                "registration:edit_profile"
            )


        # =================================================
        # USERNAME
        # =================================================

        if not username:

            messages.error(
                request,
                "Введите логин."
            )

            return redirect(
                "registration:edit_profile"
            )


        if User.objects.filter(
            username__iexact=username
        ).exclude(
            id=user.id
        ).exists():

            messages.error(
                request,
                "Этот логин уже занят."
            )

            return redirect(
                "registration:edit_profile"
            )


        # =================================================
        # EMAIL
        # =================================================

        if not email:

            messages.error(
                request,
                "Введите Email."
            )

            return redirect(
                "registration:edit_profile"
            )


        try:

            validate_email(
                email
            )

        except ValidationError:

            messages.error(
                request,
                "Введите корректный Email."
            )

            return redirect(
                "registration:edit_profile"
            )


        if User.objects.filter(
            email__iexact=email
        ).exclude(
            id=user.id
        ).exists():

            messages.error(
                request,
                "Этот Email уже используется."
            )

            return redirect(
                "registration:edit_profile"
            )


        # =================================================
        # СОХРАНЕНИЕ
        # =================================================

        user.first_name = first_name

        user.last_name = last_name

        user.username = username

        user.email = email

        user.save()


        if avatar:

            profile.avatar = avatar


        profile.save()


        messages.success(
            request,
            "Профиль успешно обновлён."
        )


        return redirect(
            "registration:profile"
        )


    context = {
        "profile": profile
    }


    return render(
        request,
        "registration/edit_profile.html",
        context
    )