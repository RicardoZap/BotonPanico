from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import requests 
import datetime
import os
from dotenv import load_dotenv
#import pyodbc

load_dotenv()

app = FastAPI()

class Auth(BaseModel):
    account: str
    password: str

class DatosRequired(BaseModel):
    unidad: str
    device: str
    contacto: Optional[str]
    telefono: Optional[int]
    notas: Optional[str]

jsession_public = None
idDispositivo = "10512"
urlGPS = None
urlVideo = None
account = os.getenv("ACCOUNT")
password = os.getenv("PASSWORD")
#cnxn = pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={os.getenv("SERVER")};DATABASE={os.getenv("DATABASE")};UID={os.getenv("USERNAME_DB")};PWD={os.getenv("PASSWORD_DB")}')

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
    headers = {
        "Content-Type": "application/json-p"
    }
    try:
        response = requests.get(url, headers)
        urlGPS = url
        return url
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/getVideo")
async def getVideo():
    global jsession_public
    global idDispositivo
    global urlVideo
    url = "http://187.188.171.164:8088/808gps/open/player/video.html?lang=en&devIdno={}&jsession={}".format(idDispositivo, jsession_public)
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
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await login()
        url_gps = await getGPSMap()
        url_video = await getVideo()
 
        json_response = {
            "unidad": datos.unidad,
            "nombre_contacto": datos.contacto,
            "FechaHoraEvento": now,
            "GPS": url_gps,
            "video": url_video,
            "notas": datos.notas
        }
        return JSONResponse(json_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/insertLog")
async def log():
    fecha = datetime.datetime.now()
    try:
        #cursor = cnxn.cursor()
        # Hace la inserción a la tabla "log"
        #cursor.execute(f"INSERT INTO log (campo1) VALUES ('{fecha}')")
        #cnxn.commit()

        return {'mensaje': 'Inserción exitosa'}
    except Exception as e:
        # En caso de error, hace un rollback y regresa el mensaje de error
        #cnxn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
