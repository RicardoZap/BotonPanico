from typing import Union
from fastapi import FastAPI, Depends, HTTPException, Request, status, Response, Header, APIRouter
from typing_extensions import Annotated
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from threading import Timer
from pydantic import BaseModel
from typing import Optional
import requests 
from datetime import datetime
import os
from dotenv import load_dotenv
import pyodbc
from datetime import datetime, timedelta
import secrets
from threading import Timer

load_dotenv()

app = FastAPI()

class Auth(BaseModel):
    account: str
    password: str

class DatosRequired(BaseModel):
    unidad: str
    device: str
    primer_nombre: str
    segundo_nombre: Optional[str]
    apellido_paterno: str
    apellido_materno: str
    numero_contacto: Optional[int]
    notas: Optional[str]
    fecha_evento: str

jsession_public = None
idDispositivo = "10512"
urlGPS = None
urlVideo = None
account = os.getenv("ACCOUNT")
password = os.getenv("PASSWORD")
gps_info = {}
#Llave inicial genereda automaticamente
API_KEY = ""
#Segunda llave/variable que se le dará valor al llamar el método de boton de panico
KEY_ALERTA = ""

# Enrutador para la ruta protegida
router = APIRouter()

#Llamada de evento al iniciar la API para generar automaticamente la API_KEY
@app.on_event("startup")
async def startup_event():
    global API_KEY
    API_KEY = generar_token()

# Middleware para verificar el token en cada solicitud
@app.middleware("http")
async def verify_api_key(request, call_next):
    global API_KEY
    global KEY_ALERTA
    if request.url.path != "/setAlerta":  # Excluir la ruta del botón de panico para evitar problemas con Swagger
        api_key = KEY_ALERTA
        #Si la segunda llave no coincide con la llave inicial se denegará el acceso
        if api_key != API_KEY:
            raise HTTPException(status_code=403, detail="Acceso no autorizado")
    response = await call_next(request)
    return response

#Función para reiniciar el valor la primera llave cada 15 minutos
def reset_token():
    global API_KEY
    API_KEY = generar_token()
    # Reiniciar el temporizador después de 15 minutos
    Timer(900, reset_token).start()

# Agregar el enrutador a la aplicación principal
app.include_router(router)

#Método para generar el valor de la llave
async def generar_token():
    return secrets.token_urlsafe(16)

@app.get("/")
def index():
    return {"message" : "Hola, soy FastApi"}

@app.get("/login")
async def login():
    global account
    global password
    url = "http://187.188.171.164:8088/StandardApiAction_login.action?account={}&password={}".format(account, password)
    headers = {
        "Content-Type": "application/json-p"
    }
    try:
        response = requests.post(url, headers)
        r = response.json()
        if(r["result"] != 0):
            return {"result": -1, "mensaje": "Usuario o contraseña incorrecta"}
        else:
            print(response.content)
            global jsession_public
            jsession_public = r["jsession"]
            return "Logueado correctamente"
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def getInfo():
    global jsession_public
    url = "http://187.188.171.164:8088/StandardApiAction_queryUserVehicle.action?jsession={}".format(jsession_public)
    headers = {
        "Content-Type": "application/json-p"
    }
    try:
        response = requests.get(url, headers)
        return response.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Ruta protegida con token
@app.get("/gpsDetalles")
async def getGPSDetail():
    global gps_info
    return JSONResponse(gps_info)
    
async def getGPSMap():
    global jsession_public
    global idDispositivo
    global urlGPS
    url = "http://187.188.171.164:8088/808gps/open/map/vehicleMap.html?jsession={}&devIdno={}".format(jsession_public, idDispositivo)
    url2 = "http://187.188.171.164:8088/StandardApiAction_getDeviceStatus.action?jsession={}&devIdno={}".format(jsession_public, idDispositivo)

    headers = {
        "Content-Type": "application/json-p"
    }
    try:
        global gps_info
        response = requests.get(url, headers)
        response2 = requests.get(url2, headers)
        data = response2.json()
        gps_info = {
            "speed": data["status"][0]["sp"],
            "ID": data["status"][0]["vid"],
            "Course": data["status"][0]["hx"],
            "longitud": data["status"][0]["mlng"],
            "latitud": data["status"][0]["mlat"],
            "altitud": 0,
            "Date": data["status"][0]["gt"]
        }
        print(gps_info)
        #getGPSDetail(gps_info)
        urlGPS = url
        gps = {
                "GPS": url,
                "GPSData": url2,
                "GPSDetailMethod": "http://127.0.0.1:8000/gpsDetalles"
            }
        return gps
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
async def getVideo():
    global jsession_public
    global idDispositivo
    global urlVideo
    url = "http://187.188.171.164:8088/808gps/open/player/video.html?lang=en&devIdno={}&channel={}&jsession={}".format(idDispositivo, 2, jsession_public)
    headers = {
        "Content-Type": "application/json-p"
    }
    try:
        response = requests.get(url, headers)
        urlVideo = url
        return url
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/setAlerta")
async def setAlerta(datos: DatosRequired, response: Response, user_agent: Annotated[Union[str, None], Header()] = None):
    try:
        global API_KEY
        global KEY_ALERTA
        print(API_KEY)
        Timer(900, reset_token).start()
        
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        await login()
        url_gps = await getGPSMap()
        url_video = await getVideo()
        camara1= url_video + "&index=1"
        camara2= url_video + "&index=2"
        json_response = {
            "concesion": datos.unidad,
            "primer_nombre_contacto": datos.primer_nombre,
            "segundo_nombre_contacto": datos.segundo_nombre,
            "apellido_paterno_contacto": datos.apellido_paterno,
            "apellido_materno_contacto": datos.apellido_materno,
            "numero_contacto": datos.numero_contacto,
            "FechaHoraEvento": fecha_actual,
            "GPS": url_gps["GPS"],
            "GPSDetallado": url_gps["GPSDetailMethod"],
            "video": [
                camara1,
                camara2
            ],
            "notas": datos.notas
        }
        await log(json_response)

        KEY_ALERTA = API_KEY
        return JSONResponse(json_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
async def log(json):
    try:
        cnxn = pyodbc.connect(f'DRIVER={os.getenv("DRIVER")};SERVER={os.getenv("SERVER")};DATABASE={os.getenv("DATABASE")};UID={os.getenv("USERNAME_DB")};PWD={os.getenv("PASSWORD_DB")};')
        cursor = cnxn.cursor()
        params = (json["concesion"],10512,json["primer_nombre_contacto"],json["segundo_nombre_contacto"],json["apellido_paterno_contacto"],json["apellido_materno_contacto"],json["video"][0],json["GPS"],json["notas"],json["FechaHoraEvento"])
        cursor.execute("{CALL ins_Envio_Evento (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)}", params)
        cursor.commit()
        cursor.close()
        cnxn.close()
        return {'mensaje': 'Inserción exitosa'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
