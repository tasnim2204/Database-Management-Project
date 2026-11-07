from pydantic import BaseModel, ValidationError, field_validator
from typing import Optional, Any
from dao.vehicles import VehicleDAO
from fastapi import HTTPException, Response

class VehicleCreate(BaseModel):
    vehicle_type_id: int
    vehicle_status_id: int
    plate_number: str
    make: Optional[str] = ""
    model: Optional[str] = ""
    year: int

    @field_validator("vehicle_type_id", "vehicle_status_id")
    @classmethod
    def validate_id(cls, value: int):
        if value <= 0:
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape.")
        return value
    @field_validator("plate_number")
    @classmethod
    def validate_plate(cls, value: str):
        value = value.strip()
        if value == "":
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape.")
        return value
    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int):
        if not (1950 <= value <= 2100):
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape.")
        return value

class VehicleUpdate(BaseModel):
    vehicle_type_id: Optional[int] | None = None
    vehicle_status_id: Optional[int] | None = None
    plate_number: Optional[str] | None = None
    make: Optional[str] | None = None
    model: Optional[str] | None = None
    year: Optional[int] | None = None

    @field_validator("vehicle_type_id", "vehicle_status_id")
    @classmethod
    def validate_id(cls, value: int):
        if value <= 0:
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape.")
        return value
    @field_validator("plate_number")
    @classmethod
    def validate_plate(cls, value: str):
        value = value.strip()
        if value == "":
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape.")
        return value
    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int):
        if not (1950 <= value <= 2100):
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape.")
        return value

class VehicleHandler:
    def create_vehicle(self, new_vehicle_data: dict[str, Any] | VehicleCreate):
        dao = VehicleDAO()
        try:
            if isinstance(new_vehicle_data, VehicleCreate):
                new_v = new_vehicle_data
            else:
                new_v = VehicleCreate.model_validate(new_vehicle_data)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape")

        if not dao.vehicle_status_exists(new_v.vehicle_status_id) or not dao.vehicle_type_exists(new_v.vehicle_type_id):
            raise HTTPException(status_code=404, detail="Referenced vehicle_type_id or vehicle_status_id does not exist.")

        if dao.plate_in_use(new_v.plate_number):
            raise HTTPException(status_code=409, detail="plate_number already exists.")

        if new_v.make is not None:
            new_v.make.strip()
        if new_v.model is not None:
            new_v.model.strip()
        try:
            return dao.create_vehicle(new_v.model_dump())
        except Exception:
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape.")

    def get_vehicles(self, limit, offset, status: Optional[Any]=None, plate_number: Optional[str]=None):
        dao = VehicleDAO()

        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="Invalid query parameter values.")
        
        return dao.get_all_vehicles(limit, offset, status, plate_number)

    def get_vehicle_by_id(self, vehicle_id: int):
        dao = VehicleDAO()

        if vehicle_id <= 0:
            raise HTTPException(status_code=400, detail="vehicle_id is not a positive integer.")

        result = dao.get_vehicle_by_id(vehicle_id)
        if result is None:
            raise HTTPException(status_code=404, detail="vehicle_id does not exist.")
        return result
    
    def update_vehicle(self, vehicle_id: int, new_vehicle_data: dict[str, Any] | VehicleUpdate):
        dao = VehicleDAO()
        try:
            if isinstance(new_vehicle_data, VehicleUpdate):
                new_vehicle = new_vehicle_data.model_dump(exclude_unset=True)
            else:
                new_vehicle = VehicleUpdate.model_validate(new_vehicle_data).model_dump(exclude_unset=True)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty payload.")

        if not new_vehicle:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty payload.")

        if "vehicle_id" in new_vehicle and not dao.vehicle_exists(vehicle_id):
            raise HTTPException(status_code=404, detail="vehicle_id does not exist.")
        if "vehicle_type_id" in new_vehicle and not dao.vehicle_type_exists(new_vehicle.vehicle_type_id): # type: ignore
            raise HTTPException(status_code=404, detail="referenced foreign key does not exist.")
        if "vehicle_status_id" in new_vehicle and not dao.vehicle_status_exists(new_vehicle.vehicle_status_id): # type: ignore
            raise HTTPException(status_code=404, detail="referenced foreign key does not exist.")

        if "make" in new_vehicle:
            new_vehicle["make"] = new_vehicle["make"].strip()
        if "model" in new_vehicle:
            new_vehicle["model"] = new_vehicle["model"].strip()

        if "plate_number" in new_vehicle:
            new_vehicle["plate_number"] = new_vehicle["plate_number"].strip()
            if dao.plate_in_use(new_vehicle["[plate_number]"], vehicle_id):
                raise HTTPException(status_code=409, detail="Updated plate_number conflicts with another vehicle.")

        result = dao.update_vehicle(vehicle_id, new_vehicle)

        if result is None:
            raise HTTPException(status_code=404, detail="vehicle_id does not exist.")
        return result

    def delete_vehicle(self, vehicle_id: int):
        dao = VehicleDAO()

        if vehicle_id <= 0 or not dao.vehicle_exists(vehicle_id):
            raise HTTPException(status_code=404, detail="vehicle_id does not exist.")

        if dao.has_location_pings(vehicle_id) or dao.has_trips(vehicle_id) or dao.has_assignments(vehicle_id):
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

        if not dao.has_location_pings(vehicle_id):
            return Response(status_code=204)

        result = dao.get_vehicle_current_location(vehicle_id)
        if result is None:
            return HTTPException(status_code=404, detail="vehicle_id does not exist.")
        return result