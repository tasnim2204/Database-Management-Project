from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from handler.vehicles import VehicleHandler, VehicleCreate, VehicleUpdate

app = FastAPI()
# origins = [
#    "http://localhost.tiangolo.com",
#    "https://localhost.tiangolo.com",
#    "http://localhost",
#    "http://localhost:8080",
# ]
origins = ['*']
app.add_middleware(
    CORSMiddleware, 
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

@app.get("/")
async def root():
    return {"message": "Hello World!"}

@app.get("/hello/{name}")
async def say_hello(name:str):
    return {"message": f"Hello {name}"}

# --------------- VEHICLE ENDPOINTS ----------------
@app.post("/api/v1/vehicles", status_code=201)
async def create_vehicle(new_vehicle: VehicleCreate):
    return VehicleHandler().create_vehicle(new_vehicle)

@app.get("/api/v1/vehicles", status_code=201)
async def get_vehicles(limit: int, offset: int, status:Optional[str]=None, plate_number:Optional[str]=None):
    return VehicleHandler().get_vehicles(limit, offset, status, plate_number)

@app.get("/api/v1/vehicles/{vehicle_id}", status_code=201)
async def get_vehicle(vehicle_id: int):
    return VehicleHandler().get_vehicle_by_id(vehicle_id)

@app.put("/api/v1/vehicles/{vehicle_id}", status_code=201)
async def update_vehicle(vehicle_id: int, new_vehicle: VehicleUpdate):
    return VehicleHandler().update_vehicle(vehicle_id, new_vehicle)

@app.delete("/api/v1/vehicles/{vehicle_id}", status_code=201)
async def delete_vehicle(vehicle_id: int):
    return VehicleHandler().delete_vehicle(vehicle_id)

@app.get("/api/v1/vehicles/{vehicle_id}/current-location")
async def get_vehicle_current_location(vehicle_id: int):
    return VehicleHandler().get_vehicle_current_location(vehicle_id)