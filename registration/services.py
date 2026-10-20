import requests

from django.conf import settings


class WhatsAppAPIError(Exception):
    pass


def send_whatsapp_verification_code(
    phone,
    code
):
    """
    Реальная отправка OTP через
    Meta WhatsApp Cloud API.
    """

    access_token = (
        settings.WHATSAPP_ACCESS_TOKEN
    )

    phone_number_id = (
        settings.WHATSAPP_PHONE_NUMBER_ID
    )

    api_version = (
        settings.WHATSAPP_API_VERSION
    )

    template_name = (
        settings.WHATSAPP_OTP_TEMPLATE
    )

    template_language = (
        settings.WHATSAPP_TEMPLATE_LANGUAGE
    )


    if not access_token:
        raise WhatsAppAPIError(
            "WHATSAPP_ACCESS_TOKEN не настроен."
        )


    if not phone_number_id:
        raise WhatsAppAPIError(
            "WHATSAPP_PHONE_NUMBER_ID не настроен."
        )


    if not api_version:
        raise WhatsAppAPIError(
            "WHATSAPP_API_VERSION не настроен."
        )


    # Meta принимает номер без +
    recipient = "".join(
        char
        for char in phone
        if char.isdigit()
    )


    url = (
        f"https://graph.facebook.com/"
        f"{api_version}/"
        f"{phone_number_id}/messages"
    )


    headers = {
        "Authorization": (
            f"Bearer {access_token}"
        ),
        "Content-Type": "application/json",
    }


    payload = {
        "messaging_product": "whatsapp",

        "recipient_type": "individual",

        "to": recipient,

        "type": "template",

        "template": {
            "name": template_name,

            "language": {
                "code": template_language
            },

            "components": [

                # Сам код в сообщении
                {
                    "type": "body",

                    "parameters": [
                        {
                            "type": "text",
                            "text": str(code)
                        }
                    ]
                },

                # Кнопка "Копировать код"
                {
                    "type": "button",

                    "sub_type": "url",

                    "index": "0",

                    "parameters": [
                        {
                            "type": "text",
                            "text": str(code)
                        }
                    ]
                },

            ]
        }
    }


    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=15
        )

    except requests.RequestException as error:

        raise WhatsAppAPIError(
            "Не удалось подключиться "
            "к WhatsApp API."
        ) from error


    if not response.ok:

        try:
            error_data = response.json()
        except ValueError:
            error_data = {
                "response": response.text
            }

        raise WhatsAppAPIError(
            f"WhatsApp API error: "
            f"{error_data}"
        )


    data = response.json()


    messages = data.get(
        "messages",
        []
    )


    if not messages:

        raise WhatsAppAPIError(
            "WhatsApp API не вернул "
            "ID отправленного сообщения."
        )


    return {
        "message_id": messages[0].get("id"),
        "recipient": recipient,
    }