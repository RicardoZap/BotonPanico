from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import requests 
from datetime import datetime
import os
from dotenv import load_dotenv
import pyodbc

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

@app.get("/getInfo")
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
    
@app.get("/getGPS")
async def getGPSMap():
    global jsession_public
    global idDispositivo
    global urlGPS
    url = "http://187.188.171.164:8088/808gps/open/map/vehicleMap.html?jsession={}&devIdno={}".format(jsession_public, idDispositivo)
    url2 = "http://187.188.171.164:8088/StandardApiAction_getDeviceStatus.action?jsession={}&devIdno={}&language=zh".format(jsession_public, idDispositivo)

    headers = {
        "Content-Type": "application/json-p"
    }
    try:
        response = requests.get(url, headers)
        response2 = requests.get(url2, headers)
        response2_json = response2.json()
        lat = response2_json["status"][0]["lat"]
        lng = response2_json["status"][0]["lng"]
        mlng = response2_json["status"][0]["mlng"]
        mlat = response2_json["status"][0]["mlat"]
        urlGPS = url
        gps = {
                "GPS": url,
                "lat": lat,
                "lng": lng,
                "mlng": mlng,
                "mlat": mlat
            }
        return gps
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/getVideo")
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
async def setAlerta(datos: DatosRequired):
    try:
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        await login()
        url_gps = await getGPSMap()
        url_video = await getVideo()
        camara1= url_video + "&index=1"
        camara2= url_video + "&index=2"
        json_response = {
            "unidad": datos.unidad,
            "primer_nombre_contacto": datos.primer_nombre,
            "segundo_nombre_contacto": datos.segundo_nombre,
            "apellido_paterno_contacto": datos.apellido_paterno,
            "apellido_materno_contacto": datos.apellido_materno,
            "numero_contacto": datos.numero_contacto,
            "FechaHoraEvento": fecha_actual,
            "GPS": url_gps["GPS"],
            "lat": url_gps["lat"],
            "lng": url_gps["lng"],
            "mlng": url_gps["mlng"],
            "mlat": url_gps["mlat"],
            "video1": camara1,
            "video2": camara2,
            "notas": datos.notas
        }
        await log(json_response)
        return JSONResponse(json_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/insertLog")
async def log(json):
    try:
        cnxn = pyodbc.connect(f'DRIVER={os.getenv("DRIVER")};SERVER={os.getenv("SERVER")};DATABASE={os.getenv("DATABASE")};UID={os.getenv("USERNAME_DB")};PWD={os.getenv("PASSWORD_DB")};')
        cursor = cnxn.cursor()
        params = (json["unidad"],10512,json["primer_nombre_contacto"],json["segundo_nombre_contacto"],json["apellido_paterno_contacto"],json["apellido_materno_contacto"],json["video1"],json["GPS"],json["notas"],json["FechaHoraEvento"])
        cursor.execute("{CALL ins_Envio_Evento (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)}", params)
        cursor.commit()
        cursor.close()
        cnxn.close()
        return {'mensaje': 'Inserción exitosa'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
