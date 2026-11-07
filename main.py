from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from handler.vehicles import VehicleHandler, VehicleCreate, VehicleUpdate
from handler.road_segments import RoadHandler, RoadSegmentCreate, RoadSegmentUpdate
from handler.parking_area import ParkingHandler, ParkingAreaCreate, ParkingAreaUpdate
from handler.location_ping import LocationHandler, LocationPingCreate, LocationPingUpdate
from handler.trip import TripHandler, TripCreate, TripUpdate
from handler.driver import DriverHandler, DriverCreate, DriverUpdate
from handler.vehicle_assignment import VehicleAssignmentHandler, VehicleAssignmentCreate, VehicleAssignmentUpdate

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

@app.get("/api/v1/vehicles", status_code=200)
async def get_vehicles(limit: int, offset: int, status:Optional[str]=None, plate_number:Optional[str]=None):
    return VehicleHandler().get_vehicles(limit, offset, status, plate_number)

@app.get("/api/v1/vehicles/{vehicle_id}", status_code=200)
async def get_vehicle_by_id(vehicle_id: int):
    return VehicleHandler().get_vehicle_by_id(vehicle_id)

@app.put("/api/v1/vehicles/{vehicle_id}", status_code=200)
async def update_vehicle(vehicle_id: int, new_vehicle: VehicleUpdate):
    return VehicleHandler().update_vehicle(vehicle_id, new_vehicle)

@app.delete("/api/v1/vehicles/{vehicle_id}", status_code=200)
async def delete_vehicle(vehicle_id: int):
    return VehicleHandler().delete_vehicle(vehicle_id)

@app.get("/api/v1/vehicles/{vehicle_id}/current-location", status_code=200)
async def get_vehicle_current_location(vehicle_id: int):
    return VehicleHandler().get_vehicle_current_location(vehicle_id)

# --------------- ROAD-SEGMENT ENDPOINTS ----------------
@app.post("/api/v1/road-segments", status_code=201)
async def create_road_segment(new_road_data: RoadSegmentCreate):
    return RoadHandler().create_road_segment(new_road_data)

@app.get("/api/v1/road-segments/geojson", status_code=200)
async def get_road_geojson(limit:int, offset: int, name: str, min_speed_kph: int, max_speed_kph: int):
    return RoadHandler().get_road_geojson(limit, offset, name, min_speed_kph, max_speed_kph)

@app.get("/api/v1/road-segments")
async def get_road_segments(limit:int, offset: int, name: Optional[str]=None, min_speed_kph: Optional[int]=None, max_speed_kph: Optional[int]=None, bbox: Optional[str]=None):
    return RoadHandler().get_road_segments(limit, offset, name, min_speed_kph, max_speed_kph, bbox)

@app.get("/api/v1/road-segments/{road_id}", status_code=200)
async def get_road_by_id(road_id: int):
    return RoadHandler().get_road_by_id(road_id)

@app.put("/api/v1/road-segments/{road_id}", status_code=200)
async def update_road_segment(road_id: int, new_road: RoadSegmentUpdate):
    return RoadHandler().update_road_segment(road_id, new_road)

@app.delete("/api/v1/road-segments/{road_id}", status_code=200)
async def delete_road_segment(road_id: int):
    return RoadHandler().delete_road_segment(road_id)

# --------------- PARKING-AREA ENDPOINTS ----------------
@app.post("/api/v1/parking-areas", status_code=201)
async def create_parking_area(new_parking_data: ParkingAreaCreate):
    return ParkingHandler().create_parking_area(new_parking_data)

@app.get("/api/v1/parking-areas", status_code=200)
async def get_parking_areas(limit: int, offset: int, bbox: Optional[str]=None):
    return ParkingHandler().get_parking_areas(limit, offset, bbox)

@app.get("/api/v1/parking-areas/{parking_area_id}", status_code=200)
async def get_parking_by_id(parking_area_id: int):
    return ParkingHandler().get_parking_by_id(parking_area_id)

@app.put("/api/v1/parking-areas/{parking_area_id}", status_code=200)
async def update_parking_area(parking_area_id:int, new_parking_data: ParkingAreaUpdate):
    return ParkingHandler().update_parking_area(parking_area_id, new_parking_data)

@app.delete("/api/v1/parking-areas/{parking_area_id}")
async def delete_parking_area(parking_area_id: int):
    return ParkingHandler().delete_parking_area(parking_area_id)

# --------------- LOCATION-PING ENDPOINTS ----------------
@app.post("/api/v1/location-pings", status_code=201)
async def create_location_ping(new_location_ping: LocationPingCreate):
    return LocationHandler().create_location_ping(new_location_ping)

@app.get("/api/v1/location-pings")
async def get_all_location_pings(limit: int, offset: int, vehicle_id: Optional[int] = None, from_ts: Optional[datetime] = None, to_ts: Optional[datetime] = None, bbox: Optional[str] = None):
    return LocationHandler().get_all_pings(limit, offset, vehicle_id, from_ts, to_ts, bbox)

@app.get("/api/v1/location-pings/{ping_id}")
async def get_ping_by_id(ping_id: int):
    return LocationHandler().get_ping_by_id(ping_id)

@app.put("/api/v1/location-pings/{ping_id}")
async def update_location_ping(ping_id: int, new_location_ping: LocationPingUpdate):
    return LocationHandler().update_location_ping(ping_id, new_location_ping)

@app.delete("/api/v1/location-pings/{ping_id}")
async def delete_location_ping(ping_id: int):
    return LocationHandler().delete_location_ping(ping_id)

@app.get("/api/v1/vehicles/{vehicle_id}/pings")
async def get_pings_by_vehicle(vehicle_id: int, limit: int, offset: int, from_ts: Optional[datetime] = None, to_ts: Optional[datetime] = None):
    return LocationHandler().get_pings_by_vehicle(vehicle_id, limit, offset, from_ts, to_ts)

# --------------- TRIP ENDPOINTS ----------------
@app.post("/api/v1/trips")
async def create_trip(new_trip_data: TripCreate):
    return TripHandler().create_trip(new_trip_data)

@app.get("/api/v1/trips")
async def get_all_trips(limit: int, offset: int, from_ts: datetime, to_ts: datetime, vehicle_id: Optional[int]=None, ):
    return TripHandler().get_all_trips(limit, offset, from_ts, to_ts, vehicle_id)

@app.get("/api/v1/trips/{trip_id}")
async def get_trip_by_id(trip_id:int):
    return TripHandler().get_trip_by_id(trip_id)

@app.put("/api/v1/trips/{trip_id}")
async def update_trip(trip_id: int, new_trip_data: TripUpdate):
    return TripHandler().update_trip(trip_id, new_trip_data)

@app.delete("/api/v1/trips/{trip_id}")
async def delete_trip(trip_id: int):
    return TripHandler().delete_trip(trip_id)

@app.get("/api/v1/vehicles/{vehicle_id}/trips")
async def get_trips_by_vehicle(vehicle_id: int, limit: int, offset: int, from_ts: Optional[datetime]=None, to_ts: Optional[datetime]=None):
    return TripHandler().get_trips_by_vehicle(vehicle_id, limit, offset, from_ts, to_ts)

# --------------- DRIVER ENDPOINTS ----------------
@app.post("/api/v1/drivers")
async def create_driver(new_driver_data: DriverCreate):
    return DriverHandler().create_driver(new_driver_data)

@app.get("/api/v1/drivers")
async def get_all_drivers(limit: int, offset: int, name: Optional[str]=None, license_number: Optional[str]=None):
    return DriverHandler().get_all_drivers(limit, offset, name, license_number)

@app.get("/api/v1/drivers/{driver_id}")
async def get_driver_by_id(driver_id: int):
    return DriverHandler().get_driver_by_id(driver_id)

@app.put("/api/v1/drivers/{driver_id}")
async def update_driver(driver_id: int, new_driver_data: DriverUpdate):
    return DriverHandler().update_driver(driver_id, new_driver_data)

@app.delete("/api/v1/drivers/{driver_id}")
async def delete_driver(driver_id: int):
    return DriverHandler().delete_driver(driver_id)

# --------------- VEHICLE ASSIGNMENT ENDPOINTS ----------------
@app.post("/api/v1/vehicle-assignments")
async def create_vehicle_assignment(new_assignment_data: VehicleAssignmentCreate):
    return VehicleAssignmentHandler().create_vehicle_assignment(new_assignment_data)

@app.get("/api/v1/vehicle-assignments")
async def get_vehicle_assignments(limit: int, offset: int, vehicle_id: Optional[int]=None, driver_id: Optional[int]=None, active: Optional[bool]=None):
    return VehicleAssignmentHandler().get_vehicle_assignments(limit, offset, vehicle_id, driver_id, active)

@app.get("/api/v1/vehicle-assignments/{assignment_id}")
async def get_assignment_by_id(assignment_id: int):
    return VehicleAssignmentHandler().get_assignment_by_id(assignment_id)

@app.put("/api/v1/vehicle-assignments/{assignment_id}")
async def update_vehicle_assignment(assignment_id: int, new_assignment_data: VehicleAssignmentUpdate):
    return VehicleAssignmentHandler().update_vehicle_assignment(assignment_id, new_assignment_data)

@app.delete("/api/v1/vehicle-assignments/{assignment_id}")
async def delete_vehicle_assignment(assignment_id: int):
    return VehicleAssignmentHandler().delete_vehicle_assignment(assignment_id)