# main.py
import os
import random
import string
import qrcode
import json
import base64
import requests
import jwt
import logging
import re
import asyncio
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta, date
from io import StringIO, BytesIO
from fastapi import FastAPI, HTTPException, Depends, Query, APIRouter, Request
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import uvicorn
import threading

from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from werkzeug.security import generate_password_hash, check_password_hash
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy import distinct, case, Integer
from redis.asyncio import Redis

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session

from app.models import (
    Elector,
    Geografico,
    CentroVotacion,
    Ticket,
    Recolector,
    Users,
    LineaTelefonica
)
from app.schemas import (
    LineaTelefonicaList,
    LineaTelefonicaCreate,
    LineaTelefonicaUpdate,
    RecolectorEstadisticas,
    ElectorList,
    UserCreate,
    UserList,
    GeograficoList,
    CentroVotacionList,
    TicketUpdate,
    TicketCreate,
    TicketList,
    RecolectorCreate,
    RecolectorList,
    RecolectorUpdate,
    ElectorCreate,
    GeograficoCreate,
    CentroVotacionCreate,
    ElectorDetail
)
from dotenv import load_dotenv
from whatsapp_chatbot_python import GreenAPIBot, Notification
import zipfile
import math

load_dotenv()

# Definir las posibles URLs de conexión
DATABASE_URLS = [
    "postgresql+psycopg2://lottobueno:lottobueno@postgres:5432/lottobueno"
]

CHUNK_SIZE = 100000  # Tamaño del lote

engine = None
SessionLocal = None

for db_url in DATABASE_URLS:
    try:
        engine = create_engine(db_url)
        # Probar la conexión
        with engine.connect() as conn:
            print(f"Conectado exitosamente usando: {db_url}")
            break  # Salir del bucle si la conexión es exitosa
    except SQLAlchemyError as e:
        print(f"Fallo al conectar usando {db_url}: {e}")

if engine is not None:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    print("No se pudo establecer conexión con ninguna de las bases de datos proporcionadas.")
    os._exit(1)

# Base declarativa para los modelos
Base = declarative_base()

app = FastAPI()


def to_dict(obj):
    return obj.__dict__


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Configuración de CORS
origins = [
    "http://localhost:8000",
    "http://localhost:3000",
    "https://7103.api.greenapi.com",
    "http://localhost",
    "https://localhost",
    "http://127.0.0.1:8000",
    "http://127.0.0.1",
    "https://wa.me"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Asignar valores por defecto si las variables de entorno no están definidas
POSTGRES_DB = os.getenv("POSTGRES_DB", "lottobueno")
POSTGRES_USER = os.getenv("POSTGRES_USER", "lottobueno")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "lottobueno")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres:5432/{POSTGRES_DB}"
)

API_INSTANCE = os.getenv("API_INSTANCE", "7103945340")
API_URL_BASE = os.getenv("API_URL_BASE", f"https://7103.api.greenapi.com/waInstance{API_INSTANCE}")
API_TOKEN = os.getenv("API_TOKEN", "fb1cffd3cfa14663a0bf5760528293c3fc0993da4b8b4c19ac")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
COMPANY_PHONE_CONTACT = os.getenv("COMPANY_PHONE_CONTACT", "584262831867")
SECRET_KEY = os.getenv("SECRET_KEY", "J-yMKNjjVaUJUj-vC-cAun_qlyXH68p55er0WIlgFuo")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Verificar que las variables requeridas están presentes
if not API_INSTANCE or not API_TOKEN:
    raise ValueError("API_INSTANCE y API_TOKEN deben estar definidos en las variables de entorno")

BASE_DIR = Path(__file__).resolve().parent

redis = Redis.from_url(REDIS_URL, decode_responses=True)


class PhoneNumberRequest(BaseModel):
    phone_number: str


class MessageRequest(BaseModel):
    chat_id: str
    message: str


class CedulaRequest(BaseModel):
    numero_cedula: str


class ContactRequest(BaseModel):
    chat_id: str
    phone_contact: str
    first_name: str
    last_name: str
    company: str


class TicketRequest(BaseModel):
    cedula: str
    telefono: str
    referido_id: Optional[int] = None
    
    
class Estado(BaseModel):
    codigo_estado: int
    estado: str


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def check_whatsapp(phone_number: str):
    url = f"{API_URL_BASE}/checkWhatsapp/{API_TOKEN}"
    payload = json.dumps({"phoneNumber": phone_number})
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        return {"status": "api", "message": "Error de HTTP en la verificación de WhatsApp"}
    except Exception as err:
        return {"status": "error", "message": "No se pudo conectar a la API de verificación de WhatsApp"}


def compress_file(file_bytes: BytesIO, filename: str) -> BytesIO:
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zip_file:
        zip_file.writestr(filename, file_bytes.getvalue())
    zip_buffer.seek(0)
    return zip_buffer


def generate_file_responses(data, file_type, base_filename):
    try:
        if file_type == 'excel':
            excel_buffer = BytesIO()
            workbook = pd.ExcelWriter(excel_buffer, engine='xlsxwriter')
            df = pd.DataFrame(data)
            df.to_excel(workbook, sheet_name=base_filename, index=False)

            # Obtener el objeto worksheet para dar formato
            worksheet = workbook.sheets[base_filename]

            # Ajustar el ancho de las columnas automáticamente
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                worksheet.set_column(idx, idx, max_length + 2)

            workbook.close()
            excel_buffer.seek(0)

            # Comprimir el archivo Excel
            filename = f"{base_filename}.xlsx"
            zip_buffer = compress_file(excel_buffer, filename)
            return [zip_buffer]

        elif file_type == 'txt':
            # Convertir a DataFrame y luego a texto con tabulaciones
            df = pd.DataFrame(data)
            output = StringIO()
            df.to_csv(output, sep='\t', index=False, encoding='utf-8')
            output.seek(0)

            # Comprimir el archivo de texto
            txt_buffer = BytesIO(output.getvalue().encode('utf-8'))
            filename = f"{base_filename}.txt"
            zip_buffer = compress_file(txt_buffer, filename)
            return [zip_buffer]

    except Exception as e:
        print(f"Error en generate_file_responses: {str(e)}")
        raise


app.mount(
    "/static/_next",
    StaticFiles(directory=BASE_DIR / "frontend/out/_next"),
    name="next-assets",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend/out"), name="app")


@app.get("/")
@app.head("/")
async def serve_frontend():
    return FileResponse(os.path.join(BASE_DIR, "frontend/out/index.html"))


@app.post("/api/check_whatsapp")
def api_check_whatsapp(request: PhoneNumberRequest):
    result = check_whatsapp(request.phone_number)
    if result.get("status") == "api":
        return {
            "status": "api",
            "message": "El servicio de verificación de WhatsApp no está disponible en este momento. Por favor, inténtalo más tarde."
        }
    if not result.get("existsWhatsapp"):
        raise HTTPException(
            status_code=400,
            detail="El número no tiene WhatsApp:" + request.phone_number
        )
    return {"status": "Número válido"}


def send_message(chat_id: str, message: str):
    url = f"{API_URL_BASE}/sendMessage/{API_TOKEN}"
    payload = json.dumps({
        "chatId": f"{chat_id}@c.us",
        "message": message
    })
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        response_data = response.json()
        
        # Revisar si la respuesta contiene el idMessage
        if "idMessage" in response_data:
            return {"status": "success", "data": response_data}
        else:
            return {
                "status": "error",
                "message": "La API respondió pero no indicó éxito",
                "data": response_data
            }
    except requests.exceptions.HTTPError as http_err:
        return {
            "status": "error",
            "message": f"Error de HTTP al enviar el mensaje: {http_err}"
        }
    except Exception as err:
        return {
            "status": "error",
            "message": f"No se pudo conectar a la API de envío de mensajes: {err}"
        }


@app.post("/api/send_message")
def api_send_message(request: MessageRequest):
    result = send_message(request.chat_id, request.message)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return {"status": "Mensaje enviado", "data": result.get("data")}


def generate_ticket_number():
    characters = string.ascii_letters + string.digits
    ticket_number = ''.join(random.choice(characters) for _ in range(12))
    return ticket_number


def send_qr_code(chat_id: str, qr_buf: BytesIO):
    url = f"{API_URL_BASE}/sendFileByUpload/{API_TOKEN}"
    files = {
        'file': ('qrcode.png', qr_buf, 'image/png')
    }
    payload = {
        'chatId': f'{chat_id}@c.us'
    }
    headers = {}

    try:
        response = requests.post(url, headers=headers, files=files, data=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        return {"status": "error", "message": "Error de HTTP al enviar el código QR"}
    except Exception as err:
        return {"status": "error", "message": "No se pudo conectar a la API de envío de códigos QR"}


@app.post("/api/generate_tickets")
def api_generate_tickets(request: TicketRequest, db: Session = Depends(get_db)):
    # Verificar si el número de WhatsApp es válido
    whatsapp_check = check_whatsapp(request.telefono)
    if whatsapp_check.get("existsWhatsapp") == False:
        # Procesar cuando no existe WhatsApp
        return {"status": "error", "message": "El número no tiene WhatsApp"}
    elif "existsWhatsapp" not in whatsapp_check:
        # Manejar otros errores posibles o falta de la clave "existsWhatsapp"
        return {"status": "error", "message": "No se pudo verificar el estado de WhatsApp"}

    # Verificar la cédula usando la función verificar_cedula
    try:
        elector_response = asyncio.run(verificar_cedula(CedulaRequest(numero_cedula=request.cedula), db))
        if not elector_response.get("elector"):
            return {"status": "error", "message": "La cédula no es válida"}
    except HTTPException as e:
        return {"status": "error", "message": str(e.detail)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

    # Procesar los datos del elector
    elector_data = elector_response.get("elector")
    nombre = f"{elector_data['p_nombre']} {elector_data['s_nombre']} {elector_data['p_apellido']} {elector_data['s_apellido']}"
    elector_geografico = elector_response.get("geografico")
    estado = elector_geografico['estado']
    municipio = elector_geografico['municipio']
    parroquia = elector_geografico['parroquia']

    # Verificar si ya existe un ticket con la cédula o el teléfono proporcionados
    existing_ticket = db.query(Ticket).filter(
        (Ticket.cedula == request.cedula) | (Ticket.telefono == request.telefono)
    ).first()
    if existing_ticket:
        qr_code_base64 = existing_ticket.qr_ticket
        return {
            "status": "success",
            "message": f"{existing_ticket.nombre}, hoy es tu día de suerte! Desde este momento estás participando en el Lotto Bueno y este es tu número de ticket {existing_ticket.id} ¡El número ganador!",
            "ticket_number": existing_ticket.numero_ticket,
            "qr_code": qr_code_base64
        }

    ticket_number = generate_ticket_number()

    # Determinar el id del recolector
    referido_id = request.referido_id if request.referido_id is not None else get_system_recolector_id(db)

    # Incluir datos de la persona y el número de ticket en el QR
    qr_data = {
        "ticket_number": ticket_number,
        "cedula": request.cedula,
        "nombre": nombre,
        "telefono": request.telefono,
        "estado": estado,
        "municipio": municipio,
        "parroquia": parroquia,
        "referido_id": referido_id
    }
    qr_data_json = json.dumps(qr_data)

    # Crear código QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data_json)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)

    # Guardar el ticket en la base de datos
    qr_code_base64 = base64.b64encode(buf.getvalue()).decode()
    new_ticket = TicketCreate(
        numero_ticket=ticket_number,
        qr_ticket=qr_code_base64,
        cedula=request.cedula,
        nombre=nombre,
        telefono=request.telefono,
        estado=estado,
        municipio=municipio,
        parroquia=parroquia,
        referido_id=referido_id,
        validado=True,
        ganador=False,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    try:
        db_ticket = Ticket(**new_ticket.dict())
        db.add(db_ticket)
        db.commit()
        db.refresh(db_ticket)
    except Exception as e:
        print(f"Error al guardar en la base de datos: {e}")
        return {
            "status": "error",
            "message": "Error interno del servidor no se guardo la tabla ticket"
        }

    return {
        "status": "success",
        "message": f"{db_ticket.nombre}, hoy es tu día de suerte! Desde este momento estás participando en el Lotto Bueno y este es tu número de ticket {db_ticket.id} ¡El número ganador!",
        "ticket_number": ticket_number,
        "qr_code": qr_code_base64
    }


@app.post("/api/generate_ticket")
def api_generate_ticket(request: TicketRequest, db: Session = Depends(get_db)):
    # Verificar si el número de WhatsApp es válido
    whatsapp_check = check_whatsapp(request.telefono)
    if "status" in whatsapp_check:
        return {"status": "error", "message": "El número no tiene WhatsApp"}

    # Verificar la cédula usando la función verificar_cedula
    try:
        elector_response = asyncio.run(verificar_cedula(CedulaRequest(numero_cedula=request.cedula), db))
        if not elector_response.get("elector"):
            message = "La cédula proporcionada no es válida para participar en Lotto Bueno."
            send_message(request.telefono, message)
            return {"status": "error", "message": "La cédula no es válida"}
    except HTTPException as e:
        message = "La cédula proporcionada no es válida para participar en Lotto Bueno."
        send_message(request.telefono, message)
        return {"status": "error", "message": str(e.detail)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

    # Procesar los datos del elector
    elector_data = elector_response.get("elector")
    nombre = f"{elector_data['p_nombre']} {elector_data['s_nombre']} {elector_data['p_apellido']} {elector_data['s_apellido']}"
    elector_geografico = elector_response.get("geografico")
    estado = elector_geografico['estado']
    municipio = elector_geografico['municipio']
    parroquia = elector_geografico['parroquia']

    # Verificar si ya existe un ticket con la cédula o el teléfono proporcionados
    existing_ticket = db.query(Ticket).filter((Ticket.cedula == request.cedula) | (Ticket.telefono == request.telefono)).first()
    if existing_ticket:
        # Enviar mensaje de texto por WhatsApp con el ID del ticket existente
        message = f"{existing_ticket.nombre}, hoy es tu día de suerte!\n\n" \
          f"Desde este momento estás participando en el Lotto Bueno y este es tu número de ticket {existing_ticket.id} ¡El número ganador!\n\n" \
          f"Es importante que guardes nuestro contacto, así podremos anunciarte que tú eres el afortunado ganador.\n" \
          f"No pierdas tu número de ticket y guarda nuestro contacto, ¡prepárate para celebrar!\n\n" \
          f"¡Mucha suerte!\n" \
          f"Lotto Bueno: ¡Tu mejor oportunidad de ganar!"

        send_message(request.telefono, message)
        
        # Enviar contacto de la empresa
        send_contact(request.telefono)
        
        qr_code_base64 = existing_ticket.qr_ticket
        qr_buf = BytesIO(base64.b64decode(qr_code_base64))
        send_qr_code(request.telefono, qr_buf)

        return {
            "status": "success",
            "message": message,
            "ticket_number": existing_ticket.numero_ticket,
            "qr_code": qr_code_base64
        }

    ticket_number = generate_ticket_number()
    referido_id = request.referido_id if request.referido_id is not None else get_system_recolector_id(db)

    qr_data = {
        "ticket_number": ticket_number,
        "cedula": request.cedula,
        "nombre": nombre,
        "telefono": request.telefono,
        "estado": estado,
        "municipio": municipio,
        "parroquia": parroquia,
        "referido_id": referido_id
    }
    qr_data_json = json.dumps(qr_data)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data_json)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)

    send_result = send_qr_code(request.telefono, buf)
    if send_result.get("status") == "error":
        return {"status": "error", "message": send_result["message"]}

    qr_code_base64 = base64.b64encode(buf.getvalue()).decode()
    new_ticket = TicketCreate(
        numero_ticket=ticket_number,
        qr_ticket=qr_code_base64,
        cedula=request.cedula,
        nombre=nombre,
        telefono=request.telefono,
        estado=estado,
        municipio=municipio,
        parroquia=parroquia,
        referido_id=referido_id,
        validado=False,
        ganador=False,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    try:
        db_ticket = Ticket(**new_ticket.dict())
        db.add(db_ticket)
        db.commit()
        db.refresh(db_ticket)
    except Exception as e:
        print(f"Error al guardar en la base de datos: {e}")
        return {"status": "error", "message": "Error interno del servidor no se guardo la tabla ticket"}

    # Enviar mensaje de texto por WhatsApp con el ID del nuevo ticket
    #message = f"Hola. {db_ticket.nombre} Apartir de este momento.  Estás participando en Lotto Bueno con el ID de ticket: {db_ticket.id}"
    message = f"{db_ticket.nombre}, hoy es tu día de suerte!\n\n" \
          f"Desde este momento estás participando en el Lotto Bueno y este es tu número de ticket {db_ticket.id} ¡El número ganador!\n\n" \
          f"Es importante que guardes nuestro contacto, así podremos anunciarte que tú eres el afortunado ganador.\n" \
          f"No pierdas tu número de ticket y guarda nuestro contacto, ¡prepárate para celebrar!\n\n" \
          f"¡Mucha suerte!\n" \
          f"Lotto Bueno: ¡Tu mejor oportunidad de ganar!"

    
    send_message(request.telefono, message)
    
    # Enviar contacto de la empresa
    send_contact(request.telefono)

    return {
        "status": "success",
        "message": message,
        "ticket_number": ticket_number,
        "qr_code": qr_code_base64
    }


def send_contact(chat_id: int, db: Session = Depends(get_db)):
    # Intentar obtener un número de contacto aleatorio de la tabla 'lineas_telefonicas'
    try:
        # Obtener todos los números de contacto
        phone_contacts = db.query(LineaTelefonica.numero).all()
        if phone_contacts:
            # Seleccionar un número de contacto aleatorio
            phone_contact = random.choice(phone_contacts)[0]
        else:
            # Usar la variable de ambiente si no hay números disponibles
            phone_contact = os.getenv("COMPANY_PHONE_CONTACT", "584262831867")
    except Exception as e:
        # Usar la variable de ambiente en caso de cualquier error
        phone_contact = os.getenv("COMPANY_PHONE_CONTACT", "584262831867")

    contact_request = ContactRequest(
        chat_id=chat_id,
        phone_contact=phone_contact,
        first_name="Empresa",
        last_name="Lotto Bueno",
        company="Lotto Bueno"
    )
    result = enviar_contacto(contact_request.chat_id, contact_request.phone_contact, contact_request.first_name, contact_request.last_name, contact_request.company)
    if result.get("status") == "Error":
        raise HTTPException(status_code=500, detail=result["detail"])
    
def get_system_recolector_id(db: Session) -> int:
    system_recolector = db.query(Recolector).filter(Recolector.nombre == 'system').first()
    if system_recolector is None:
        system_recolector = Recolector(nombre='system', cedula='', telefono='', es_referido=False)
        db.add(system_recolector)
        db.commit()
        db.refresh(system_recolector)
    return system_recolector.id


def obtener_numero_instancia():
    url = f"{API_URL_BASE}/getSettings/{API_TOKEN}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data["wid"]
    except requests.exceptions.HTTPError as http_err:
        return None
    except Exception as err:
        return None


def verificar_numero_whatsapp(phone_number):
    url = f"{FASTAPI_BASE_URL}/check_whatsapp"
    payload = {"phone_number": phone_number}
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        return {"status": "Error", "detail": str(http_err)}
    except Exception as err:
        return {"status": "Error", "detail": str(err)}


@app.get("/api/download/excel/electores")
async def download_excel_electores(
    codigo_estado: Optional[str] = Query(None),
    codigo_municipio: Optional[str] = Query(None),
    codigo_parroquia: Optional[str] = Query(None),
    codigo_centro_votacion: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Elector)
        nombre_estado = "todos"
        nombre_municipio = "todos"
        nombre_parroquia = "todos"
        nombre_centro = "todos"

        if codigo_estado:
            query = query.filter(Elector.codigo_estado == codigo_estado)
            estado = db.query(Geografico.estado).filter(Geografico.codigo_estado == codigo_estado).first()
            if estado:
                nombre_estado = estado[0]

        if codigo_municipio:
            query = query.filter(Elector.codigo_municipio == codigo_municipio)
            municipio = db.query(Geografico.municipio).filter(
                Geografico.codigo_estado == codigo_estado,
                Geografico.codigo_municipio == codigo_municipio
            ).first()
            if municipio:
                nombre_municipio = municipio[0]

        if codigo_parroquia:
            query = query.filter(Elector.codigo_parroquia == codigo_parroquia)
            parroquia = db.query(Geografico.parroquia).filter(
                Geografico.codigo_estado == codigo_estado,
                Geografico.codigo_municipio == codigo_municipio,
                Geografico.codigo_parroquia == codigo_parroquia
            ).first()
            if parroquia:
                nombre_parroquia = parroquia[0]

        if codigo_centro_votacion:
            query = query.filter(Elector.codigo_centro_votacion == codigo_centro_votacion)
            centro = db.query(CentroVotacion.nombre_cv).filter(
                CentroVotacion.codificacion_nueva_cv == codigo_centro_votacion
            ).first()
            if centro:
                nombre_centro = centro[0]

        # Obtener el total de registros
        total_records = query.count()
        
        # Si hay menos de 100,000 registros, procesar normalmente
        if total_records <= 100000:
            electores = query.all()
            data = [to_dict(elector) for elector in electores]
            df = pd.DataFrame(data)
            
            # Crear un único archivo Excel
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Electores', index=False)
                worksheet = writer.sheets['Electores']
                
                for idx, col in enumerate(df.columns):
                    max_length = max(df[col].astype(str).apply(len).max(), len(str(col)))
                    worksheet.set_column(idx, idx, max_length + 2)

            excel_buffer.seek(0)
            filename = f"electores_{nombre_estado}_{nombre_municipio}_{nombre_parroquia}_{nombre_centro}.xlsx"
            zip_buffer = compress_file(excel_buffer, filename)
            
            return StreamingResponse(
                zip_buffer,
                media_type='application/zip',
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}.zip"'
                }
            )
        
        # Para grandes conjuntos de datos, dividir en múltiples archivos
        batch_size = 100000
        num_batches = (total_records + batch_size - 1) // batch_size
        
        # Crear un archivo ZIP que contendrá todos los archivos Excel
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zip_file:
            for batch_num in range(num_batches):
                offset = batch_num * batch_size
                
                # Obtener el lote actual de registros
                batch_electores = query.offset(offset).limit(batch_size).all()
                data = [to_dict(elector) for elector in batch_electores]
                df = pd.DataFrame(data)
                
                # Crear archivo Excel para este lote
                batch_buffer = BytesIO()
                with pd.ExcelWriter(batch_buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='Electores', index=False)
                    worksheet = writer.sheets['Electores']
                    
                    for idx, col in enumerate(df.columns):
                        max_length = max(df[col].astype(str).apply(len).max(), len(str(col)))
                        worksheet.set_column(idx, idx, max_length + 2)
                
                batch_buffer.seek(0)
                
                # Agregar el archivo Excel al ZIP
                batch_filename = f"electores_{nombre_estado}_{nombre_municipio}_{nombre_parroquia}_{nombre_centro}_parte_{batch_num + 1}.xlsx"
                zip_file.writestr(batch_filename, batch_buffer.getvalue())
        
        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type='application/zip',
            headers={
                "Content-Disposition": f'attachment; filename="electores_{nombre_estado}_{nombre_municipio}_{nombre_parroquia}_{nombre_centro}_completo.zip"'
            }
        )

    except Exception as e:
        print(f"Error en download_excel_electores: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/excel/centros-por-estado/{codigo_estado}")
async def download_excel_centros_por_estado(
    codigo_estado: str,
    db: Session = Depends(get_db)
):
    try:
        # Obtener información del estado
        estado = db.query(Geografico.estado).filter(Geografico.codigo_estado == codigo_estado).first()
        if not estado:
            raise HTTPException(status_code=404, detail="Estado no encontrado")
        nombre_estado = estado[0]

        centros_query = (
            db.query(
                CentroVotacion.codificacion_nueva_cv,
                CentroVotacion.nombre_cv,
                CentroVotacion.direccion_cv,
                Geografico.estado,
                Geografico.municipio,
                Geografico.parroquia,
                func.count(Elector.id).label('total_electores')
            )
            .join(Geografico, 
                (CentroVotacion.codigo_estado == Geografico.codigo_estado) &
                (CentroVotacion.codigo_municipio == Geografico.codigo_municipio) &
                (CentroVotacion.codigo_parroquia == Geografico.codigo_parroquia)
            )
            .join(Elector, CentroVotacion.codificacion_nueva_cv == Elector.codigo_centro_votacion)
            .filter(CentroVotacion.codigo_estado == codigo_estado)
            .group_by(
                CentroVotacion.codificacion_nueva_cv,
                CentroVotacion.nombre_cv,
                CentroVotacion.direccion_cv,
                Geografico.estado,
                Geografico.municipio,
                Geografico.parroquia
            )
            .order_by(Geografico.municipio, Geografico.parroquia, CentroVotacion.nombre_cv)
        )

        centros = centros_query.all()
        if not centros:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron centros de votación para este estado"
            )

        data = [{
            'Código Centro': centro[0],
            'Centro de Votación': centro[1],
            'Dirección': centro[2],
            'Estado': centro[3],
            'Municipio': centro[4],
            'Parroquia': centro[5],
            'Total Electores': centro[6]
        } for centro in centros]

        df = pd.DataFrame(data)

        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Centros', index=False)
            worksheet = writer.sheets['Centros']

            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                worksheet.set_column(idx, idx, max_length + 2)

        excel_buffer.seek(0)
        filename = f"centros_electorales_{nombre_estado}.xlsx"
        zip_buffer = compress_file(excel_buffer, filename)

        return StreamingResponse(
            zip_buffer,
            media_type='application/zip',
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.zip"'
            }
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error generando Excel de centros: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generando Excel de centros: {str(e)}")


@app.get("/api/download/txt/electores")
async def download_txt_electores(
    codigo_estado: Optional[str] = Query(None),
    codigo_municipio: Optional[str] = Query(None),
    codigo_parroquia: Optional[str] = Query(None),
    codigo_centro_votacion: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Elector)
        nombre_estado = "todos"
        nombre_municipio = "todos"
        nombre_parroquia = "todos"
        nombre_centro = "todos"

        if codigo_estado:
            query = query.filter(Elector.codigo_estado == codigo_estado)
            estado = db.query(Geografico.estado).filter(Geografico.codigo_estado == codigo_estado).first()
            if estado:
                nombre_estado = estado[0]

        if codigo_municipio:
            query = query.filter(Elector.codigo_municipio == codigo_municipio)
            municipio = db.query(Geografico.municipio).filter(
                Geografico.codigo_estado == codigo_estado,
                Geografico.codigo_municipio == codigo_municipio
            ).first()
            if municipio:
                nombre_municipio = municipio[0]

        if codigo_parroquia:
            query = query.filter(Elector.codigo_parroquia == codigo_parroquia)
            parroquia = db.query(Geografico.parroquia).filter(
                Geografico.codigo_estado == codigo_estado,
                Geografico.codigo_municipio == codigo_municipio,
                Geografico.codigo_parroquia == codigo_parroquia
            ).first()
            if parroquia:
                nombre_parroquia = parroquia[0]

        if codigo_centro_votacion:
            query = query.filter(Elector.codigo_centro_votacion == codigo_centro_votacion)
            centro = db.query(CentroVotacion.nombre_cv).filter(
                CentroVotacion.codificacion_nueva_cv == codigo_centro_votacion
            ).first()
            if centro:
                nombre_centro = centro[0]

        electores = query.all()
        data = [to_dict(elector) for elector in electores]
        
        filename = f"electores_{nombre_estado}_{nombre_municipio}_{nombre_parroquia}_{nombre_centro}"
        
        # Convertir a DataFrame y luego a texto con tabulaciones
        df = pd.DataFrame(data)
        output = StringIO()
        df.to_csv(output, sep='\t', index=False, encoding='utf-8')
        output.seek(0)
        
        # Comprimir el archivo
        txt_buffer = BytesIO(output.getvalue().encode('utf-8'))
        zip_buffer = compress_file(txt_buffer, f"{filename}.txt")
        
        return StreamingResponse(
            zip_buffer,
            media_type='application/zip',
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.txt.zip"'
            }
        )
    except Exception as e:
        print(f"Error generando TXT: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generando TXT: {str(e)}")


@app.get("/api/download/excel/tickets")
async def download_excel_tickets(
    codigo_estado: Optional[str] = Query(None),
    codigo_municipio: Optional[str] = Query(None),
    codigo_parroquia: Optional[str] = Query(None),
    codigo_centro_votacion: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Ticket)
        nombre_estado = "todos"
        nombre_municipio = "todos"
        nombre_parroquia = "todos"
        nombre_centro = "todos"

        if codigo_estado:
            query = query.filter(Ticket.estado == codigo_estado)
            estado = db.query(Geografico.estado).filter(Geografico.codigo_estado == codigo_estado).first()
            if estado:
                nombre_estado = estado[0]

        if codigo_municipio:
            query = query.filter(Ticket.municipio == codigo_municipio)
            municipio = db.query(Geografico.municipio).filter(
                Geografico.codigo_estado == codigo_estado,
                Geografico.codigo_municipio == codigo_municipio
            ).first()
            if municipio:
                nombre_municipio = municipio[0]

        if codigo_parroquia:
            query = query.filter(Ticket.parroquia == codigo_parroquia)
            parroquia = db.query(Geografico.parroquia).filter(
                Geografico.codigo_estado == codigo_estado,
                Geografico.codigo_municipio == codigo_municipio,
                Geografico.codigo_parroquia == codigo_parroquia
            ).first()
            if parroquia:
                nombre_parroquia = parroquia[0]

        if codigo_centro_votacion:
            query = query.filter(Ticket.centro_votacion == codigo_centro_votacion)
            centro = db.query(CentroVotacion.nombre_cv).filter(
                CentroVotacion.codificacion_nueva_cv == codigo_centro_votacion
            ).first()
            if centro:
                nombre_centro = centro[0]

        tickets = query.all()
        data = [to_dict(ticket) for ticket in tickets]
        
        filename = f"tickets_{nombre_estado}_{nombre_municipio}_{nombre_parroquia}_{nombre_centro}.xlsx"

        excel_buffer = BytesIO()
        workbook = pd.ExcelWriter(excel_buffer, engine='xlsxwriter')
        df = pd.DataFrame(data)
        df.to_excel(workbook, sheet_name='Tickets', index=False)

        worksheet = workbook.sheets['Tickets']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(str(col))
            )
            worksheet.set_column(idx, idx, max_length + 2)

        workbook.close()
        excel_buffer.seek(0)

        zip_buffer = compress_file(excel_buffer, filename)

        return StreamingResponse(
            zip_buffer,
            media_type='application/zip',
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.zip"'
            }
        )
    except Exception as e:
        print(f"Error generando Excel: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generando Excel: {str(e)}")


@app.get("/api/download/txt/tickets")
async def download_txt_tickets(
    codigo_estado: Optional[str] = Query(None),
    codigo_municipio: Optional[str] = Query(None),
    codigo_parroquia: Optional[str] = Query(None),
    codigo_centro_votacion: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Ticket)
        nombre_estado = "todos"
        nombre_municipio = "todos"
        nombre_parroquia = "todos"
        nombre_centro = "todos"

        if codigo_estado:
            query = query.filter(Ticket.estado == codigo_estado)
            estado = db.query(Geografico.estado).filter(Geografico.codigo_estado == codigo_estado).first()
            if estado:
                nombre_estado = estado[0]

        if codigo_municipio:
            query = query.filter(Ticket.municipio == codigo_municipio)
            municipio = db.query(Geografico.municipio).filter(
                Geografico.codigo_estado == codigo_estado,
                Geografico.codigo_municipio == codigo_municipio
            ).first()
            if municipio:
                nombre_municipio = municipio[0]

        if codigo_parroquia:
            query = query.filter(Ticket.parroquia == codigo_parroquia)
            parroquia = db.query(Geografico.parroquia).filter(
                Geografico.codigo_estado == codigo_estado,
                Geografico.codigo_municipio == codigo_municipio,
                Geografico.codigo_parroquia == codigo_parroquia
            ).first()
            if parroquia:
                nombre_parroquia = parroquia[0]

        if codigo_centro_votacion:
            query = query.filter(Ticket.centro_votacion == codigo_centro_votacion)
            centro = db.query(CentroVotacion.nombre_cv).filter(
                CentroVotacion.codificacion_nueva_cv == codigo_centro_votacion
            ).first()
            if centro:
                nombre_centro = centro[0]

        tickets = query.all()
        data = [to_dict(ticket) for ticket in tickets]
        
        filename = f"tickets_{nombre_estado}_{nombre_municipio}_{nombre_parroquia}_{nombre_centro}"

        df = pd.DataFrame(data)
        output = StringIO()
        df.to_csv(output, sep='\t', index=False, encoding='utf-8')
        output.seek(0)

        txt_buffer = BytesIO(output.getvalue().encode('utf-8'))
        zip_buffer = compress_file(txt_buffer, f"{filename}.txt")

        return StreamingResponse(
            zip_buffer,
            media_type='application/zip',
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.txt.zip"'
            }
        )
    except Exception as e:
        print(f"Error generando TXT: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generando TXT: {str(e)}")


@app.post("/api/enviar_contacto")
def api_enviar_contacto(request: ContactRequest):
    result = enviar_contacto(
        request.chat_id,
        request.phone_contact,
        request.first_name,
        request.last_name,
        request.company
    )
    if result.get("status") == "Error":
        raise HTTPException(status_code=500, detail=result["detail"])
    return {"status": "Contacto enviado"}


def enviar_contacto(chat_id, phone_contact, first_name, last_name, company):
    url = f"{API_URL_BASE}/sendContact/{API_TOKEN}"
    payload = {
        "chatId": f"{chat_id}@c.us",
        "contact": {
            "phoneContact": phone_contact,
            "firstName": first_name,
            "lastName": last_name,
            "company": company
        }
    }
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        return {"status": "Error", "detail": str(http_err)}
    except Exception as err:
        return {"status": "Error", "detail": str(err)}


@app.post("/api/reboot_instance")
def api_reboot_instance():
    try:
        reboot_instance()
        return {"status": "Instancia reiniciada"}
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


def reboot_instance():
    url = f"{API_URL_BASE}/reboot/{API_TOKEN}"
    headers = {}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print("Instance rebooted successfully.")
        print(response.text.encode('utf8'))
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        raise
    except Exception as err:
        print(f"Other error occurred: {err}")
        raise


async def get_elector_from_cache(elector_id: int, db: Session):
    cache_key = f"elector:{elector_id}"
    elector = await redis.get(cache_key)
    if elector:
        return json.loads(elector)
    else:
        db_elector = db.query(Elector).filter(Elector.id == elector_id).first()
        if db_elector:
            await redis.set(
                cache_key,
                json.dumps(to_dict(db_elector), default=custom_serializer),
                ex=60 * 60
            )
        return to_dict(db_elector)


async def get_elector_by_cedula_from_cache(numero_cedula: int, db: Session):
    cache_key = f"elector:cedula:{numero_cedula}"
    elector = await redis.get(cache_key)
    if elector:
        return json.loads(elector)
    else:
        db_elector = db.query(Elector).filter(Elector.numero_cedula == numero_cedula).first()
        if db_elector:
            centro_votacion = db.query(CentroVotacion).filter(CentroVotacion.codificacion_nueva_cv == db_elector.codigo_centro_votacion).first()
            geografico = db.query(Geografico).filter(
                Geografico.codigo_estado == db_elector.codigo_estado,
                Geografico.codigo_municipio == db_elector.codigo_municipio,
                Geografico.codigo_parroquia == db_elector.codigo_parroquia
            ).first()
            result = {
                "elector": to_dict(db_elector),
                "centro_votacion": to_dict(centro_votacion),
                "geografico": to_dict(geografico)
            }
            await redis.set(cache_key, json.dumps(result, default=custom_serializer), ex=60*60)
            return result
        return None

def to_dict(obj):
    if not obj:
        return None
    return {c.key: getattr(obj, c.key) for c in obj.__table__.columns}

def custom_serializer(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f'Type {obj.__class__.__name} not serializable')


router = APIRouter()

# @bot.router.message(command="start")
# def message_handler(notification: Notification) -> None:
#     sender_data = notification.event["senderData"]
#     sender_name = sender_data["senderName"]

#     notification.answer(
#         (
#             f"👋 Hola, {sender_name}. Para validar tu registro, por favor envíame tu número de cédula."
#         )
#     )

# @bot.router.message()
# def obtener_cedula(notification: Notification) -> None:
#     sender = notification.sender
#     message_data = notification.event.get("messageData", {})
#     extended_text_message_data = message_data.get("extendedTextMessageData", {})
#     cedula = extended_text_message_data.get("textMessage") or extended_text_message_data.get("text")

#     if not cedula:
#         notification.answer("Por favor envíame un número de cédula válido.")
#         return

#     db = next(get_db())
#     elector_response = asyncio.run(verificar_cedula(CedulaRequest(numero_cedula=cedula), db))

#     if elector_response.get("elector"):
#         elector_data = elector_response.get("elector")
#         nombre_completo = f"{elector_data['p_nombre']} {elector_data['s_nombre']} {elector_data['p_apellido']} {elector_data['s_apellido']}"
#         chat_id = notification.event["senderData"]["chatId"]

#         existing_ticket = db.query(Ticket).filter((Ticket.cedula == cedula) | (Ticket.telefono == sender)).first()
#         if existing_ticket:
#             qr_code_base64 = existing_ticket.qr_ticket
#             qr_buf = BytesIO(base64.b64decode(qr_code_base64))

#             message = f"{nombre_completo}, hoy es tu día de suerte!\n\n" \
#                       f"Desde este momento estás participando en el Lotto Bueno y este es tu número de ticket {existing_ticket.id} ¡El número ganador!\n\n" \
#                       f"Es importante que guardes nuestro contacto, así podremos anunciarte que tú eres el afortunado ganador.\n" \
#                       f"No pierdas tu número de ticket y guarda nuestro contacto, ¡prepárate para celebrar!\n\n" \
#                       f"¡Mucha suerte!\n" \
#                       f"Lotto Bueno: ¡Tu mejor oportunidad de ganar!"

#             send_message(chat_id, message)
#             send_qr_code(chat_id, qr_buf)

#             # Seleccionar un número de contacto aleatorio
#             phone_contact = obtener_numero_contacto(db)

#             if phone_contact:
#                 enviar_contacto(chat_id, phone_contact.split('@')[0], "Lotto", "Bueno", "Lotto Bueno Inc")
#             notification.answer("Gracias por registrarte. ¡Hasta pronto!")
#             notification.state_manager.delete_state(sender)
#         else:
#             notification.answer("No se encontró un ticket asociado a la cédula proporcionada.")
#     else:
#         notification.answer("El número de cédula proporcionado no está registrado. Por favor intenta nuevamente.")

def obtener_numero_contacto(db: Session) -> str:
     try:
         phone_contacts = db.query(LineaTelefonica.numero).all()
         if phone_contacts:
             phone_contact = random.choice(phone_contacts)[0]
         else:
             phone_contact = obtener_numero_instancia()
         return phone_contact
     except Exception as e:
         return obtener_numero_instancia()




@router.post("/verificar_cedula")
async def verificar_cedula(request: CedulaRequest, db: Session = Depends(get_db)):
    numero_cedula = request.numero_cedula
    response = await read_elector_by_cedula_no_cache(numero_cedula, db)
    return response


@router.get("/total/api/electores", response_model=int)
def get_total_electores(
    codigo_estado: Optional[int] = None,
    codigo_municipio: Optional[int] = None,
    codigo_parroquia: Optional[int] = None,
    codigo_centro_votacion: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Elector)
    if codigo_estado is not None:
        query = query.filter(Elector.codigo_estado == codigo_estado)
    if codigo_municipio is not None:
        query = query.filter(Elector.codigo_municipio == codigo_municipio)
    if codigo_parroquia is not None:
        query = query.filter(Elector.codigo_parroquia == codigo_parroquia)
    if codigo_centro_votacion is not None:
        query = query.filter(Elector.codigo_centro_votacion == codigo_centro_votacion)
    
    total = query.count()
    return total


@app.get("/api/electores/", response_model=List[ElectorList])
async def read_electores(
    skip: int = 0,
    limit: int = 100,
    codigo_estado: int = Query(None),
    codigo_municipio: int = Query(None),
    codigo_parroquia: int = Query(None),
    codigo_centro_votacion: int = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Elector)
    if codigo_estado:
        query = query.filter(Elector.codigo_estado == codigo_estado)
    if codigo_municipio:
        query = query.filter(Elector.codigo_municipio == codigo_municipio)
    if codigo_parroquia:
        query = query.filter(Elector.codigo_parroquia == codigo_parroquia)
    if codigo_centro_votacion:
        query = query.filter(Elector.codigo_centro_votacion == codigo_centro_votacion)

    electores = query.offset(skip).limit(limit).all()
    return [elector for elector in electores]


@app.get("/api/electores/{elector_id}", response_model=ElectorList)
async def read_elector(elector_id: int, db: Session = Depends(get_db)):
    elector = db.query(Elector).filter(Elector.id == elector_id).first()
    if not elector:
        raise HTTPException(status_code=404, detail="Esta cedula no esta Autorizada para el registro en Lotto Bueno")
    return elector


@app.get("/api/electores/cedula/{numero_cedula}", response_model=ElectorDetail)
async def read_elector_by_cedula(numero_cedula: int, db: Session = Depends(get_db)):
    result = await get_elector_by_cedula_from_cache(numero_cedula, db)
    if not result:
        raise HTTPException(status_code=404, detail="Esta cedula no esta Autorizada para el registro en Lotto Bueno")
    return result

def to_dict(obj):
    if not obj:
        return None
    return {c.key: getattr(obj, c.key) for c in obj.__table__.columns}

@router.get("/electores/cedula_no_cache/{numero_cedula}", response_model=ElectorDetail)
async def read_elector_by_cedula_no_cache(numero_cedula: int, db: Session = Depends(get_db)):
    db_elector = db.query(Elector).filter(Elector.numero_cedula == numero_cedula).first()
    if db_elector:
        centro_votacion = db.query(CentroVotacion).filter(CentroVotacion.codificacion_nueva_cv == db_elector.codigo_centro_votacion).first()
        geografico = db.query(Geografico).filter(
            Geografico.codigo_estado == db_elector.codigo_estado,
            Geografico.codigo_municipio == db_elector.codigo_municipio,
            Geografico.codigo_parroquia == db_elector.codigo_parroquia
        ).first()
        result = {
            "elector": to_dict(db_elector),
            "centro_votacion": to_dict(centro_votacion),
            "geografico": to_dict(geografico)
        }
        return result
    else:
        raise HTTPException(
            status_code=404,
            detail="Esta cedula no esta Autorizada para el registro en Lotto Bueno"
        )


@app.get("/api/geograficos/", response_model=list[GeograficoList])
async def read_geograficos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    geograficos = db.query(Geografico).offset(skip).limit(limit).all()
    return [to_dict(geografico) for geografico in geograficos]


@app.post("/api/geograficos/", response_model=GeograficoList)
async def create_geografico(geografico: GeograficoCreate, db: Session = Depends(get_db)):
    db_geografico = Geografico(**geografico.model_dump())
    db.add(db_geografico)
    db.commit()
    db.refresh(db_geografico)
    return to_dict(db_geografico)


@app.get("/api/centros_votacion/", response_model=list[CentroVotacionList])
async def read_centros_votacion(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    centros = db.query(CentroVotacion).offset(skip).limit(limit).all()
    return [to_dict(centro) for centro in centros]


@app.post("/api/centros_votacion/", response_model=CentroVotacionList)
async def create_centro_votacion(centro: CentroVotacionCreate, db: Session = Depends(get_db)):
    db_centro = CentroVotacion(**centro.model_dump())
    db.add(db_centro)
    db.commit()
    db.refresh(db_centro)
    return to_dict(db_centro)


@app.get("/api/stats/{stat_type}")
async def get_statistics(stat_type: str, db: Session = Depends(get_db)):
    valid_stats = ["estado", "municipio", "parroquia", "centro_votacion"]
    if stat_type not in valid_stats:
        raise HTTPException(status_code=400, detail="Invalid statistics type")
    stats = await get_statistics_from_cache(stat_type, db)
    return stats


async def get_statistics_from_cache(stat_type: str, db: Session):
    cache_key = f"stats:{stat_type}"
    stats = await redis.get(cache_key)
    if stats:
        return json.loads(stats)
    else:
        if stat_type == "estado":
            stats = db.query(Elector.codigo_estado, func.count(Elector.id)).group_by(Elector.codigo_estado).all()
        elif stat_type == "municipio":
            stats = db.query(Elector.codigo_municipio, func.count(Elector.id)).group_by(Elector.codigo_municipio).all()
        elif stat_type == "parroquia":
            stats = db.query(Elector.codigo_parroquia, func.count(Elector.id)).group_by(Elector.codigo_parroquia).all()
        elif stat_type == "centro_votacion":
            stats = db.query(Elector.codigo_centro_votacion, func.count(Elector.id)).group_by(Elector.codigo_centro_votacion).all()
        
        stats_dict = [{"key": key, "count": count} for key, count in stats]
        await redis.set(cache_key, json.dumps(stats_dict), ex=60*60)
        return stats_dict


class TicketResponse(BaseModel):
    total: int
    items: List[TicketList]


@app.get("/api/tickets/", response_model=TicketResponse)
async def read_tickets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    total = db.query(Ticket).count()
    tickets = db.query(Ticket).offset(skip).limit(limit).all()
    return {"total": total, "items": [to_dict(ticket) for ticket in tickets]}


@app.get("/api/tickets/cedula/{cedula}", response_model=TicketList)
async def read_ticket_by_cedula(cedula: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.cedula == cedula).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.get("/api/tickets/{ticket_id}", response_model=TicketList)
async def read_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return to_dict(ticket)


@app.post("/api/tickets/", response_model=TicketList)
async def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db)):
    db_ticket = Ticket(**ticket.model_dump())
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return to_dict(db_ticket)


@app.patch("/api/tickets/{ticket_id}", response_model=TicketList)
async def update_ticket(ticket_id: int, ticket: TicketUpdate, db: Session = Depends(get_db)):
    db_ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if "validado" in ticket.dict(exclude_unset=True):
        db_ticket.validado = ticket.validado
    if "ganador" in ticket.dict(exclude_unset=True):
        db_ticket.ganador = ticket.ganador
    db.commit()
    db.refresh(db_ticket)
    return to_dict(db_ticket)


@app.get("/api/tickets/estados", response_model=List[str])
async def get_estados(db: Session = Depends(get_db)):
    estados = db.query(distinct(Ticket.estado)).all()
    return [estado[0] for estado in estados]


@app.get("/api/tickets/municipios", response_model=List[str])
async def get_municipios(estado: str, db: Session = Depends(get_db)):
    municipios = db.query(distinct(Ticket.municipio)).filter(Ticket.estado == estado).all()
    return [municipio[0] for municipio in municipios]


class RecolectorResponse(BaseModel):
    total: int
    items: List[RecolectorList]


@app.get("/api/recolectores/", response_model=RecolectorResponse)
async def read_recolectores(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    total = db.query(Recolector).count()
    recolectores = db.query(Recolector).offset(skip).limit(limit).all()
    return {"total": total, "items": [to_dict(recolector) for recolector in recolectores]}


@app.get("/api/recolectores/{recolector_id}", response_model=RecolectorList)
async def read_recolector(recolector_id: int, db: Session = Depends(get_db)):
    recolector = db.query(Recolector).filter(Recolector.id == recolector_id).first()
    if not recolector:
        raise HTTPException(status_code=404, detail="Recolector not found")
    return to_dict(recolector)


@app.post("/api/recolectores/", response_model=RecolectorList)
async def create_recolector(recolector: RecolectorCreate, db: Session = Depends(get_db)):
    db_recolector = Recolector(**recolector.model_dump())
    db.add(db_recolector)
    db.commit()
    db.refresh(db_recolector)
    return to_dict(db_recolector)


@app.delete("/api/recolectores/{recolector_id}", response_model=dict)
async def delete_recolector(recolector_id: int, db: Session = Depends(get_db)):
    recolector = db.query(Recolector).filter(Recolector.id == recolector_id).first()
    if not recolector:
        raise HTTPException(status_code=404, detail="Recolector not found")
    db.delete(recolector)
    db.commit()
    return {"message": "Recolector deleted successfully"}


@app.patch("/api/recolectores/{recolector_id}", response_model=RecolectorList)
async def update_recolector(recolector_id: int, recolector: RecolectorUpdate, db: Session = Depends(get_db)):
    db_recolector = db.query(Recolector).filter(Recolector.id == recolector_id).first()
    if not db_recolector:
        raise HTTPException(status_code=404, detail="Recolector not found")
    for key, value in recolector.dict(exclude_unset=True).items():
        setattr(db_recolector, key, value)
    db.commit()
    db.refresh(db_recolector)
    return to_dict(db_recolector)


@app.get("/api/recolectores/estadisticas/", response_model=List[RecolectorEstadisticas])
async def get_recolector_estadisticas(
    recolector_id: Optional[int] = None,
    codigo_estado: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = (
        db.query(
            Recolector.id,
            Recolector.nombre,
            func.count(Ticket.id).label("tickets_count")
        )
        .join(Ticket, Ticket.referido_id == Recolector.id, isouter=True)
    )

    if recolector_id:
        query = query.filter(Recolector.id == recolector_id)
    if codigo_estado:
        query = query.filter(Ticket.estado == codigo_estado)

    query = query.group_by(Recolector.id, Recolector.nombre)

    estadisticas = query.all()
    return [
        {"recolector_id": est.id, "nombre": est.nombre, "tickets_count": est.tickets_count}
        for est in estadisticas
    ]


@app.get("/api/recolectores/{recolector_id}/referidos")
async def get_recolector_referidos(
    recolector_id: int,
    codigo_estado: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        recolector = db.query(Recolector).filter(Recolector.id == recolector_id).first()
        if not recolector:
            raise HTTPException(status_code=404, detail="Recolector no encontrado")

        query = (
            db.query(
                Ticket.id,
                Ticket.cedula,
                Ticket.nombre,
                Ticket.telefono,
                Ticket.estado,
                Ticket.municipio,
                Ticket.parroquia,
                Ticket.created_at
            )
            .filter(Ticket.referido_id == recolector_id)
            .order_by(
                # Ordenar primero por letra de cédula (V antes que E)
                case(
                    (func.substr(Ticket.cedula, 1, 1) == 'V', 0),
                    (func.substr(Ticket.cedula, 1, 1) == 'E', 1),
                    else_=2
                ),
                # Luego ordenar por número de cédula (convertido a entero)
                func.cast(func.substr(Ticket.cedula, 2), Integer).asc()
            )
        )

        if codigo_estado:
            query = query.filter(Ticket.estado == codigo_estado)

        referidos = query.all()

        return {
            "recolector": {
                "id": recolector.id,
                "nombre": recolector.nombre,
                "total_referidos": len(referidos)
            },
            "referidos": [
                {
                    "id": ref.id,
                    "cedula": ref.cedula,
                    "nombre": ref.nombre,
                    "telefono": ref.telefono,
                    "estado": ref.estado,
                    "municipio": ref.municipio,
                    "parroquia": ref.parroquia,
                    "fecha_registro": ref.created_at.isoformat()
                }
                for ref in referidos
            ]
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/excel/recolector-referidos/{recolector_id}")
async def download_excel_recolector_referidos(
    recolector_id: int,
    codigo_estado: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        # Obtener el recolector
        recolector = db.query(Recolector).filter(Recolector.id == recolector_id).first()
        if not recolector:
            raise HTTPException(status_code=404, detail="Recolector no encontrado")

        # Consulta ordenada de referidos
        query = (
            db.query(Ticket)
            .filter(Ticket.referido_id == recolector_id)
            .order_by(
                # Ordenar primero por letra de cédula (V antes que E)
                case(
                    (func.substr(Ticket.cedula, 1, 1) == 'V', 0),
                    (func.substr(Ticket.cedula, 1, 1) == 'E', 1),
                    else_=2
                ),
                # Luego ordenar por número de cédula (convertido a entero)
                func.cast(func.substr(Ticket.cedula, 2), Integer).asc()
            )
        )

        if codigo_estado:
            query = query.filter(Ticket.estado == codigo_estado)

        referidos = query.all()

        # Crear DataFrame con los datos ordenados
        df = pd.DataFrame([{
            'Cédula': ref.cedula,
            'Nombre': ref.nombre,
            'Teléfono': ref.telefono,
            'Estado': ref.estado,
            'Municipio': ref.municipio,
            'Parroquia': ref.parroquia,
            'Fecha de Registro': ref.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for ref in referidos])

        # Crear el archivo Excel
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            workbook = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1
            })

            # Escribir la información del recolector y estadísticas
            worksheet = workbook.add_worksheet('Referidos')
            worksheet.write(0, 0, f"Recolector: {recolector.nombre}", header_format)
            worksheet.write(1, 0, f"Cédula del Recolector: {recolector.cedula}", header_format)
            worksheet.write(2, 0, f"Total de Referidos: {len(referidos)}", header_format)
            if codigo_estado:
                estado_nombre = db.query(Geografico.estado).filter(
                    Geografico.codigo_estado == codigo_estado
                ).first()
                if estado_nombre:
                    worksheet.write(3, 0, f"Estado: {estado_nombre[0]}", header_format)

            # Escribir los datos de referidos
            df.to_excel(writer, sheet_name='Referidos', startrow=5, index=False)

            # Ajustar el ancho de las columnas
            for idx, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).apply(len).max(), len(str(col)))
                worksheet.set_column(idx, idx, max_length + 2)

        excel_buffer.seek(0)
        recolector_nombre = recolector.nombre.replace(" ", "_")
        estado_filtro = f"_{codigo_estado}" if codigo_estado else ""
        filename = f"referidos_{recolector_nombre}{estado_filtro}.xlsx"

        # Comprimir el archivo Excel
        zip_buffer = compress_file(excel_buffer, filename)

        return StreamingResponse(
            zip_buffer,
            media_type='application/zip',
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.zip"'
            }
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def read_settings():
    try:
        with open("app/settings.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Settings file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error decoding JSON from settings file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def write_settings(settings: dict):
    try:
        with open("app/settings.json", "w") as file:
            json.dump(settings, file, indent=4)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings")
async def get_settings():
    settings = read_settings()
    return JSONResponse(status_code=200, content=settings)


@app.post("/api/settings")
async def update_settings(payload: dict):
    try:
        settings = read_settings()

        if "currentTemplate" in payload:
            settings["currentTemplate"] = payload["currentTemplate"]

        current_template = settings.get("currentTemplate")
        if not current_template:
            raise HTTPException(status_code=400, detail="currentTemplate not set in settings")
        if current_template not in settings:
            raise HTTPException(
                status_code=400,
                detail=f"Template {current_template} not found in settings"
            )

        template_settings = settings[current_template]
        for section_key, section_value in payload.get(current_template, {}).items():
            if section_key in template_settings:
                if isinstance(template_settings[section_key], dict) and isinstance(section_value, dict):
                    template_settings[section_key].update(section_value)
                else:
                    template_settings[section_key] = section_value
            else:
                template_settings[section_key] = section_value

        write_settings(settings)
        return JSONResponse(status_code=200, content={"message": "Settings saved"})
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


class UpdateHTMLSettings(BaseModel):
    title: str
    description: str
    faviconUrl: str
    

BASE_DIR = Path(__file__).resolve().parent

@app.post("/api/update-html")
async def update_html(settings: UpdateHTMLSettings):
    try:
        html_path = BASE_DIR / "frontend/out/index.html"
        with open(html_path, 'r', encoding='utf-8') as file:
            html_content = file.read()

        html_content = re.sub(r'<title>.*?</title>', f'<title>{settings.title}</title>', html_content)
        html_content = re.sub(
            r'<meta name="description" content=".*?"/>',
            f'<meta name="description" content="{settings.description}"/>',
            html_content
        )
        html_content = re.sub(
            r'<link rel="icon" href=".*?" type="image/x-icon"/>',
            f'<link rel="icon" href="{settings.faviconUrl}" type="image/x-icon"/>',
            html_content
        )
        
        with open(html_path, 'w', encoding='utf-8') as file:
            file.write(html_content)
        
        _next_dir = BASE_DIR / "frontend/out/_next/static/chunks/app"
        for root, _, files in os.walk(_next_dir):
            for name in files:
                if name.endswith(".js"):
                    file_path = os.path.join(root, name)
                    with open(file_path, 'r', encoding='utf-8') as file:
                        file_content = file.read()
                    
                    file_content = re.sub(
                        r'title:t.title\|\|"[^"]+"',
                        f'title:t.title||"{settings.title}"',
                        file_content
                    )
                    file_content = re.sub(
                        r'description:t.description\|\|"[^"]+"',
                        f'description:t.description||"{settings.description}"',
                        file_content
                    )
                    file_content = re.sub(
                        r'faviconUrl:t.faviconUrl\|\|"[^"]+"',
                        f'faviconUrl:t.faviconUrl||"{settings.faviconUrl}"',
                        file_content
                    )
                    
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write(file_content)

        return {"message": "HTML and chunks updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UserCreate(BaseModel):
    username: str
    email: str
    isAdmin: bool
    password: str


@app.post("/api/users", response_model=UserList)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    hashed_password = generate_password_hash(user.password)
    new_user = Users(
        username=user.username,
        email=user.email,
        isAdmin=user.isAdmin,
        hashed_password=hashed_password,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.get("/api/users/{user_id}", response_model=UserList)
async def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/api/users", response_model=list[UserList])
async def get_users(db: Session = Depends(get_db)):
    users = db.query(Users).all()
    return users


@app.put("/api/users/{user_id}", response_model=UserList)
async def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(Users).filter(Users.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    hashed_password = generate_password_hash(user.password)
    db_user.username = user.username
    db_user.email = user.email
    db_user.hashed_password = hashed_password
    db_user.isAdmin = user.isAdmin
    db_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    return db_user


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(Users).filter(Users.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}


@app.post("/api/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(Users).filter(Users.username == form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    if not check_password_hash(user.hashed_password, form_data.password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer", "isAdmin": user.isAdmin}


@app.post("/api/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    return {"message": "User logged out successfully"}


@app.get("/api/estados/", response_model=list[GeograficoList])
async def read_estados(db: Session = Depends(get_db)):
    estados = db.query(Geografico.codigo_estado, Geografico.estado).distinct().order_by(Geografico.estado.asc()).all()
    return [{"codigo_estado": estado[0], "estado": estado[1], "codigo_municipio": None, "codigo_parroquia": None, "municipio": None, "parroquia": None, "id": i} for i, estado in enumerate(estados)]


@app.get("/api/municipios/{codigo_estado}", response_model=list[GeograficoList])
async def read_municipios(codigo_estado: int, db: Session = Depends(get_db)):
    municipios = db.query(Geografico.codigo_municipio, Geografico.municipio).filter(
        Geografico.codigo_estado == codigo_estado
    ).distinct().order_by(Geografico.municipio.asc()).all()
    return [{"codigo_municipio": municipio[0], "municipio": municipio[1], "codigo_estado": codigo_estado, "codigo_parroquia": None, "estado": None, "parroquia": None, "id": i} for i, municipio in enumerate(municipios)]


@app.get("/api/parroquias/{codigo_estado}/{codigo_municipio}", response_model=list[GeograficoList])
async def read_parroquias(codigo_estado: int, codigo_municipio: int, db: Session = Depends(get_db)):
    parroquias = db.query(Geografico.codigo_parroquia, Geografico.parroquia).filter(
        Geografico.codigo_estado == codigo_estado,
        Geografico.codigo_municipio == codigo_municipio
    ).distinct().order_by(Geografico.parroquia.asc()).all()
    return [{"codigo_parroquia": parroquia[0], "parroquia": parroquia[1], "codigo_estado": codigo_estado, "codigo_municipio": codigo_municipio, "estado": None, "municipio": None, "id": i} for i, parroquia in enumerate(parroquias)]


@app.get("/api/centros_votacion/{codigo_estado}/{codigo_municipio}/{codigo_parroquia}", response_model=List[CentroVotacionList])
async def read_centros_votacion_by_ubicacion(codigo_estado: int, codigo_municipio: int, codigo_parroquia: int, db: Session = Depends(get_db)):
    centros = db.query(CentroVotacion).filter(
        CentroVotacion.codigo_estado == codigo_estado,
        CentroVotacion.codigo_municipio == codigo_municipio,
        CentroVotacion.codigo_parroquia == codigo_parroquia
    ).distinct(
        CentroVotacion.codificacion_nueva_cv
    ).order_by(
        CentroVotacion.codificacion_nueva_cv,
        CentroVotacion.nombre_cv
    ).all()
    
    return [
        CentroVotacionList(
            id=centro.id,
            codificacion_vieja_cv=str(centro.codificacion_vieja_cv),
            codificacion_nueva_cv=str(centro.codificacion_nueva_cv),
            condicion=str(centro.condicion),
            codigo_estado=centro.codigo_estado,
            codigo_municipio=centro.codigo_municipio,
            codigo_parroquia=centro.codigo_parroquia,
            nombre_cv=centro.nombre_cv,
            direccion_cv=centro.direccion_cv
        )
        for centro in centros
    ]



class LineaTelefonicaResponse(BaseModel):
    total: int
    items: List[LineaTelefonicaList]


@app.get("/api/lineas_telefonicas/", response_model=LineaTelefonicaResponse)
async def read_lineas_telefonicas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    total = db.query(LineaTelefonica).count()
    lineas_telefonicas = db.query(LineaTelefonica).offset(skip).limit(limit).all()
    return {"total": total, "items": lineas_telefonicas}


@app.get("/api/lineas_telefonicas/{linea_telefonica_id}", response_model=LineaTelefonicaList)
async def read_linea_telefonica(linea_telefonica_id: int, db: Session = Depends(get_db)):
    linea_telefonica = db.query(LineaTelefonica).filter(LineaTelefonica.id == linea_telefonica_id).first()
    if not linea_telefonica:
        raise HTTPException(status_code=404, detail="LineaTelefonica not found")
    return linea_telefonica


@app.post("/api/lineas_telefonicas/", response_model=LineaTelefonicaList)
async def create_linea_telefonica(linea_telefonica: LineaTelefonicaCreate, db: Session = Depends(get_db)):
    db_linea_telefonica = LineaTelefonica(**linea_telefonica.dict())
    db.add(db_linea_telefonica)
    db.commit()
    db.refresh(db_linea_telefonica)
    return db_linea_telefonica


@app.patch("/api/lineas_telefonicas/{linea_telefonica_id}", response_model=LineaTelefonicaList)
async def update_linea_telefonica(linea_telefonica_id: int, linea_telefonica: LineaTelefonicaUpdate, db: Session = Depends(get_db)):
    db_linea_telefonica = db.query(LineaTelefonica).filter(LineaTelefonica.id == linea_telefonica_id).first()
    if not db_linea_telefonica:
        raise HTTPException(status_code=404, detail="LineaTelefonica not found")
    db_linea_telefonica.numero = linea_telefonica.numero
    db_linea_telefonica.operador = linea_telefonica.operador
    db.commit()
    db.refresh(db_linea_telefonica)
    return db_linea_telefonica


@app.delete("/api/lineas_telefonicas/{linea_telefonica_id}", response_model=LineaTelefonicaList)
async def delete_linea_telefonica(linea_telefonica_id: int, db: Session = Depends(get_db)):
    db_linea_telefonica = db.query(LineaTelefonica).filter(LineaTelefonica.id == linea_telefonica_id).first()
    if not db_linea_telefonica:
        raise HTTPException(status_code=404, detail="LineaTelefonica not found")
    db.delete(db_linea_telefonica)
    db.commit()
    return db_linea_telefonica


class SorteoRequest(BaseModel):
    cantidad_ganadores: int
    estado: Optional[str]
    municipio: Optional[str]


@app.post("/api/sorteo/ganadores", response_model=List[TicketList])
async def sorteo_ganadores(request: SorteoRequest, db: Session = Depends(get_db)):
    query = db.query(Ticket).filter(Ticket.validado == True, Ticket.ganador == False)
    
    if request.estado:
        query = query.filter(Ticket.estado == request.estado)
    
    if request.municipio:
        query = query.filter(Ticket.municipio == request.municipio)
    
    tickets_validos = query.all()
    if len(tickets_validos) < request.cantidad_ganadores:
        return JSONResponse(
            status_code=400,
            content={"message": "No hay suficientes tickets válidos para seleccionar la cantidad de ganadores solicitada"}
        )

    ganadores = random.sample(tickets_validos, request.cantidad_ganadores)
    for ganador in ganadores:
        ganador.ganador = True
        db.commit()
        db.refresh(ganador)
    
    return ganadores


@app.post("/api/sorteo/quitar_ganadores")
async def quitar_ganadores(db: Session = Depends(get_db)):
    tickets_ganadores = db.query(Ticket).filter(Ticket.ganador == True).all()
    for ticket in tickets_ganadores:
        ticket.ganador = False
        db.commit()
        db.refresh(ticket)
    return {"message": "Marca de ganadores eliminada de todos los tickets"}


app.include_router(router)


@app.get("/api/download/excel/electores/info")
async def get_electores_download_info(
    codigo_estado: Optional[str] = Query(None),
    codigo_municipio: Optional[str] = Query(None),
    codigo_parroquia: Optional[str] = Query(None),
    codigo_centro_votacion: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Elector)
        if codigo_estado:
            query = query.filter(Elector.codigo_estado == codigo_estado)
        if codigo_municipio:
            query = query.filter(Elector.codigo_municipio == codigo_municipio)
        if codigo_parroquia:
            query = query.filter(Elector.codigo_parroquia == codigo_parroquia)
        if codigo_centro_votacion:
            query = query.filter(Elector.codigo_centro_votacion == codigo_centro_votacion)

        total_records = query.count()
        batch_size = 100000
        num_batches = (total_records + batch_size - 1) // batch_size

        return JSONResponse({
            "total_records": total_records,
            "num_batches": num_batches,
            "batch_size": batch_size
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/excel/electores/batch/{batch_number}")
async def download_excel_electores_batch(
    batch_number: int,
    codigo_estado: Optional[str] = Query(None),
    codigo_municipio: Optional[str] = Query(None),
    codigo_parroquia: Optional[str] = Query(None),
    codigo_centro_votacion: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Elector)
        nombre_estado = "todos"
        nombre_municipio = "todos"
        nombre_parroquia = "todos"
        nombre_centro = "todos"

        if codigo_estado:
            query = query.filter(Elector.codigo_estado == codigo_estado)
            estado = db.query(Geografico.estado).filter(
                Geografico.codigo_estado == codigo_estado
            ).first()
            if estado:
                nombre_estado = estado[0]

        if codigo_municipio:
            query = query.filter(Elector.codigo_municipio == codigo_municipio)
            municipio = db.query(Geografico.municipio).filter(
                Geografico.codigo_estado == codigo_estado,
                Geografico.codigo_municipio == codigo_municipio
            ).first()
            if municipio:
                nombre_municipio = municipio[0]

        if codigo_parroquia:
            query = query.filter(Elector.codigo_parroquia == codigo_parroquia)
            parroquia = db.query(Geografico.parroquia).filter(
                Geografico.codigo_estado == codigo_estado,
                Geografico.codigo_municipio == codigo_municipio,
                Geografico.codigo_parroquia == codigo_parroquia
            ).first()
            if parroquia:
                nombre_parroquia = parroquia[0]

        if codigo_centro_votacion:
            query = query.filter(Elector.codigo_centro_votacion == codigo_centro_votacion)
            centro = db.query(CentroVotacion.nombre_cv).filter(
                CentroVotacion.codificacion_nueva_cv == codigo_centro_votacion
            ).first()
            if centro:
                nombre_centro = centro[0]

        batch_size = 100000
        offset = (batch_number - 1) * batch_size

        batch_electores = query.offset(offset).limit(batch_size).all()
        if not batch_electores:
            raise HTTPException(status_code=404, detail="No hay más registros")

        data = [to_dict(elector) for elector in batch_electores]
        df = pd.DataFrame(data)

        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Electores', index=False)
            worksheet = writer.sheets['Electores']

            for idx, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).apply(len).max(), len(str(col)))
                worksheet.set_column(idx, idx, max_length + 2)

        excel_buffer.seek(0)

        filename = (
            f"electores_{nombre_estado}_{nombre_municipio}_{nombre_parroquia}_{nombre_centro}_parte_{batch_number}.xlsx"
        )
        zip_buffer = compress_file(excel_buffer, filename)

        return StreamingResponse(
            zip_buffer,
            media_type='application/zip',
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.zip"'
            }
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error generando Excel batch {batch_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generando Excel batch {batch_number}: {str(e)}")


@app.get("/api/download/excel/electores/progress")
async def get_download_progress(request: Request):
    async def event_generator():
        try:
            progress_key = request.headers.get("X-Progress-Key", "default")
            progress = 0
            while progress < 100:
                progress = await redis.get(f"download_progress:{progress_key}") or 0
                if isinstance(progress, str):
                    progress = float(progress)

                yield {
                    "event": "progress",
                    "data": json.dumps({"progress": progress})
                }
                await asyncio.sleep(1)
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }

    return EventSourceResponse(event_generator())


@app.get("/api/download/excel/electores-por-centros/{codigo_estado}")
async def download_excel_electores_por_centros(
    codigo_estado: str,
    download_id: str,
    db: Session = Depends(get_db)
):
    try:
        download_info_str = await redis.get(f"download:electores_centros:{download_id}")
        if not download_info_str:
            raise HTTPException(status_code=404, detail="Información de descarga no encontrada")

        download_info = json.loads(download_info_str)
        estado = db.query(Geografico.estado).filter(
            Geografico.codigo_estado == codigo_estado
        ).first()
        if not estado:
            raise HTTPException(status_code=404, detail="Estado no encontrado")
        nombre_estado = estado[0]

        centros = (
            db.query(CentroVotacion)
            .filter(CentroVotacion.codigo_estado == codigo_estado)
            .all()
        )
        if not centros:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron centros de votación para este estado"
            )

        # Se asumiría que hay alguna variable batch_size previamente establecida
        # (No está en el contexto completo, se podría setear en 100,000 si se desea)
        batch_size = 100000
        total_centros = len(centros)
        num_batches = (total_centros + batch_size - 1) // batch_size

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zip_file:
            for batch_num in range(num_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, total_centros)
                centros_batch = centros[start_idx:end_idx]

                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    workbook = writer.book
                    header_format = workbook.add_format({
                        'bold': True,
                        'bg_color': '#D3D3D3',
                        'border': 1
                    })

                    for centro in centros_batch:
                        electores = (
                            db.query(Elector)
                            .filter(
                                Elector.codigo_estado == codigo_estado,
                                Elector.codigo_centro_votacion == centro.codificacion_nueva_cv
                            )
                            .all()
                        )
                        if electores:
                            data = [{
                                'Cédula': f"{elector.letra_cedula}-{elector.numero_cedula}",
                                'Primer Nombre': elector.p_nombre,
                                'Segundo Nombre': elector.s_nombre,
                                'Primer Apellido': elector.p_apellido,
                                'Segundo Apellido': elector.s_apellido,
                                'Fecha Nacimiento': elector.fecha_nacimiento,
                                'Sexo': elector.sexo
                            } for elector in electores]

                            df = pd.DataFrame(data)
                            sheet_name = f"Centro_{centro.codificacion_nueva_cv}"[:31]
                            df.to_excel(writer, sheet_name=sheet_name, startrow=4, index=False)
                            worksheet = writer.sheets[sheet_name]

                            worksheet.write(0, 0, f"Centro de Votación: {centro.nombre_cv}", header_format)
                            worksheet.write(1, 0, f"Dirección: {centro.direccion_cv}", header_format)
                            worksheet.write(2, 0, f"Código: {centro.codificacion_nueva_cv}", header_format)

                            for idx, col in enumerate(df.columns):
                                max_length = max(df[col].astype(str).apply(len).max(), len(str(col)))
                                worksheet.set_column(idx, idx, max_length + 2)

                excel_buffer.seek(0)
                batch_filename = f"electores_por_centros_{nombre_estado}_parte_{batch_num + 1}.xlsx"
                zip_file.writestr(batch_filename, excel_buffer.getvalue())

        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type='application/zip',
            headers={
                "Content-Disposition": f'attachment; filename="electores_por_centros_{nombre_estado}_completo.zip"'
            }
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error generando Excel de electores por centros: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generando Excel de electores por centros: {str(e)}"
        )


@app.get("/api/download/excel/electores-por-centros/info/{codigo_estado}")
async def get_electores_por_centros_info(
    codigo_estado: str,
    db: Session = Depends(get_db)
):
    try:
        # Primero verificamos que el estado exista
        estado = db.query(Geografico.estado).filter(
            Geografico.codigo_estado == int(codigo_estado)
        ).first()

        if not estado:
            return {
                "centros": [],
                "total_centros": 0,
                "total_electores": 0
            }

        # Consulta para obtener los centros y su conteo de electores
        centros = db.query(
            CentroVotacion.codificacion_nueva_cv.label('codigo'),
            CentroVotacion.nombre_cv.label('nombre'),
            func.count(distinct(Elector.id)).label('total_electores')
        ).outerjoin(
            Elector,
            CentroVotacion.codificacion_nueva_cv == Elector.codigo_centro_votacion
        ).filter(
            CentroVotacion.codigo_estado == int(codigo_estado)
        ).group_by(
            CentroVotacion.codificacion_nueva_cv,
            CentroVotacion.nombre_cv
        ).all()

        if not centros:
            return {
                "centros": [],
                "total_centros": 0,
                "total_electores": 0
            }

        centros_info = []
        total_electores = 0

        for centro in centros:
            num_electores = centro.total_electores or 0
            num_particiones = max(1, math.ceil(num_electores / 100000))
            centros_info.append({
                "codigo": str(centro.codigo),
                "nombre": centro.nombre,
                "total_electores": num_electores,
                "num_particiones": num_particiones
            })
            total_electores += num_electores

        return {
            "centros": centros_info,
            "total_centros": len(centros_info),
            "total_electores": total_electores
        }

    except ValueError as ve:
        print(f"Error de valor en get_electores_por_centros_info: {str(ve)}")
        raise HTTPException(
            status_code=400,
            detail=f"Código de estado inválido: {codigo_estado}"
        )
    except Exception as e:
        print(f"Error al obtener información de centros: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener información de centros: {str(e)}"
        )


@app.get("/api/download/excel/electores-por-centros/progress/{download_id}")
async def get_download_progress(download_id: str):
    try:
        progress_data = await redis.get(f"download:{download_id}")
        if not progress_data:
            return {
                "estado": "not_found",
                "progreso": 0,
                "total_centros": 0,
                "centros_procesados": 0,
                "total_electores": 0,
                "electores_procesados": 0
            }

        progress_info = json.loads(progress_data)
        return {
            "estado": progress_info.get("estado", "pending"),
            "progreso": progress_info.get("progreso", 0),
            "total_centros": progress_info.get("total_centros", 0),
            "centros_procesados": progress_info.get("centros_procesados", 0),
            "total_electores": progress_info.get("total_electores", 0),
            "electores_procesados": progress_info.get("electores_procesados", 0)
        }
    except Exception as e:
        print(f"Error al obtener progreso de descarga: {str(e)}")
        return {
            "estado": "error",
            "progreso": 0,
            "mensaje": str(e),
            "total_centros": 0,
            "centros_procesados": 0,
            "total_electores": 0,
            "electores_procesados": 0
        }


@app.get("/api/download/excel/electores-por-centros/{codigo_estado}/{codigo_centro}")
async def download_excel_electores_por_centro(
    codigo_estado: str,
    codigo_centro: str,
    db: Session = Depends(get_db)
):
    try:
        # Obtener información del centro
        centro = db.query(CentroVotacion).filter(
            CentroVotacion.codigo_estado == int(codigo_estado),
            CentroVotacion.codificacion_nueva_cv == codigo_centro
        ).first()

        if not centro:
            raise HTTPException(status_code=404, detail="Centro no encontrado")

        # Obtener información geográfica completa
        geo_info = db.query(Geografico).filter(
            Geografico.codigo_estado == int(codigo_estado),
            Geografico.codigo_municipio == centro.codigo_municipio,
            Geografico.codigo_parroquia == centro.codigo_parroquia
        ).first()

        if not geo_info:
            raise HTTPException(status_code=404, detail="Información geográfica no encontrada")

        # Obtener los electores del centro, ordenados por letra (V antes que E) y número de cédula
        electores = (
            db.query(Elector)
            .filter(Elector.codigo_centro_votacion == codigo_centro)
            .order_by(
                # Ordenar primero por letra de cédula (V antes que E)
                case(
                    (Elector.letra_cedula == 'V', 0),
                    (Elector.letra_cedula == 'E', 1),
                    else_=2
                ),
                # Luego ordenar por número de cédula
                Elector.numero_cedula.asc()
            )
            .all()
        )

        if not electores:
            # Si no hay electores, crear un DataFrame vacío con las columnas necesarias
            df = pd.DataFrame(columns=[
                'Cédula', 'Primer Nombre', 'Segundo Nombre',
                'Primer Apellido', 'Segundo Apellido',
                'Fecha Nacimiento', 'Sexo'
            ])
        else:
            # Crear DataFrame con los electores
            data = [{
                'Cédula': f"{elector.letra_cedula}-{elector.numero_cedula}",
                'Primer Nombre': elector.p_nombre,
                'Segundo Nombre': elector.s_nombre,
                'Primer Apellido': elector.p_apellido,
                'Segundo Apellido': elector.s_apellido,
                'Fecha Nacimiento': elector.fecha_nacimiento,
                'Sexo': elector.sexo
            } for elector in electores]
            df = pd.DataFrame(data)

        # Crear el archivo Excel
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            workbook = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1
            })

            # Escribir la información del centro
            worksheet = workbook.add_worksheet(f"Centro_{codigo_centro}"[:31])
            worksheet.write(0, 0, f"Estado: {geo_info.estado}", header_format)
            worksheet.write(1, 0, f"Municipio: {geo_info.municipio}", header_format)
            worksheet.write(2, 0, f"Parroquia: {geo_info.parroquia}", header_format)
            worksheet.write(3, 0, f"Centro de Votación: {centro.nombre_cv}", header_format)
            worksheet.write(4, 0, f"Dirección: {centro.direccion_cv}", header_format)
            worksheet.write(5, 0, f"Código: {centro.codificacion_nueva_cv}", header_format)

            # Escribir los datos de electores
            df.to_excel(writer, sheet_name=f"Centro_{codigo_centro}"[:31], startrow=7, index=False)

            # Ajustar el ancho de las columnas
            for idx, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).apply(len).max(), len(str(col)))
                worksheet.set_column(idx, idx, max_length + 2)

        excel_buffer.seek(0)
        filename = f"electores_{geo_info.estado}_centro_{codigo_centro}.xlsx"

        # Comprimir el archivo Excel
        zip_buffer = compress_file(excel_buffer, filename)

        return StreamingResponse(
            zip_buffer,
            media_type='application/zip',
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.zip"'
            }
        )

    except ValueError as ve:
        print(f"Error de valor en download_excel_electores_por_centro: {str(ve)}")
        raise HTTPException(
            status_code=400,
            detail=f"Error de valor: {str(ve)}"
        )
    except Exception as e:
        print(f"Error generando Excel de electores por centro: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generando Excel de electores por centro: {str(e)}"
        )


@app.get("/api/centros_votacion/", response_model=list[CentroVotacionList])
async def read_all_centros_votacion(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    centros = db.query(CentroVotacion).distinct(
        CentroVotacion.codificacion_nueva_cv
    ).order_by(
        CentroVotacion.codificacion_nueva_cv,
        CentroVotacion.nombre_cv
    ).offset(skip).limit(limit).all()
    return [to_dict(centro) for centro in centros]




if __name__ == "__main__":
    import platform
    import uvicorn
    
    if platform.system() != "Windows":
        # En sistemas Unix/Linux, usar uvloop
        import uvloop
        uvloop.install()
        
    uvicorn.run(app, host="0.0.0.0", port=8000)
