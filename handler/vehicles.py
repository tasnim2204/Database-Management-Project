from pydantic import BaseModel, ValidationError
from typing import Optional, Any
from dao.vehicles import VehicleDAO
from fastapi import HTTPException
from psycopg2 import errors

class VehicleCreate(BaseModel):
    vehicle_type_id: int
    vehicle_status_id: int
    plate_number: str
    make: Optional[str] = ""
    model: Optional[str] = ""
    year: int

class VehicleUpdate(BaseModel):
    vehicle_type_id: Optional[int] | None = None
    vehicle_status_id: Optional[int] | None = None
    plate_number: Optional[str] | None = None
    make: Optional[str] | None = None
    model: Optional[str] | None = None
    year: Optional[int] | None = None

class VehicleHandler:
    def create_vehicle(self, new_vehicle_data: dict[str, Any] | VehicleCreate):
        dao = VehicleDAO()
        try:
            if isinstance(new_vehicle_data, VehicleCreate):
                new_v = new_vehicle_data
            else:
                new_v = VehicleCreate.model_validate(new_vehicle_data) # validates the object to be an instance of VehicleCreate
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape. VALIDATION")
        
        if new_v.vehicle_status_id <= 0 or new_v.vehicle_type_id <= 0: #no es un valor posible
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape. NOT VALID VALUE")

        plate_number = new_v.plate_number.strip()
        if plate_number == "": #no tiene valor
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape. PLATE")

        if new_v.year < 1950 or new_v.year > 2100:
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape. YEARTHING")

        make = new_v.make.strip() if new_v.make is not None else None
        model = new_v.model.strip() if new_v.model is not None else None

        if not dao.vehicle_status_exists(new_v.vehicle_status_id) or not dao.vehicle_type_exists(new_v.vehicle_type_id):
            raise HTTPException(status_code=404, detail="Referenced vehicle_type_id or vehicle_status_id does not exist.")

        if dao.plate_in_use(plate_number):
            raise HTTPException(status_code=409, detail="plate_number already exists. IN USE")

        payload = VehicleCreate(vehicle_type_id=new_v.vehicle_type_id, vehicle_status_id=new_v.vehicle_status_id, 
                                plate_number=plate_number, make=make, model=model, year=new_v.year)

        try:
            return dao.create_vehicle(payload.model_dump())
        except Exception:
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape.EXCEPTION")

    def get_vehicles(self, limit, offset, status=None, plate_number=None):
        dao = VehicleDAO()
        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="Invalid query parameter values.")
        return dao.get_all_vehicles(limit, offset, status, plate_number)

    def get_vehicle_by_id(self, vehicle_id: int):
        dao = VehicleDAO()
        
        result = dao.get_vehicle_by_id(vehicle_id)
        if result is None:
            raise HTTPException(status_code=404, detail="vehicle_id does not exist.")
        return result
    
    def update_vehicle(self, vehicle_id: int, new_vehicle_data: dict[str, Any] | VehicleUpdate):
        dao = VehicleDAO()
        try:
            if isinstance(new_vehicle_data, VehicleUpdate):
                new_v = new_vehicle_data.model_dump(exclude_unset=True)
            else:
                validated_vehicle = VehicleUpdate.model_validate(new_vehicle_data) # validates the object to be an instance of VehicleUpdate
                new_v = validated_vehicle
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty payload. VALIDATION")

        if not new_v:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty payload.")
        
        if vehicle_id <= 0 or not dao.vehicle_exists(vehicle_id): #vehicle id invalid
            raise HTTPException(status_code=404, detail="vehicle_id or referenced foreign key does not exist.")

        if "vehicle_type_id" in new_v and not dao.vehicle_type_exists(new_v["vehicle_type_id"]): # type: ignore
            raise HTTPException(status_code=400, detail="Malformed JSON or empty payload.")

        if "vehicle_status_id" in new_v and not dao.vehicle_status_exists(new_v["vehicle_status_id"]): # type: ignore
            raise HTTPException(status_code=400, detail="Malformed JSON or empty payload.")

        if "plate_number" in new_v: #type: ignore
            new_v["plate_number"] = new_v["plate_number"].strip() # type: ignore

            if "plate_number" not in new_v or dao.plate_in_use(new_v["plate_number"], vehicle_id): # type: ignore
                raise HTTPException(status_code=409, detail="Updated plate_number conflicts with another vehicle.")

        if "make" in new_v:  # type: ignore
            new_v["make"] = new_v["make"].strip()  # type: ignore

        if "model" in new_v:  # type: ignore
            new_v["model"] = new_v["model"].strip()  # type: ignore

        if "year" in new_v:  # type: ignore
            if new_v["year"] < 1950 or new_v["year"] > 2100: # type: ignore
                raise HTTPException(status_code=400, detail="Malformed JSON or empty payload.")

        try:
            result = dao.update_vehicle(vehicle_id, new_v) # type: ignore
            return result if not None else None
        except Exception:
            raise HTTPException(status_code=409, detail="Updated plate_number conflicts with another vehicle.")

    def delete_vehicle(self, vehicle_id: int):
        dao = VehicleDAO()

        if vehicle_id <= 0 or not dao.vehicle_exists(vehicle_id):
            raise HTTPException(status_code=404, detail="vehicle_id does not exist.")

        if dao.has_location_pings(vehicle_id) or dao.has_trips(vehicle_id):
            raise HTTPException(status_code=409, detail="Deletion is blocked by business rules /foreign key constraints.")

        results = dao.delete_vehicle(vehicle_id)
        if results is None:
            raise HTTPException(status_code=404, detail="vehicle_id does not exist.")
            
        return {"message": "Vehicle deleted successfully.", 
                "vehicle_id": vehicle_id}

    def get_vehicle_current_location(self, vehicle_id: int):
        dao = VehicleDAO()
        if vehicle_id <= 0:
            raise HTTPException(status_code=400, detail="vehicle_id is not a positive integer.")
        
        if not dao.vehicle_exists(vehicle_id):
            raise HTTPException(status_code=404, detail="vehicle_id does not exist.")

        result = dao.get_vehicle_current_location(vehicle_id)
        if result is None:
            return HTTPException(status_code=204, detail="Vehicle exists but has no recorded pings yet.")
        return result