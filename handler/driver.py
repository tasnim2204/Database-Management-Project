from datetime import datetime
from pydantic import BaseModel, ValidationError, field_validator
from typing import Optional, Any
from dao.driver import DriverDAO
from fastapi import HTTPException

class DriverCreate(BaseModel):
    first_name: str
    last_name: str
    license_number: str
    hired_at: datetime

    @field_validator("first_name", "last_name", "license_number")
    @classmethod
    def validate_string(cls, value:str) -> str:
        if not value or not value.strip():
            raise HTTPException(status_code=400, detail="value must be non-empty.")
        return value.strip()

class DriverUpdate(BaseModel):
    first_name: Optional[str] | None = None
    last_name: Optional[str] | None = None
    license_number: Optional[str] | None = None
    hired_at: Optional[datetime] | None = None

    @field_validator("first_name", "last_name", "license_number")
    @classmethod
    def validate_string(cls, value:str) -> str:
        if not value or not value.strip():
            raise HTTPException(status_code=400, detail="value must be non-empty.")
        return value.strip()

class DriverHandler:
    def create_driver(self, new_driver_data: dict[str, Any] | DriverCreate):
        dao = DriverDAO()
        try:
            if isinstance(new_driver_data, DriverCreate):
                new_driver = new_driver_data
            else:
                new_driver = DriverCreate.model_validate(new_driver_data) # validates the object to be an instance of VehicleCreate
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape. VALIDaTION")
        
        license_number = new_driver.license_number.strip()
        if license_number == "": #no tiene valor
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape. LICENSE")

        if dao.license_in_use(license_number):
            raise HTTPException(status_code=409, detail="license_number already exists.")
        try:
            return dao.create_driver(new_driver.model_dump())
        except ValueError:
            raise HTTPException(status_code=422, detail="A required field is null or invalid.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Malformed JSON or invalid payload shape. Error: {e}")

    def get_all_drivers(self, limit: int, offset: int, name: Optional[str]=None, license_number: Optional[str]=None):
        dao = DriverDAO()
        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="Invalid query parameter values.")
        return dao.get_all_drivers(limit, offset, name, license_number)

    def get_driver_by_id(self, driver_id: int):
        dao = DriverDAO()

        result = dao.get_driver_by_id(driver_id)
        if result is None:
            raise HTTPException(status_code=404, detail="vehicle_id does not exist.")
        return result

    def update_driver(self, driver_id: int, new_driver_data: dict[str,Any] | DriverUpdate):
        dao = DriverDAO()
        try:
            if isinstance(new_driver_data, DriverUpdate):
                new_driver = new_driver_data.model_dump(exclude_unset=True)
            else:
                new_driver = DriverUpdate.model_validate(new_driver_data)
                new_driver = new_driver_data
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload.")
        
        if not new_driver:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload.")
        if driver_id < 0:
            raise HTTPException(status_code=404, detail="driver_id does not exist.")

        if "first_name" in new_driver:
            new_driver["first_name"] = new_driver["first_name"].strip()
            if new_driver["first_name"] == "":
                raise HTTPException(status_code=400, detail="Malformed JSON or empty update payload.")
        if "last_name" in new_driver:
            new_driver["last_name"] = new_driver["last_name"].strip()
            if new_driver["last_name"] == "":
                raise HTTPException(status_code=400, detail="Malformed JSON or empty update payload.")

        if "license_number" in new_driver:
            new_driver["license_number"] = new_driver["license_number"].strip()
            if new_driver["license_number"] == "": #no tiene valor
                raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape. LICENSE")
        try:
            result = dao.update_driver(driver_id, new_driver)
            if result is None:
                return None
            return result
        except ValueError:
            raise HTTPException(status_code=422, detail="A supplied field is null or invalid.")
        except Exception:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")

    def delete_driver(self, driver_id: int):
        dao = DriverDAO()
        if driver_id < 0:
            raise HTTPException(status_code=404, detail="driver_id does not exist.")
        if dao.has_assignments(driver_id):
            raise HTTPException(status_code=409, detail="The driver is referenced by a vehicle assignment.")
        
        result = dao.delete_driver(driver_id)
        if result is None:
            raise HTTPException(status_code=404, detail="road_id does not exist.")
        return {"message": "Driver deleted successfully.", 
                        "driver_id": driver_id}