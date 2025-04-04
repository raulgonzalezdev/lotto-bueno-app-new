import os
import sys
from pathlib import Path
import random
import base64
import json
import asyncio
from io import BytesIO
import requests

# Añadir el directorio donde se encuentra whatsapp_chatbot_python al PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parent.parent))

from whatsapp_chatbot_python import GreenAPIBot, Notification
from fastapi import HTTPException
from app.schemas import CedulaRequest
from app.main import get_db, send_message, send_qr_code, obtener_numero_contacto, enviar_contacto, verificar_cedula

API_INSTANCE = os.getenv("API_INSTANCE", "7103945340")
API_TOKEN = os.getenv("API_TOKEN", "fb1cffd3cfa14663a0bf5760528293c3fc0993da4b8b4c19ac")
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")

bot = GreenAPIBot(API_INSTANCE, API_TOKEN)

@bot.router.message(command="start")
def message_handler(notification: Notification) -> None:
    sender_data = notification.event["senderData"]
    sender_name = sender_data["senderName"]
    notification.answer(
        f"👋 Hola, {sender_name}. Para validar tu registro, por favor envíame tu número de cédula."
    )

@bot.router.message()
def obtener_cedula(notification: Notification) -> None:
    sender = notification.sender
    message_data = notification.event.get("messageData", {})

    # Intentar obtener la cédula de ambas posibles estructuras
    extended_text_message_data = message_data.get("extendedTextMessageData", {})
    cedula = extended_text_message_data.get("textMessage") or extended_text_message_data.get("text")

    if not cedula:
        text_message_data = message_data.get("textMessageData", {})
        cedula = text_message_data.get("textMessage")

    print(f"message_data: {message_data}")
    print(f"cedula: {cedula}")

    if not cedula:
        notification.answer(f"Por favor envíame un número de cédula válido. Datos recibidos: {json.dumps(message_data, indent=2)}")
        return

    print(f"Procesando cédula: {cedula}")
    db = next(get_db())
    elector_response = asyncio.run(verificar_cedula(CedulaRequest(numero_cedula=cedula), db))

    if elector_response.get("elector"):
        elector_data = elector_response.get("elector")
        nombre_completo = f"{elector_data['p_nombre']} {elector_data['s_nombre']} {elector_data['p_apellido']} {elector_data['s_apellido']}"
        

        # Llamada a la API para obtener el ticket por cédula
        try:
            response = requests.get(f"{FASTAPI_BASE_URL}/tickets/cedula/{cedula}")
            response.raise_for_status()
            existing_ticket = response.json()
            print(f"Ticket encontrado: {existing_ticket}")
            chat_id = existing_ticket["telefono"]

            qr_code_base64 = existing_ticket["qr_ticket"]
            qr_buf = BytesIO(base64.b64decode(qr_code_base64))

            message = f"{nombre_completo}, hoy es tu día de suerte!\n\n" \
                      f"Desde este momento estás participando en el Lotto Bueno y este es tu número de ticket {existing_ticket['id']} ¡El número ganador!\n\n" \
                      f"Es importante que guardes nuestro contacto, así podremos anunciarte que tú eres el afortunado ganador.\n" \
                      f"No pierdas tu número de ticket y guarda nuestro contacto, ¡prepárate para celebrar!\n\n" \
                      f"¡Mucha suerte!\n" \
                      f"Lotto Bueno: ¡Tu mejor oportunidad de ganar!"

            send_message(chat_id, message)
            send_qr_code(chat_id, qr_buf)

            phone_contact = obtener_numero_contacto(db)
            print(f"phone_contact: {phone_contact}")
            if phone_contact:
                enviar_contacto(chat_id, phone_contact.split('@')[0], "Lotto", "Bueno", "Lotto Bueno Inc")

            notification.answer("Gracias por registrarte. ¡Hasta pronto!")
            notification.state_manager.delete_state(sender)
        except requests.HTTPError as http_err:
            print(f"HTTP error: {http_err}")
            notification.answer(f"Error al obtener ticket: {http_err}")
        except Exception as err:
            print(f"Unexpected error: {err}")
            notification.answer(f"Error inesperado: {err}")
    else:
        print("Cédula no registrada.")
        notification.answer("El número de cédula proporcionado no está registrado. Por favor intenta nuevamente.")

if __name__ == "__main__":
    bot.run_forever()
